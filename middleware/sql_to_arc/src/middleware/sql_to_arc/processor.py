"""Orchestration and worker management for the SQL-to-ARC conversion process."""

import asyncio
import concurrent.futures
import json
import logging
import multiprocessing
from collections import defaultdict
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, TypeVar

from opentelemetry import trace
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
class _CompositionCounts:
    """Study/assay counts for one successfully harvested investigation."""

    studies: int
    assays: int


@dataclass(frozen=True, slots=True)
class _UploadRequest:
    """Inputs for a single ARC upload + scope update."""

    arc_json: str
    investigation_id: str
    inv_info: str
    composition: _CompositionCounts


async def _upload_and_update_scope(
    ctx: WorkerContext,
    scope: RepositoryScope,
    request: _UploadRequest,
) -> None:
    """Upload ARC and record harvested/failed on the repository scope."""
    tracer = trace.get_tracer(__name__)
    try:
        with tracer.start_as_current_span(
            "upload_arc",
            attributes={
                "rdi": ctx.rdi,
                "worker_id": ctx.worker_id,
                "investigation_id": request.investigation_id,
            },
        ):
            arc_dict = json.loads(request.arc_json)

            result = await ctx.client.create_or_update_arc(
                rdi=ctx.rdi,
                arc=arc_dict,
            )

        # create_or_update_arc has no harvest id today; wire the setter when one appears.
        harvest_id = getattr(result, "harvest_id", None)
        if isinstance(harvest_id, str) and harvest_id:
            scope.set_harvest_id(harvest_id)

        scope.record_harvested()
        if request.composition.studies:
            scope.add_studies(request.composition.studies)
        if request.composition.assays:
            scope.add_assays(request.composition.assays)

        logger.info(
            "%s: Upload request finished. API reported success for ARC %s.",
            request.inv_info,
            request.investigation_id,
        )

    except json.JSONDecodeError as e:
        logger.error(
            "%s: Invalid ARC JSON for investigation %s: %s",
            request.inv_info,
            request.investigation_id,
            e,
            exc_info=True,
        )
        scope.record_failed(f"Invalid ARC JSON: {e}", record_id=request.investigation_id)
    except (ConnectionError, TimeoutError, ApiClientError) as e:
        size_kb = len(request.arc_json.encode("utf-8")) / 1024
        logger.error(
            "%s: Failed to upload ARC %s (%.2f KB). Check api_client.timeout if this is httpx.ReadTimeout: %s",
            request.inv_info,
            request.investigation_id,
            size_kb,
            e,
            exc_info=True,
        )
        scope.record_failed(f"Upload failed: {e}", record_id=request.investigation_id)


async def _build_and_upload_single_arc(
    ctx: WorkerContext,
    investigation: InvestigationRow,
    *,
    scope: RepositoryScope,
    inv_info: str,
    semaphore: asyncio.Semaphore,
) -> None:
    """
    Orchestrate the creation and transmission of a single ARC.

    This function handles the lifecycle of one research dataset:
    1. Acquires a semaphore slot (concurrency control).
    2. Gathers pre-fetched relational data into a bundle.
    3. Offloads the CPU-intensive ARC generation to a Process Pool.
    4. Uploads the resulting JSON to the Middleware API.
    """
    inv_id = str(investigation.identifier)
    async with semaphore:
        studies = ctx.studies_by_inv.get(inv_id, [])
        assays = ctx.assays_by_inv.get(inv_id, [])

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
                return

            logger.info("%s: ARC JSON created: size=%.2fKB", inv_info, len(arc_json.encode("utf-8")) / 1024)

            await _upload_and_update_scope(
                ctx,
                scope,
                _UploadRequest(
                    arc_json=arc_json,
                    investigation_id=inv_id,
                    inv_info=inv_info,
                    composition=_CompositionCounts(studies=len(studies), assays=len(assays)),
                ),
            )

        except TimeoutError:
            logger.error("%s: ARC generation timed out for investigation %s", inv_info, inv_id)
            scope.record_failed("ARC generation timed out", record_id=inv_id)
        except DuplicateAssayRowError as e:
            logger.error(
                "%s: Conflicting duplicate vAssay rows for assay %s (fields: %s) in investigation %s",
                inv_info,
                e.assay_id,
                ", ".join(e.fields),
                inv_id,
            )
            scope.record_failed(
                f"Conflicting duplicate vAssay rows for assay {e.assay_id}",
                record_id=inv_id,
            )
        except DuplicateStudyRowError as e:
            logger.error(
                "%s: Conflicting duplicate vStudy rows for study %s (fields: %s) in investigation %s",
                inv_info,
                e.study_id,
                ", ".join(e.fields),
                inv_id,
            )
            scope.record_failed(
                f"Conflicting duplicate vStudy rows for study {e.study_id}",
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


async def process_investigation(
    ctx: WorkerContext,
    investigation: InvestigationRow,
    scope: RepositoryScope,
    inv_info: str,
    semaphore: asyncio.Semaphore,
) -> None:
    """Process a single investigation."""
    tracer = trace.get_tracer(__name__)
    inv_id = str(investigation.identifier)

    with tracer.start_as_current_span(
        "build_investigation",
        attributes={"investigation_id": inv_id, "worker_id": ctx.worker_id},
    ):
        logger.info("%s: Building ARC for investigation %s...", inv_info, inv_id)
        await _build_and_upload_single_arc(
            ctx,
            investigation,
            scope=scope,
            inv_info=inv_info,
            semaphore=semaphore,
        )


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


@dataclass(slots=True)
class WorkerResources:
    """Orchestration resources shared across investigation tasks."""

    client: ApiClient
    config: Config
    scope: RepositoryScope
    pool_holder: ProcessPoolHolder
    semaphore: asyncio.Semaphore


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
    )

    inv_info = f"Investigation {idx}"
    task = asyncio.create_task(process_investigation(ctx, investigation, res.scope, inv_info, res.semaphore))
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


async def process_investigations(
    db: Database,
    client: ApiClient,
    config: Config,
) -> HarvestReport:
    """Fetch investigations from DB and process them concurrently with flow control."""
    report = HarvestReport(name="SQL to ARC Conversion Run")
    scope = report.open_repository(config.rdi)

    expected_count = await db.count_investigations()
    _apply_expected_datasets(scope, expected_count, config.debug_limit)

    semaphore = asyncio.Semaphore(config.max_concurrent_tasks)

    logger.info(
        "Starting SQL-to-ARC processing: CPU_workers=%d, Max_tasks=%d, Batch_size=%d",
        config.max_concurrent_arc_builds,
        config.max_concurrent_tasks,
        config.db_batch_size,
    )

    with (
        ProcessPoolHolder(
            max_workers=config.max_concurrent_arc_builds,
            mp_context=multiprocessing.get_context("spawn"),
        ) as pool_holder,
        trace.get_tracer(__name__).start_as_current_span("process_investigations"),
    ):
        running_tasks: set[asyncio.Task[None]] = set()
        inv_idx = 0
        investigation_gen = db.stream_investigations(scope=scope, limit=config.debug_limit)

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

            res = WorkerResources(
                client=client,
                config=config,
                scope=scope,
                pool_holder=pool_holder,
                semaphore=semaphore,
            )

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
            logger.info("Waiting for %d remaining tasks to complete...", len(running_tasks))
            await asyncio.gather(*running_tasks)

    report.finish()
    return report
