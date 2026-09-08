"""Technical pipeline plumbing for SQL-to-ARC orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator, Callable, Coroutine
from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from middleware.api_client import ApiClient
from middleware.shared.json_types import RoCrateContent
from middleware.shared.report import RepositoryScope
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.context import RelatedDataBatch, WorkerContext
from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.models import InvestigationRow
from middleware.sql_to_arc.process_pool import ProcessPoolHolder

logger = logging.getLogger(__name__)

ProcessInvestigation = Callable[
    [WorkerContext, InvestigationRow, str, "WorkerResources"],
    Coroutine[object, object, None],
]


@dataclass(frozen=True, slots=True)
class CompositionCounts:
    """Study/assay counts for one successfully built investigation."""

    studies: int
    assays: int


@dataclass(frozen=True, slots=True)
class BuiltArc:
    """A successfully built ARC waiting to be submitted in the harvest stream."""

    arc_payload: RoCrateContent
    investigation_id: str
    inv_info: str
    composition: CompositionCounts


@dataclass(slots=True)
class WorkerResources:
    """Technical resources shared across build tasks."""

    client: ApiClient
    config: Config
    scope: RepositoryScope
    pool_holder: ProcessPoolHolder
    semaphore: asyncio.Semaphore
    built_queue: asyncio.Queue[BuiltArc | None]
    process_investigation: ProcessInvestigation
    displaced_arcs: list[BuiltArc] = field(default_factory=list)


class _HasInvestigationRef(Protocol):
    """Row models that can be grouped by investigation."""

    investigation_ref: str


class _ArcStreamTracker(Protocol):
    """Minimal state interface needed by the queue consumer."""

    def track(self, built: BuiltArc) -> None: ...


TRow = TypeVar("TRow", bound=_HasInvestigationRef)


def enqueue_queue_sentinel(built_queue: asyncio.Queue[BuiltArc | None]) -> list[BuiltArc]:
    """Enqueue the end-of-stream sentinel without blocking on abort."""
    displaced: list[BuiltArc] = []
    while True:
        try:
            built_queue.put_nowait(None)
            return displaced
        except asyncio.QueueFull:
            try:
                item = built_queue.get_nowait()
            except asyncio.QueueEmpty:
                continue
            if item is None:
                return displaced
            displaced.append(item)


async def _fetch_and_group_related_data(db: Database, investigation_ids: list[str]) -> RelatedDataBatch:
    """Fetch related data in bulk and group it by investigation ID."""

    async def group_stream(gen: AsyncGenerator[TRow, None]) -> tuple[dict[str, list[TRow]], int]:
        grouped: dict[str, list[TRow]] = defaultdict(list)
        count = 0
        async for row in gen:
            grouped[str(row.investigation_ref)].append(row)
            count += 1
        return dict(grouped), count

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
    task: asyncio.Task[None] = asyncio.create_task(res.process_investigation(ctx, investigation, inv_info, res))
    running_tasks.add(task)

    def _on_task_done(done: asyncio.Task[None]) -> None:
        running_tasks.discard(done)
        if done.cancelled():
            return
        exc = done.exception()
        if exc is not None:
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


async def _spawn_batch(
    batch: list[InvestigationRow],
    *,
    db: Database,
    res: WorkerResources,
    running_tasks: set[asyncio.Task[None]],
    inv_idx: int,
) -> int:
    """Fetch related data for a batch and spawn build tasks with backpressure."""
    batch_data = await _fetch_and_group_related_data(db, [str(inv.identifier) for inv in batch])
    max_concurrent = res.config.max_concurrent_tasks
    for investigation in batch:
        while len(running_tasks) >= max_concurrent:
            pending = set(running_tasks)
            if not pending:
                break
            await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        inv_idx += 1
        _spawn_investigation_task(
            investigation,
            inv_idx,
            batch_data,
            res,
            running_tasks,
        )
    return inv_idx


async def _close_drive_builds(
    investigation_gen: AsyncGenerator[InvestigationRow, None],
    running_tasks: set[asyncio.Task[None]],
    res: WorkerResources,
) -> None:
    """Close the DB stream, cancel leftover builds, and close the queue."""
    try:
        await investigation_gen.aclose()
    finally:
        current = asyncio.current_task()
        aborting = current is not None and current.cancelling() > 0
        if aborting:
            res.displaced_arcs.extend(enqueue_queue_sentinel(res.built_queue))
            await _cancel_running_builds(running_tasks)
        else:
            await _cancel_running_builds(running_tasks)
            await res.built_queue.put(None)


async def drive_builds(
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
            batch: list[InvestigationRow] = []
            try:
                for _ in range(config.db_batch_size):
                    try:
                        batch.append(await anext(investigation_gen))
                    except StopAsyncIteration:
                        break
            except (RuntimeError, OSError, ConnectionError) as exc:
                logger.error(
                    "Database or connection error while fetching investigations: %s",
                    exc,
                    exc_info=True,
                )
                raise
            except Exception as exc:
                logger.error("Unexpected error while fetching investigations: %s", exc, exc_info=True)
                raise

            if not batch:
                break

            inv_idx = await _spawn_batch(
                batch,
                db=db,
                res=res,
                running_tasks=running_tasks,
                inv_idx=inv_idx,
            )

        if running_tasks:
            logger.info("Waiting for %d remaining build tasks to complete...", len(running_tasks))
            await asyncio.gather(*running_tasks)
    finally:
        await _close_drive_builds(investigation_gen, running_tasks, res)


async def stream_arcs_from_queue(
    built_queue: asyncio.Queue[BuiltArc | None],
    state: _ArcStreamTracker,
) -> AsyncGenerator[RoCrateContent, None]:
    """Yield ARC payloads from the queue into ``harvest_arcs``."""
    while True:
        item = await built_queue.get()
        if item is None:
            return
        state.track(item)
        logger.info("%s: Queued ARC %s for harvest upload", item.inv_info, item.investigation_id)
        yield item.arc_payload


def drain_unsubmitted_arcs(
    built_queue: asyncio.Queue[BuiltArc | None],
    scope: RepositoryScope,
    detail: str,
    *,
    already_recorded: set[str],
) -> None:
    """Mark ARCs left on the queue after abort as failed."""
    while True:
        try:
            item = built_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        if item is None or item.investigation_id in already_recorded:
            continue
        scope.record_failed(detail, record_id=item.investigation_id)
        already_recorded.add(item.investigation_id)
