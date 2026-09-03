"""Orchestration and worker management for the SQL-to-ARC conversion process."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import multiprocessing
from dataclasses import dataclass, field
from typing import cast

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from middleware.api_client import ApiClient, ApiClientError, HarvestError
from middleware.shared.json_types import RoCrateContent
from middleware.shared.report import HarvestReport, RepositoryScope
from middleware.sql_to_arc.builder import DuplicateAssayRowError, DuplicateStudyRowError, build_single_arc_task
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.context import ArcBuildData, WorkerContext
from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.models import InvestigationRow
from middleware.sql_to_arc.pipeline import (
    BuiltArc,
    CompositionCounts,
    WorkerResources,
    drain_unsubmitted_arcs,
    drive_builds,
    stream_arcs_from_queue,
)
from middleware.sql_to_arc.process_pool import ProcessPoolHolder

logger = logging.getLogger(__name__)


def _apply_expected_datasets(scope: RepositoryScope, count: int | None, debug_limit: int | None) -> None:
    """Set expected datasets on the scope when a count is known."""
    if not isinstance(count, int):
        return
    expected = min(count, debug_limit) if isinstance(debug_limit, int) else count
    scope.set_expected_datasets(expected)


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

    def track(self, built: BuiltArc) -> None:
        """Record metadata for a yielded ARC payload."""
        self.submitted_ids.append(built.investigation_id)
        self.compositions[built.investigation_id] = built.composition
        raw_id = built.arc_payload.get("identifier")
        if isinstance(raw_id, str) and raw_id:
            self.arc_id_to_investigation[raw_id] = built.investigation_id
        # Also map investigation id itself for clients that echo it as arc_id.
        self.arc_id_to_investigation.setdefault(built.investigation_id, built.investigation_id)


def _apply_upload_outcomes(errors: list[HarvestError], state: ArcStreamState, scope: RepositoryScope) -> None:
    """Apply harvest_arcs per-item errors and successes to the repository scope."""
    failed_ids: set[str] = set()
    for err in errors:
        arc_id = err.arc_id
        record_id = state.arc_id_to_investigation.get(arc_id) if isinstance(arc_id, str) and arc_id else None
        if record_id is None:
            # Cannot attribute to a dataset — record as repository issue, not a dataset failure.
            scope.record_repository_issue(f"Unattributed harvest error: {err.message}")
            continue
        scope.record_failed(err.message, record_id=record_id)
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


def _built_arc_from_json(
    arc_json: str,
    *,
    inv_id: str,
    inv_info: str,
    composition: CompositionCounts,
    scope: RepositoryScope,
) -> BuiltArc | None:
    """Validate ARC JSON and wrap it as a ``BuiltArc``, or record failure and return None."""
    try:
        payload = json.loads(arc_json)
    except json.JSONDecodeError as e:
        logger.error("%s: Invalid ARC JSON for investigation %s: %s", inv_info, inv_id, e, exc_info=True)
        scope.record_failed(f"Invalid ARC JSON: {e}", record_id=inv_id)
        return None
    if not isinstance(payload, dict):
        logger.error("%s: ARC JSON for investigation %s is not an object", inv_info, inv_id)
        scope.record_failed("ARC JSON is not an object", record_id=inv_id)
        return None
    logger.info("%s: ARC JSON created: size=%.2fKB", inv_info, len(arc_json.encode("utf-8")) / 1024)
    return BuiltArc(
        arc_payload=cast(RoCrateContent, payload),
        investigation_id=inv_id,
        inv_info=inv_info,
        composition=composition,
    )


async def _build_single_arc(
    ctx: WorkerContext,
    investigation: InvestigationRow,
    *,
    scope: RepositoryScope,
    inv_info: str,
    semaphore: asyncio.Semaphore,
) -> BuiltArc | None:
    """Build one ARC in the process pool.

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
                "%s: Investigation %s has assays but no studies. This is allowed but unusual.",
                inv_info,
                inv_id,
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
        executor = ctx.pool_holder.get_executor()
        try:
            arc_json = await asyncio.wait_for(
                loop.run_in_executor(executor, build_single_arc_task, build_data),
                timeout=getattr(ctx, "arc_generation_timeout_minutes", 30) * 60,
            )
            if arc_json is None:
                logger.error("%s: Build returned None for investigation %s", inv_info, inv_id)
                scope.record_failed("Build returned no ARC JSON", record_id=inv_id)
                return None
            return _built_arc_from_json(
                arc_json,
                inv_id=inv_id,
                inv_info=inv_info,
                composition=CompositionCounts(studies=len(studies), assays=len(assays)),
                scope=scope,
            )
        except TimeoutError:
            logger.error("%s: ARC generation timed out for investigation %s", inv_info, inv_id)
            scope.record_failed("ARC generation timed out", record_id=inv_id)
        except (DuplicateAssayRowError, DuplicateStudyRowError) as e:
            if isinstance(e, DuplicateAssayRowError):
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
            else:
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
            # asyncio.CancelledError is BaseException (3.8+) and is not caught here.
            logger.error("%s: Failed to build ARC for investigation %s: %s", inv_info, inv_id, e, exc_info=True)
            scope.record_failed(f"Build failed: {e}", record_id=inv_id)
        return None


async def process_investigation(
    ctx: WorkerContext,
    investigation: InvestigationRow,
    inv_info: str,
    res: WorkerResources,
) -> None:
    """Build a single investigation and enqueue it for harvest upload."""
    tracer = trace.get_tracer(__name__)
    inv_id = str(investigation.identifier)

    with tracer.start_as_current_span(
        "build_investigation",
        attributes={"investigation_id": inv_id, "worker_id": ctx.worker_id},
    ):
        logger.info("%s: Building ARC for investigation %s...", inv_info, inv_id)
        try:
            built = await _build_single_arc(
                ctx,
                investigation,
                scope=res.scope,
                inv_info=inv_info,
                semaphore=res.semaphore,
            )
            if built is not None:
                await res.built_queue.put(built)
        except asyncio.CancelledError:
            res.scope.record_failed("Build cancelled after harvest abort", record_id=inv_id)
            raise


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
                arcs=stream_arcs_from_queue(res.built_queue, state),
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
            # asyncio.CancelledError is BaseException (3.8+) and is not caught here.
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
    already_recorded = set(state.submitted_ids)
    for item in res.displaced_arcs:
        if item.investigation_id in already_recorded:
            continue
        res.scope.record_failed(upload_error, record_id=item.investigation_id)
        already_recorded.add(item.investigation_id)
    drain_unsubmitted_arcs(
        res.built_queue,
        res.scope,
        upload_error,
        already_recorded=already_recorded,
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
            process_investigation=process_investigation,
        )
        build_task = asyncio.create_task(drive_builds(db, config, worker_res))
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
