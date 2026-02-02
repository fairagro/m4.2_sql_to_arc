"""Orchestration and worker management for the SQL-to-ARC conversion process."""

import asyncio
import concurrent.futures
import json
import logging
import multiprocessing
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any

from opentelemetry import trace
from pydantic import BaseModel, ConfigDict

from middleware.api_client import ApiClient, ApiClientError
from middleware.sql_to_arc.builder import build_single_arc_task
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.models import (
    ArcBuildData,
    RelatedDataBatch,
    WorkerContext,
)
from middleware.sql_to_arc.stats import ProcessingStats

logger = logging.getLogger(__name__)


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
        logger.error("%s: Failed to upload ARC %s: %s", inv_info, investigation_id, e, exc_info=True)
        stats.failed_datasets += 1
        stats.failed_ids.append(investigation_id)


async def _build_and_upload_single_arc(
    ctx: WorkerContext,
    investigation: dict[str, Any],
    *,
    stats: ProcessingStats,
    inv_info: str,
    semaphore: asyncio.Semaphore,
) -> None:
    """Build a single ARC and upload it."""
    inv_id = str(investigation["identifier"])
    # Acquire semaphore to limit concurrency
    async with semaphore:
        # Prepare data bundle for this investigation
        build_data = ArcBuildData(
            investigation_row=investigation,
            studies=ctx.studies_by_inv.get(inv_id, []),
            assays=ctx.assays_by_inv.get(inv_id, []),
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
                loop.run_in_executor(ctx.executor, build_single_arc_task, build_data),
                timeout=getattr(ctx, "arc_generation_timeout_minutes", 30) * 60,
            )

            if arc_json is None:
                logger.error("%s: Build returned None for investigation %s", inv_info, inv_id)
                stats.failed_datasets += 1
                stats.failed_ids.append(inv_id)
                return

            json_size_kb = len(arc_json.encode("utf-8")) / 1024
            logger.info("%s: ARC JSON created: size=%.2fKB", inv_info, json_size_kb)

            # Upload single ARC
            await _upload_and_update_stats(ctx, arc_json, inv_id, stats, inv_info)

        except TimeoutError:
            logger.error("%s: ARC generation timed out for investigation %s", inv_info, inv_id)
            stats.failed_datasets += 1
            stats.failed_ids.append(inv_id)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("%s: Failed to build ARC for investigation %s: %s", inv_info, inv_id, e)
            stats.failed_datasets += 1
            stats.failed_ids.append(inv_id)


async def process_investigation(
    ctx: WorkerContext,
    investigation: dict[str, Any],
    stats: ProcessingStats,
    inv_info: str,
    semaphore: asyncio.Semaphore,
) -> None:
    """Process a single investigation."""
    tracer = trace.get_tracer(__name__)
    inv_id = str(investigation["identifier"])

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

    async def group_stream(gen: AsyncGenerator[dict[str, Any], None]) -> tuple[dict[str, list[dict[str, Any]]], int]:
        m = defaultdict(list)
        count = 0
        async for r in gen:
            m[str(r["investigation_ref"])].append(r)
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


class WorkerResources(BaseModel):
    """Orchestration resources shared across investigation tasks."""

    client: ApiClient
    config: Config
    stats: ProcessingStats
    executor: concurrent.futures.Executor
    semaphore: asyncio.Semaphore

    model_config = ConfigDict(arbitrary_types_allowed=True)


def _spawn_investigation_task(
    investigation: dict[str, Any],
    idx: int,
    batch_data: RelatedDataBatch,
    res: WorkerResources,
    running_tasks: set[asyncio.Task],
) -> None:
    """Create worker context and spawn a processing task."""
    res.stats.found_datasets += 1
    ctx = WorkerContext(
        client=res.client,
        rdi=res.config.rdi,
        studies_by_inv=batch_data.studies_by_inv,
        assays_by_inv=batch_data.assays_by_inv,
        contacts_by_inv=batch_data.contacts_by_inv,
        pubs_by_inv=batch_data.pubs_by_inv,
        anns_by_inv=batch_data.anns_by_inv,
        worker_id=1,
        total_workers=res.config.max_concurrent_arc_builds,
        executor=res.executor,
        arc_generation_timeout_minutes=res.config.arc_generation_timeout_minutes,
    )

    inv_info = f"Investigation {idx}"
    task = asyncio.create_task(process_investigation(ctx, investigation, res.stats, inv_info, res.semaphore))
    running_tasks.add(task)
    task.add_done_callback(running_tasks.discard)


async def process_investigations(
    db: Database,
    client: ApiClient,
    config: Config,
) -> ProcessingStats:
    """Fetch investigations from DB and process them concurrently with flow control."""
    stats = ProcessingStats()
    semaphore = asyncio.Semaphore(config.max_concurrent_tasks)

    logger.info(
        "Starting SQL-to-ARC processing: CPU_workers=%d, Max_tasks=%d, Batch_size=%d",
        config.max_concurrent_arc_builds,
        config.max_concurrent_tasks,
        config.db_batch_size,
    )

    with (
        concurrent.futures.ProcessPoolExecutor(
            max_workers=config.max_concurrent_arc_builds,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor,
        trace.get_tracer(__name__).start_as_current_span("process_investigations"),
    ):
        running_tasks: set[asyncio.Task] = set()
        inv_idx = 0
        investigation_gen = db.stream_investigations(limit=config.debug_limit)

        while True:
            batch = []
            try:
                for _ in range(config.db_batch_size):
                    try:
                        batch.append(await anext(investigation_gen))
                    except StopAsyncIteration:
                        break
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Unexpected error while fetching investigations: %s", e, exc_info=True)
                break

            if not batch:
                break

            if len(running_tasks) >= config.max_concurrent_tasks:
                await asyncio.wait(running_tasks, return_when=asyncio.FIRST_COMPLETED)

            # 3. Relational Batching: Fetch all related data for this batch at once
            batch_data = await _fetch_and_group_related_data(db, [str(inv["identifier"]) for inv in batch])
            stats.total_studies += batch_data.study_count
            stats.total_assays += batch_data.assay_count

            # 4. Prepare resources for spawning tasks
            res = WorkerResources(
                client=client,
                config=config,
                stats=stats,
                executor=executor,
                semaphore=semaphore,
            )

            # 5. Spawn tasks for each investigation in the batch
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

    return stats
