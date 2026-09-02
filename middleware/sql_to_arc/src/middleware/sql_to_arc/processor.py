"""Orchestration and worker management for the SQL-to-ARC conversion process."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import multiprocessing
from collections import defaultdict
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pydantic import BaseModel

from middleware.api_client import ApiClient, ApiClientError
from middleware.shared.report import HarvestReport, RepositoryScope
from middleware.sql_to_arc.builder import DuplicateAssayRowError, DuplicateStudyRowError, build_single_arc_task
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.context import (
    ArcBuildData,
    RelatedDataBatch,
    WorkerContext,
)
from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.models import InvestigationRow
from middleware.sql_to_arc.process_pool import ProcessPoolHolder

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _apply_expected_datasets(scope: RepositoryScope, count: int | None, debug_limit: int | None) -> None:
    """Set expected datasets on the scope when a count is known."""
    if not isinstance(count, int):
        return
    expected = min(count, debug_limit) if isinstance(debug_limit, int) else count
    scope.set_expected_datasets(expected)


@dataclass(frozen=True, slots=True)
class CompositionCounts:
    """Study/assay counts for one successfully built investigation."""

    studies: int
    assays: int


@dataclass(frozen=True, slots=True)
class BuiltArc:
    """A successfully built ARC waiting to be submitted in the harvest stream."""

    arc_json: str
    investigation_id: str
    inv_info: str
    composition: CompositionCounts


@dataclass
class ArcStreamState:
    """Tracks ARCs yielded into ``harvest_arcs`` for post-upload scope updates."""

    submitted_ids: list[str] = field(default_factory=list)
    compositions: dict[str, CompositionCounts] = field(default_factory=dict)
    arc_id_to_investigation: dict[str, str] = field(default_factory=dict)

    @property
    def submitted(self) -> int:
        """Number of ARCs submitted into the harvest stream."""
        return len(self.submitted_ids)

    def track(self, built: BuiltArc, arc_payload: dict[str, Any]) -> None:
        """Record metadata for a yielded ARC payload."""
        self.submitted_ids.append(built.investigation_id)
        self.compositions[built.investigation_id] = built.composition
        raw_id = arc_payload.get("identifier")
        if isinstance(raw_id, str) and raw_id:
            self.arc_id_to_investigation[raw_id] = built.investigation_id
        # Also map investigation id itself for clients that echo it as arc_id.
        self.arc_id_to_investigation.setdefault(built.investigation_id, built.investigation_id)


def _investigation_id_for_error(state: ArcStreamState, arc_id: str | None) -> str | None:
    """Resolve a harvest error arc_id to the investigation id used for reporting."""
    if not isinstance(arc_id, str) or not arc_id:
        return None
    return state.arc_id_to_investigation.get(arc_id, arc_id)


def _apply_upload_outcomes(errors: list[Any], state: ArcStreamState, scope: RepositoryScope) -> None:
    """Apply harvest_arcs per-item errors and successes to the repository scope."""
    failed_ids: set[str] = set()
    for err in errors:
        raw_id = getattr(err, "arc_id", None)
        record_id = _investigation_id_for_error(state, raw_id if isinstance(raw_id, str) else None)
        message = str(getattr(err, "message", err))
        if record_id is None:
            # Cannot attribute to a dataset; avoid a null dataset failure and keep applying peers.
            scope.record_repository_issue(f"Unattributed harvest error: {message}")
            continue
        scope.record_failed(message, record_id=record_id)
        failed_ids.add(record_id)

    for inv_id in state.submitted_ids:
        if inv_id in failed_ids:
            continue
        scope.record_harvested()
        composition = state.compositions.get(inv_id)
        if composition is None:
            continue
        if composition.studies:
            scope.add_studies(composition.studies)
        if composition.assays:
            scope.add_assays(composition.assays)


def _apply_upload_aborted(
    state: ArcStreamState,
    scope: RepositoryScope,
    detail: str,
) -> None:
    """Record failures when harvest_arcs aborts before a normal result."""
    if state.submitted == 0:
        scope.record_repository_issue(detail)
        return
    for inv_id in state.submitted_ids:
        scope.record_failed(detail, record_id=inv_id)


def _fail_drained_queue(
    built_queue: asyncio.Queue[BuiltArc | None],
    scope: RepositoryScope,
    detail: str,
    *,
    already_recorded: set[str],
) -> None:
    """Mark ARCs left on the build queue as failed after a harvest abort."""
    while True:
        try:
            item = built_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        if item is None:
            break
        if item.investigation_id in already_recorded:
            continue
        scope.record_failed(detail, record_id=item.investigation_id)
        already_recorded.add(item.investigation_id)


async def _build_single_arc(
    ctx: WorkerContext,
    investigation: InvestigationRow,
    *,
    scope: RepositoryScope,
    inv_info: str,
    semaphore: asyncio.Semaphore,
) -> BuiltArc | None:
    """
    Build one ARC in the process pool.

    Returns a ``BuiltArc`` on success. Build/skip failures are recorded on
    ``scope`` and return ``None`` so they never enter the harvest stream.
    """
    inv_id = str(investigation.identifier)
    async with semaphore:
        studies = ctx.studies_by_inv.get(inv_id, [])
        assays = ctx.assays_by_inv.get(inv_id, [])

        if len(studies) > ctx.max_studies:
            logger.warning(
                "%s: Skipping investigation %s: %d studies exceed max_studies=%d",
                inv_info,
                inv_id,
                len(studies),
                ctx.max_studies,
            )
            scope.record_skipped()
            return None
        if len(assays) > ctx.max_assays:
            logger.warning(
                "%s: Skipping investigation %s: %d assays exceed max_assays=%d",
                inv_info,
                inv_id,
                len(assays),
                ctx.max_assays,
            )
            scope.record_skipped()
            return None

        if assays and not studies:
            logger.warning(
                "%s: Investigation %s has assays but no studies. This is allowed but unusual.", inv_info, inv_id
            )

        build_data = ArcBuildData(
            investigation_row=investigation,
            studies=studies,
            assays=assays,
            contacts=ctx.contacts_by_inv.get(inv_id, []),
            publications=ctx.pubs_by_inv.get(inv_id, []),
            annotations=ctx.anns_by_inv.get(inv_id, []),
        )

        loop = asyncio.get_running_loop()
        try:
            executor = ctx.pool_holder.get_executor()
            arc_json = await asyncio.wait_for(
                loop.run_in_executor(executor, build_single_arc_task, build_data),
                timeout=getattr(ctx, "arc_generation_timeout_minutes", 30) * 60,
            )

            if arc_json is None:
                logger.error("%s: Build returned None for investigation %s", inv_info, inv_id)
                scope.record_failed("Build returned no ARC JSON", record_id=inv_id)
                return None

            logger.info("%s: ARC JSON created: size=%.2fKB", inv_info, len(arc_json.encode("utf-8")) / 1024)
            return BuiltArc(
                arc_json=arc_json,
                investigation_id=inv_id,
                inv_info=inv_info,
                composition=CompositionCounts(studies=len(studies), assays=len(assays)),
            )

        except TimeoutError:
            logger.error("%s: ARC generation timed out for investigation %s", inv_info, inv_id)
            scope.record_failed("ARC generation timed out", record_id=inv_id)
        except DuplicateAssayRowError as e:
            fields = ", ".join(e.fields)
            logger.error(
                "%s: Conflicting duplicate vAssay rows for assay %s (fields: %s) in investigation %s",
                inv_info,
                e.assay_id,
                fields,
                inv_id,
            )
            scope.record_failed(
                f"Conflicting duplicate vAssay rows for assay {e.assay_id} (fields: {fields})",
                record_id=inv_id,
            )
        except DuplicateStudyRowError as e:
            fields = ", ".join(e.fields)
            logger.error(
                "%s: Conflicting duplicate vStudy rows for study %s (fields: %s) in investigation %s",
                inv_info,
                e.study_id,
                fields,
                inv_id,
            )
            scope.record_failed(
                f"Conflicting duplicate vStudy rows for study {e.study_id} (fields: {fields})",
                record_id=inv_id,
            )
        except concurrent.futures.BrokenExecutor as e:
            logger.error(
                "%s: Worker process died while building investigation %s "
                "(likely OOM or crash in arctrl; process pool was reset): %s",
                inv_info,
                inv_id,
                e,
                exc_info=True,
            )
            ctx.pool_holder.recreate(executor)
            scope.record_failed(f"Worker process died: {e}", record_id=inv_id)
        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            # arctrl often raises bare Exception (e.g. duplicate study names); keep the run going.
            logger.error("%s: Failed to build ARC for investigation %s: %s", inv_info, inv_id, e, exc_info=True)
            scope.record_failed(f"Build failed: {e}", record_id=inv_id)
        return None


@dataclass(slots=True)
class WorkerResources:
    """Orchestration resources shared across investigation tasks."""

    client: ApiClient
    config: Config
    scope: RepositoryScope
    pool_holder: ProcessPoolHolder
    semaphore: asyncio.Semaphore
    built_queue: asyncio.Queue[BuiltArc | None]


async def process_investigation(
    ctx: WorkerContext,
    investigation: InvestigationRow,
    inv_info: str,
    res: WorkerResources,
) -> None:
    """Build a single investigation and enqueue it for harvest upload."""
    tracer = trace.get_tracer(__name__)
    inv_id = str(investigation.identifier)
    scope = res.scope
    semaphore = res.semaphore
    built_queue = res.built_queue

    with tracer.start_as_current_span(
        "build_investigation",
        attributes={"investigation_id": inv_id, "worker_id": ctx.worker_id},
    ):
        logger.info("%s: Building ARC for investigation %s...", inv_info, inv_id)
        try:
            built = await _build_single_arc(
                ctx,
                investigation,
                scope=scope,
                inv_info=inv_info,
                semaphore=semaphore,
            )
            if built is None:
                return
            try:
                payload = json.loads(built.arc_json)
            except json.JSONDecodeError as e:
                logger.error(
                    "%s: Invalid ARC JSON for investigation %s: %s",
                    inv_info,
                    inv_id,
                    e,
                    exc_info=True,
                )
                scope.record_failed(f"Invalid ARC JSON: {e}", record_id=inv_id)
                return
            if not isinstance(payload, dict):
                logger.error("%s: ARC JSON for investigation %s is not an object", inv_info, inv_id)
                scope.record_failed("ARC JSON is not an object", record_id=inv_id)
                return
            await built_queue.put(built)
        except asyncio.CancelledError:
            scope.record_failed("Build cancelled after harvest abort", record_id=inv_id)
            raise


async def _fetch_and_group_related_data(db: Database, investigation_ids: list[str]) -> RelatedDataBatch:
    """Fetch related data in bulk and group by investigation ID."""
    logger.info("Fetching related data (studies, assays, contacts, etc.)...")

    async def group_stream(
        gen: AsyncGenerator[Any, None],
    ) -> tuple[dict[str, list[Any]], int]:
        """Consume an async generator and group items by investigation reference."""
        m = defaultdict(list)
        count = 0
        async for r in gen:
            inv_ref = r.investigation_ref
            m[str(inv_ref)].append(r)
            count += 1
        return dict(m), count

    studies_by_inv, study_count = await group_stream(db.stream_studies(investigation_ids))
    assays_by_inv, assay_count = await group_stream(db.stream_assays(investigation_ids))
    contacts_by_inv, _ = await group_stream(db.stream_contacts(investigation_ids))
    pubs_by_inv, _ = await group_stream(db.stream_publications(investigation_ids))
    anns_by_inv, _ = await group_stream(db.stream_annotation_tables(investigation_ids))

    return RelatedDataBatch(
        studies_by_inv=studies_by_inv,
        assays_by_inv=assays_by_inv,
        contacts_by_inv=contacts_by_inv,
        pubs_by_inv=pubs_by_inv,
        anns_by_inv=anns_by_inv,
        study_count=study_count,
        assay_count=assay_count,
    )


def _spawn_investigation_task(
    investigation: InvestigationRow,
    idx: int,
    batch_data: RelatedDataBatch,
    res: WorkerResources,
    running_tasks: set[asyncio.Task[None]],
) -> None:
    """Create worker context and spawn a processing task."""
    ctx = WorkerContext(
        client=res.client,
        rdi=res.config.rdi,
        studies_by_inv=batch_data.studies_by_inv,
        assays_by_inv=batch_data.assays_by_inv,
        contacts_by_inv=batch_data.contacts_by_inv,
        pubs_by_inv=batch_data.pubs_by_inv,
        anns_by_inv=batch_data.anns_by_inv,
        worker_id=idx % res.config.max_concurrent_arc_builds,
        total_workers=res.config.max_concurrent_arc_builds,
        pool_holder=res.pool_holder,
        arc_generation_timeout_minutes=res.config.arc_generation_timeout_minutes,
        max_studies=res.config.max_studies,
        max_assays=res.config.max_assays,
    )

    inv_info = f"Investigation {idx}"
    task = asyncio.create_task(process_investigation(ctx, investigation, inv_info, res))
    running_tasks.add(task)

    def _on_task_done(done: asyncio.Task[None]) -> None:
        running_tasks.discard(done)
        if done.cancelled():
            return
        exc = done.exception()
        if exc is not None:
            # Should be rare: process_investigation is expected to swallow per-investigation failures.
            logger.error("%s: Unhandled task failure: %s", inv_info, exc, exc_info=exc)

    task.add_done_callback(_on_task_done)


async def _cancel_running_builds(running_tasks: set[asyncio.Task[None]]) -> None:
    """Cancel outstanding investigation build tasks and wait for them to finish."""
    if not running_tasks:
        return
    for task in running_tasks:
        task.cancel()
    await asyncio.gather(*running_tasks, return_exceptions=True)
    running_tasks.clear()


async def _drive_builds(
    db: Database,
    config: Config,
    res: WorkerResources,
) -> None:
    """Stream DB batches, build ARCs concurrently, and enqueue successful builds."""
    running_tasks: set[asyncio.Task[None]] = set()
    inv_idx = 0
    investigation_gen = db.stream_investigations(scope=res.scope, limit=config.debug_limit)

    try:
        while True:
            batch = []
            try:
                for _ in range(config.db_batch_size):
                    try:
                        batch.append(await anext(investigation_gen))
                    except StopAsyncIteration:
                        break
            except (RuntimeError, OSError, ConnectionError) as e:
                logger.error("Database or connection error while fetching investigations: %s", e, exc_info=True)
                raise
            except Exception as e:
                logger.error("Unexpected error while fetching investigations: %s", e, exc_info=True)
                raise

            if not batch:
                break

            if len(running_tasks) >= config.max_concurrent_tasks:
                await asyncio.wait(running_tasks, return_when=asyncio.FIRST_COMPLETED)

            batch_data = await _fetch_and_group_related_data(db, [str(inv.identifier) for inv in batch])

            for investigation in batch:
                inv_idx += 1
                _spawn_investigation_task(
                    investigation,
                    inv_idx,
                    batch_data,
                    res,
                    running_tasks,
                )

        if running_tasks:
            logger.info("Waiting for %d remaining build tasks to complete...", len(running_tasks))
            await asyncio.gather(*running_tasks)
    finally:
        # Stop any still-running investigation builds (e.g. when the driver is cancelled
        # after a harvest abort) before closing the queue for consumers.
        await _cancel_running_builds(running_tasks)
        await res.built_queue.put(None)


async def _arc_stream_from_queue(
    built_queue: asyncio.Queue[BuiltArc | None],
    state: ArcStreamState,
) -> AsyncGenerator[dict[str, Any], None]:
    """Yield ARC dicts for harvest_arcs from the build queue."""
    while True:
        item = await built_queue.get()
        if item is None:
            return
        arc_payload = json.loads(item.arc_json)
        if not isinstance(arc_payload, dict):
            # Defensive: process_investigation validates before enqueue.
            continue
        state.track(item, arc_payload)
        logger.info(
            "%s: Queued ARC %s for harvest upload (%.2f KB)",
            item.inv_info,
            item.investigation_id,
            len(item.arc_json.encode("utf-8")) / 1024,
        )
        yield arc_payload


async def _run_harvest_upload(
    res: WorkerResources,
    state: ArcStreamState,
    expected_datasets: int | None,
) -> str | None:
    """Run harvest_arcs and apply success outcomes. Returns an error detail on failure."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(
        "harvest_upload",
        attributes={"rdi": res.config.rdi},
    ) as upload_span:
        try:
            result = await res.client.harvest_arcs(
                rdi=res.config.rdi,
                arcs=_arc_stream_from_queue(res.built_queue, state),
                expected_datasets=expected_datasets,
            )
            harvest_id = result.harvest_id
            res.scope.set_harvest_id(harvest_id)
            _apply_upload_outcomes(result.errors, state, res.scope)
            upload_span.set_attribute("harvester.harvest_id", harvest_id)
            upload_span.set_attribute("harvester.arcs_submitted", state.submitted)
            logger.info(
                "Finished harvest upload for RDI %s. Harvest: %s (submitted=%d, errors=%d)",
                res.config.rdi,
                harvest_id,
                state.submitted,
                len(result.errors),
            )
            return None
        except (ConnectionError, TimeoutError, ApiClientError, OSError, RuntimeError) as e:
            upload_span.set_status(Status(StatusCode.ERROR))
            upload_span.record_exception(e)
            detail = f"Harvest upload failed: {e}"
            logger.error("%s", detail, exc_info=True)
            return detail
        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            upload_span.set_status(Status(StatusCode.ERROR))
            upload_span.record_exception(e)
            detail = f"Harvest upload failed: {e}"
            logger.error("%s", detail, exc_info=True)
            return detail


async def _finalize_build_pipeline(
    build_task: asyncio.Task[None],
    res: WorkerResources,
    state: ArcStreamState,
    upload_error: str | None,
) -> None:
    """Cancel/await builds and record failures for any leftover queued ARCs."""
    if not build_task.done():
        build_task.cancel()
    try:
        await build_task
    except asyncio.CancelledError:
        logger.info("Build pipeline cancelled after harvest upload abort")

    if upload_error is None:
        return
    _apply_upload_aborted(state, res.scope, upload_error)
    _fail_drained_queue(
        res.built_queue,
        res.scope,
        upload_error,
        already_recorded=set(state.submitted_ids),
    )


async def process_investigations(
    db: Database,
    client: ApiClient,
    config: Config,
) -> HarvestReport:
    """Fetch investigations from DB, build ARCs, and upload via harvest_arcs."""
    report = HarvestReport(name="SQL to ARC Conversion Run")
    scope = report.open_repository(config.rdi)

    expected_count = await db.count_investigations()
    _apply_expected_datasets(scope, expected_count, config.debug_limit)
    expected_datasets = scope.snapshot().expected_datasets

    logger.info(
        "Starting SQL-to-ARC processing: CPU_workers=%d, Max_tasks=%d, Batch_size=%d",
        config.max_concurrent_arc_builds,
        config.max_concurrent_tasks,
        config.db_batch_size,
    )

    built_queue: asyncio.Queue[BuiltArc | None] = asyncio.Queue(
        maxsize=max(1, config.max_concurrent_tasks),
    )
    state = ArcStreamState()
    tracer = trace.get_tracer(__name__)

    with (
        ProcessPoolHolder(
            max_workers=config.max_concurrent_arc_builds,
            mp_context=multiprocessing.get_context("spawn"),
        ) as pool_holder,
        tracer.start_as_current_span("process_investigations"),
    ):
        worker_res = WorkerResources(
            client=client,
            config=config,
            scope=scope,
            pool_holder=pool_holder,
            semaphore=asyncio.Semaphore(config.max_concurrent_tasks),
            built_queue=built_queue,
        )
        build_task = asyncio.create_task(_drive_builds(db, config, worker_res))
        upload_error: str | None = None

        try:
            upload_error = await _run_harvest_upload(worker_res, state, expected_datasets)
        except asyncio.CancelledError:
            if upload_error is None:
                upload_error = "Harvest upload cancelled"
            raise
        finally:
            await _finalize_build_pipeline(build_task, worker_res, state, upload_error)

    report.finish()
    return report
