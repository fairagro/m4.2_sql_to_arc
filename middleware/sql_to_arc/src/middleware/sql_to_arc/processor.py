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
from middleware.sql_to_arc.builder import DuplicateAssayRowError, build_single_arc_task
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.context import (
    ArcBuildData,
    RelatedDataBatch,
    WorkerContext,
)
from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.models import InvestigationRow
from middleware.sql_to_arc.process_pool import ProcessPoolHolder
from middleware.sql_to_arc.stats import ProcessingStats

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def _upload_and_update_stats(
    ctx: WorkerContext,
    arc_json: str,
    investigation_id: str,
    stats: ProcessingStats,
    inv_info: str,
) -> None:
    """Upload ARC and update statistics."""
    tracer = trace.get_tracer(__name__)
    try:
        with tracer.start_as_current_span(
            "upload_arc", attributes={"rdi": ctx.rdi, "worker_id": ctx.worker_id, "investigation_id": investigation_id}
        ):
            # Parse JSON back to dict for the API client (it will serialize again,
            # but we need the dict for validation/processing)
            arc_dict = json.loads(arc_json)

            await ctx.client.create_or_update_arc(
                rdi=ctx.rdi,
                arc=arc_dict,
            )

        logger.info("%s: Upload request finished. API reported success for ARC %s.", inv_info, investigation_id)

    except (ConnectionError, TimeoutError, ApiClientError) as e:
        size_kb = len(arc_json.encode("utf-8")) / 1024
        logger.error(
            "%s: Failed to upload ARC %s (%.2f KB). Check api_client.timeout if this is httpx.ReadTimeout: %s",
            inv_info,
            investigation_id,
            size_kb,
            e,
            exc_info=True,
        )
        stats.failed_datasets += 1
        stats.failed_ids.append(investigation_id)


async def _build_and_upload_single_arc(
    ctx: WorkerContext,
    investigation: InvestigationRow,
    *,
    stats: ProcessingStats,
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

    Args:
        ctx: Context containing executors and pre-fetched data.
        investigation: The metadata row for the investigation.
        stats: Global stats object to update on success/failure.
        inv_info: Logging prefix for traceability.
        semaphore: Semaphore to limit concurrent processing.
    """
    inv_id = str(investigation.identifier)
    # Acquire semaphore to limit concurrency
    async with semaphore:
        # Prepare data bundle for this investigation
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

        # Build ARC in executor
        loop = asyncio.get_event_loop()
        try:
            # Replaced direct ARC transfer with JSON transfer from worker
            # Note: build_single_arc_task now returns a JSON string
            arc_json = await asyncio.wait_for(
                loop.run_in_executor(ctx.pool_holder.get_executor(), build_single_arc_task, build_data),
                timeout=getattr(ctx, "arc_generation_timeout_minutes", 30) * 60,
            )

            if arc_json is None:
                logger.error("%s: Build returned None for investigation %s", inv_info, inv_id)
                stats.failed_datasets += 1
                stats.failed_ids.append(inv_id)
                return

            logger.info("%s: ARC JSON created: size=%.2fKB", inv_info, len(arc_json.encode("utf-8")) / 1024)

            # Upload single ARC
            await _upload_and_update_stats(ctx, arc_json, inv_id, stats, inv_info)

        except TimeoutError:
            logger.error("%s: ARC generation timed out for investigation %s", inv_info, inv_id)
            stats.failed_datasets += 1
            stats.failed_ids.append(inv_id)
        except DuplicateAssayRowError as e:
            logger.error(
                "%s: Conflicting duplicate vAssay rows for assay %s (fields: %s) in investigation %s",
                inv_info,
                e.assay_id,
                ", ".join(e.fields),
                inv_id,
            )
            stats.failed_datasets += 1
            stats.failed_ids.append(inv_id)
        except concurrent.futures.BrokenExecutor as e:
            logger.error(
                "%s: Worker process died while building investigation %s "
                "(likely OOM or crash in arctrl; process pool was reset): %s",
                inv_info,
                inv_id,
                e,
                exc_info=True,
            )
            ctx.pool_holder.recreate(ctx.pool_holder.get_executor())
            stats.failed_datasets += 1
            stats.failed_ids.append(inv_id)
        except (ValueError, RuntimeError) as e:
            logger.error("%s: Failed to build ARC for investigation %s: %s", inv_info, inv_id, e)
            stats.failed_datasets += 1
            stats.failed_ids.append(inv_id)


async def process_investigation(
    ctx: WorkerContext,
    investigation: InvestigationRow,
    stats: ProcessingStats,
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
            stats=stats,
            inv_info=inv_info,
            semaphore=semaphore,
        )


async def _fetch_and_group_related_data(db: Database, investigation_ids: list[str]) -> RelatedDataBatch:
    """Fetch related data in bulk and group by investigation ID."""
    logger.info("Fetching related data (studies, assays, contacts, etc.)...")

    async def group_stream(
        gen: AsyncGenerator[Any, None],
    ) -> tuple[dict[str, list[Any]], int]:
        """
        Help to consume an async generator and group items by their investigation reference.

        This organizes relational data (like Studies or Assays) into a lookup table where
        the key is the 'investigation_ref'. This is essential for the 1:N mapping during
        ARC construction.
        """
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
    stats: ProcessingStats
    pool_holder: ProcessPoolHolder
    semaphore: asyncio.Semaphore


def _spawn_investigation_task(
    investigation: InvestigationRow,
    idx: int,
    batch_data: RelatedDataBatch,
    res: WorkerResources,
    running_tasks: set[asyncio.Task[None]],
) -> None:
    """
    Create worker context and spawn a processing task.

    Args:
        investigation: The data row from DB representing the research dataset.
        idx: The global sequence number of this investigation (used for logging context).
        batch_data: The pre-fetched relational data (studies, assays, etc.) for the current batch.
        res: Shared resources (API client, config, stats, executor, semaphore).
        running_tasks: The set of currently active asyncio tasks for backpressure tracking.
    """
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

    # Logging Context: 'inv_info' provides a human-readable prefix (e.g. "Investigation 42")
    # that is passed down to sub-functions to keep log entries traceable back to their origin
    # without repeating the logic of generating this string everywhere.
    inv_info = f"Investigation {idx}"
    # MUTABLE ARGUMENTS: Note that 'res.stats' and 'running_tasks' are passed by reference.
    # The 'process_investigation' task will update 'res.stats' directly on failure
    # and 'running_tasks' will automatically discard this task via its done_callback.
    task = asyncio.create_task(process_investigation(ctx, investigation, res.stats, inv_info, res.semaphore))
    running_tasks.add(task)
    # Self-cleanup: When the task is finished (success or failure), it removes itself
    # from the 'running_tasks' set to free up slots for the next batch.
    task.add_done_callback(running_tasks.discard)


async def process_investigations(
    db: Database,
    client: ApiClient,
    config: Config,
) -> ProcessingStats:
    """Fetch investigations from DB and process them concurrently with flow control."""
    stats = ProcessingStats()
    # 1. Flow Control: Use a semaphore to limit the number of active tasks.
    # This prevents the application from reading too much data into RAM at once.
    semaphore = asyncio.Semaphore(config.max_concurrent_tasks)

    logger.info(
        "Starting SQL-to-ARC processing: CPU_workers=%d, Max_tasks=%d, Batch_size=%d",
        config.max_concurrent_arc_builds,
        config.max_concurrent_tasks,
        config.db_batch_size,
    )

    # 2. Parallelization: Process pool for CPU-intensive ARC generation (recreatable on worker crash).
    pool_holder = ProcessPoolHolder(
        max_workers=config.max_concurrent_arc_builds,
        mp_context=multiprocessing.get_context("spawn"),
    )
    with trace.get_tracer(__name__).start_as_current_span("process_investigations"):
        running_tasks: set[asyncio.Task[None]] = set()
        inv_idx = 0
        # Initialize the streaming generator for investigations
        investigation_gen = db.stream_investigations(stats=stats, limit=config.debug_limit)

        while True:
            # 3. Memory-Efficient Fetching: Get a chunk of investigations from the generator.
            # We fetch in batches to balance between DB roundtrips and RAM usage.
            # 'anext' is used to manually advance the async generator.
            batch = []
            try:
                for _ in range(config.db_batch_size):
                    try:
                        # Fetch next investigation from the server-side cursor
                        batch.append(await anext(investigation_gen))
                    except StopAsyncIteration:
                        # End of stream reached, triggered by 'anext'
                        break
            except (RuntimeError, OSError, ConnectionError) as e:
                logger.error("Database or connection error while fetching investigations: %s", e, exc_info=True)
                break
            except Exception as e:
                logger.error("Unexpected error while fetching investigations: %s", e, exc_info=True)
                raise

            if not batch:
                break

            # 4. Backpressure: If we reached the task limit, wait for at least one to finish.
            # This is crucial for throttling the 'Producer' (the DB generator).
            if len(running_tasks) >= config.max_concurrent_tasks:
                await asyncio.wait(running_tasks, return_when=asyncio.FIRST_COMPLETED)

            # 5. Relational Batching: Fetch ALL related data (Studies, Assays, etc.)
            # for the entire batch in ONE go to avoid N+1 query performance hits.
            batch_data = await _fetch_and_group_related_data(db, [str(inv.identifier) for inv in batch])
            stats.total_studies += batch_data.study_count
            stats.total_assays += batch_data.assay_count

            # 6. Resource Injection: Bundle dependencies to pass them to worker tasks.
            res = WorkerResources(
                client=client,
                config=config,
                stats=stats,
                pool_holder=pool_holder,
                semaphore=semaphore,
            )

            # 7. Task Execution: Spawn an asynchronous task for each investigation.
            # Each task will later use the Semaphore to enter the Process Pool.
            # IN-PLACE UPDATES: These tasks will directly update 'stats' and
            # manage their own lifecycle within 'running_tasks'.
            for investigation in batch:
                inv_idx += 1
                _spawn_investigation_task(
                    investigation,
                    inv_idx,
                    batch_data,
                    res,
                    running_tasks,
                )

        # 8. Cleanup: Wait for all remaining background tasks (uploads, builds) to finish.
        if running_tasks:
            logger.info("Waiting for %d remaining tasks to complete...", len(running_tasks))
            await asyncio.gather(*running_tasks)

        pool_holder.shutdown()

    return stats
