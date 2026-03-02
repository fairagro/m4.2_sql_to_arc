"""Internal context models for the SQL-to-ARC processing workflow."""

import concurrent.futures
from dataclasses import dataclass
from typing import Any

from middleware.api_client import ApiClient
from middleware.sql_to_arc.models import (
    AssayRow,
    ContactRow,
    PublicationRow,
    StudyRow,
)


@dataclass(frozen=True, slots=True)
class WorkerContext:
    """Context data for a worker process, combining API client and pre-fetched data."""

    client: ApiClient
    rdi: str
    studies_by_inv: dict[str, list[StudyRow]]
    assays_by_inv: dict[str, list[AssayRow]]
    contacts_by_inv: dict[str, list[ContactRow]]
    pubs_by_inv: dict[str, list[PublicationRow]]
    anns_by_inv: dict[str, list[dict[str, Any]]]
    worker_id: int
    total_workers: int
    executor: concurrent.futures.Executor
    arc_generation_timeout_minutes: int = 30


@dataclass(frozen=True, slots=True)
class RelatedDataBatch:
    """Batch of related data grouped by investigation ID."""

    studies_by_inv: dict[str, list[StudyRow]]
    assays_by_inv: dict[str, list[AssayRow]]
    contacts_by_inv: dict[str, list[ContactRow]]
    pubs_by_inv: dict[str, list[PublicationRow]]
    anns_by_inv: dict[str, list[dict[str, Any]]]
    study_count: int
    assay_count: int
