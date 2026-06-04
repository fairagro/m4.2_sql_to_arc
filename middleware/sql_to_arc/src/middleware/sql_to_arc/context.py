"""Internal context models for the SQL-to-ARC processing workflow."""

from dataclasses import dataclass

from middleware.api_client import ApiClient
from middleware.sql_to_arc.models import (
    AnnotationTableRow,
    AssayRow,
    ContactRow,
    InvestigationRow,
    PublicationRow,
    StudyRow,
)
from middleware.sql_to_arc.process_pool import ProcessPoolHolder


@dataclass(frozen=True, slots=True)
class ArcBuildData:
    """Data bundle for building a single ARC."""

    investigation_row: InvestigationRow
    studies: list[StudyRow]
    assays: list[AssayRow]
    contacts: list[ContactRow]
    publications: list[PublicationRow]
    annotations: list[AnnotationTableRow]


@dataclass(frozen=True, slots=True)
class WorkerContext:
    """Context data for a worker process, combining API client and pre-fetched data."""

    client: ApiClient
    rdi: str
    studies_by_inv: dict[str, list[StudyRow]]
    assays_by_inv: dict[str, list[AssayRow]]
    contacts_by_inv: dict[str, list[ContactRow]]
    pubs_by_inv: dict[str, list[PublicationRow]]
    anns_by_inv: dict[str, list[AnnotationTableRow]]
    worker_id: int
    total_workers: int
    pool_holder: ProcessPoolHolder
    arc_generation_timeout_minutes: int = 30


@dataclass(frozen=True, slots=True)
class RelatedDataBatch:
    """Batch of related data grouped by investigation ID."""

    studies_by_inv: dict[str, list[StudyRow]]
    assays_by_inv: dict[str, list[AssayRow]]
    contacts_by_inv: dict[str, list[ContactRow]]
    pubs_by_inv: dict[str, list[PublicationRow]]
    anns_by_inv: dict[str, list[AnnotationTableRow]]
    study_count: int
    assay_count: int
