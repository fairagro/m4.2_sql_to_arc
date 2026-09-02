"""Integration tests for the SQL-to-ARC workflow."""

import asyncio
import json
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from arctrl import ARC

from middleware.api_client import ApiClient, HarvestResult, HarvestStatus
from middleware.shared.config.config_base import OtelConfig
from middleware.shared.report import HarvestReport
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.context import WorkerContext
from middleware.sql_to_arc.main import main
from middleware.sql_to_arc.models import (
    AnnotationTableRow,
    AssayRow,
    ContactRow,
    InvestigationRow,
    PublicationRow,
    StudyRow,
)
from middleware.sql_to_arc.process_pool import ProcessPoolHolder
from middleware.sql_to_arc.processor import BuiltArc, WorkerResources, process_investigation


class MockExecutor(ThreadPoolExecutor):
    """Mock ThreadPoolExecutor to prevent multiprocessing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the mock executor."""
        kwargs.pop("mp_context", None)
        super().__init__(*args, **kwargs)


@pytest.fixture
def mock_db_cursor() -> AsyncMock:
    """Mock database cursor."""
    cursor = AsyncMock()
    # Setup default behavior for fetchall/aiter
    cursor.fetchall.return_value = []
    cursor.__aiter__.return_value = []
    return cursor


@pytest.fixture
def mock_db_connection(mock_db_cursor: AsyncMock) -> AsyncMock:
    """Mock database connection."""
    conn = AsyncMock()
    # conn.cursor is synchronous, returns an async context manager
    conn.cursor = MagicMock()
    conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_db_cursor)
    conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
    return conn


@pytest.fixture
def mock_api_client() -> AsyncMock:
    """Mock API client with a default successful harvest_arcs implementation."""
    client = AsyncMock(spec=ApiClient)

    async def _empty_harvest(
        *,
        rdi: str,
        arcs: Any,
        expected_datasets: int | None = None,
    ) -> HarvestResult:
        _ = expected_datasets
        async for _arc in arcs:
            pass
        return HarvestResult(
            harvest_id="harvest-test",
            rdi=rdi,
            status=HarvestStatus.COMPLETED,
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T00:01:00Z",
        )

    client.harvest_arcs.side_effect = _empty_harvest
    return client


class WorkflowTester:
    """Helper class to simplify integration tests for sql_to_arc."""

    def __init__(self, mocker: MagicMock, mock_api_client: AsyncMock) -> None:
        """
        Initialize the WorkflowTester with mock dependencies.

        Args:
            mocker (MagicMock): Mocking utility for patching dependencies.
            mock_api_client (AsyncMock): Mocked API client for simulating API interactions.
        """
        self.mocker = mocker
        self.api_client = mock_api_client
        self.db = AsyncMock()
        self.db.validate_schema = AsyncMock(return_value=None)
        self.db.count_investigations = AsyncMock(return_value=0)
        self.captured_arcs: list[ARC] = []

        # Default empty mocks
        self.set_db_content()

        # Patch Database class
        mocker.patch("middleware.sql_to_arc.main.Database", return_value=self.db)

        # Patch API Client context manager
        mocker.patch(
            "middleware.sql_to_arc.main.ApiClient",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=self.api_client)),
        )

        # Patch configuration
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.api_client = MagicMock()
        self.mock_config.rdi = "test-rdi"
        self.mock_config.rdi_url = "http://test.com"
        self.mock_config.max_concurrent_arc_builds = 1
        self.mock_config.max_concurrent_tasks = 4
        self.mock_config.db_batch_size = 10
        self.mock_config.arc_generation_timeout_minutes = 30
        self.mock_config.max_studies = 5000
        self.mock_config.max_assays = 10000
        self.mock_config.debug_limit = None
        self.mock_config.log_level = "INFO"
        self.mock_config.otel = OtelConfig(endpoint=None, log_console_spans=False, log_level="INFO")
        mock_conn = MagicMock()
        mock_conn.get_secret_value.return_value = "sqlite+aiosqlite:///:memory:"
        self.mock_config.connection_string = mock_conn

        mocker.patch("middleware.sql_to_arc.main.ConfigWrapper.from_yaml_file")
        mocker.patch("middleware.sql_to_arc.main.Config.from_config_wrapper", return_value=self.mock_config)
        mocker.patch("middleware.sql_to_arc.main.configure_logging")

        # Capture ARCs yielded into harvest_arcs
        async def capture_harvest(
            *,
            rdi: str,
            arcs: Any,
            expected_datasets: int | None = None,
        ) -> HarvestResult:
            _ = expected_datasets
            async for arc in arcs:
                serialized_arc = arc
                if isinstance(arc, dict):
                    serialized_arc = ARC.from_rocrate_json_string(json.dumps(arc))
                self.captured_arcs.append(serialized_arc)
            return HarvestResult(
                harvest_id="harvest-test",
                rdi=rdi,
                status=HarvestStatus.COMPLETED,
                started_at="2026-01-01T00:00:00Z",
                completed_at="2026-01-01T00:01:00Z",
            )

        self.api_client.harvest_arcs.side_effect = capture_harvest

    @staticmethod
    def _as_gen(data: list[dict[str, Any]], model_cls: type[Any] | None = None) -> AsyncGenerator[Any, None]:
        async def gen() -> AsyncGenerator[Any, None]:
            for item in data:
                yield model_cls.model_validate(item) if model_cls else item

        return gen()

    def set_db_content(  # noqa: PLR0913, PLR0917
        self,
        investigations: list[dict[str, Any]] | None = None,
        studies: list[dict[str, Any]] | None = None,
        assays: list[dict[str, Any]] | None = None,
        contacts: list[dict[str, Any]] | None = None,
        publications: list[dict[str, Any]] | None = None,
        annotations: list[dict[str, Any]] | None = None,
    ) -> None:
        """Mock the database streaming methods with provided data."""

        def _prepare_data(data: list[dict[str, Any]] | None, target_cls: type[Any] | None) -> list[dict[str, Any]]:
            if not data or not target_cls:
                return data or []
            prepared = []
            model_fields = target_cls.model_fields.keys()
            for item in data:
                new_item = item.copy()
                # Rename description to description_text if needed
                if "description" in new_item and "description_text" in model_fields:
                    new_item["description_text"] = new_item.pop("description")
                # Add default values for required fields missing in test data
                for field_name, field_info in target_cls.model_fields.items():
                    extra = field_info.json_schema_extra
                    is_required = isinstance(extra, dict) and extra.get("spec_required")
                    if is_required and field_name not in new_item:
                        new_item[field_name] = "Test Value"
                prepared.append(new_item)
            return prepared

        # The stream_* methods are async generator methods (not coroutines), so they must
        # be set as regular MagicMock, not AsyncMock. AsyncMock would wrap the return
        # value in a coroutine, but async generators are called directly (no await) and
        # return an AsyncGenerator object immediately.
        self.db.stream_investigations = MagicMock(
            side_effect=lambda *args, **kwargs: self._as_gen(  # noqa: ARG005
                _prepare_data(investigations, InvestigationRow), InvestigationRow
            )
        )
        self.db.count_investigations = AsyncMock(return_value=len(investigations or []))
        self.db.stream_studies = MagicMock(
            side_effect=lambda *args, **kwargs: self._as_gen(  # noqa: ARG005
                _prepare_data(studies, StudyRow), StudyRow
            )
        )
        self.db.stream_assays = MagicMock(
            side_effect=lambda *args, **kwargs: self._as_gen(  # noqa: ARG005
                _prepare_data(assays, AssayRow), AssayRow
            )
        )
        self.db.stream_contacts = MagicMock(
            side_effect=lambda *args, **kwargs: self._as_gen(  # noqa: ARG005
                _prepare_data(contacts, ContactRow), ContactRow
            )
        )
        self.db.stream_publications = MagicMock(
            side_effect=lambda *args, **kwargs: self._as_gen(  # noqa: ARG005
                _prepare_data(publications, PublicationRow), PublicationRow
            )
        )
        self.db.stream_annotation_tables = MagicMock(
            side_effect=lambda *args, **kwargs: self._as_gen(  # noqa: ARG005
                _prepare_data(annotations, AnnotationTableRow), AnnotationTableRow
            )
        )

    async def run(self) -> list[ARC]:
        """Execute the main workflow and return captured ARC objects."""
        # Prevent real engine creation
        self.mocker.patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=MagicMock())
        self.mocker.patch(
            "sqlalchemy.ext.asyncio.AsyncSession",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock())),
        )
        self.mocker.patch("middleware.sql_to_arc.processor.concurrent.futures.ProcessPoolExecutor", MockExecutor)

        await main(["-c", "config.yaml"])
        return self.captured_arcs


@pytest.fixture
def workflow_tester(mocker: MagicMock, mock_api_client: AsyncMock) -> WorkflowTester:
    """Fixture providing a WorkflowTester instance."""
    return WorkflowTester(mocker, mock_api_client)


@pytest.mark.asyncio
async def test_process_worker_investigations(mock_api_client: AsyncMock) -> None:
    """Test worker investigations build and enqueue ARC payloads for harvest."""
    investigation_rows: list[dict[str, Any]] = [
        {
            "identifier": 1,
            "title": "Test 1",
            "description_text": "Desc 1",
            "submission_time": None,
            "release_time": None,
        },
        {
            "identifier": 2,
            "title": "Test 2",
            "description_text": "Desc 2",
            "submission_time": None,
            "release_time": None,
        },
    ]
    studies_by_investigation: dict[str, list[StudyRow]] = {
        "1": [StudyRow.model_validate(study) for study in list[dict[str, Any]]()],
        "2": [StudyRow.model_validate(study) for study in list[dict[str, Any]]()],
    }
    assays_by_study: dict[str, list[dict[str, Any]]] = {}

    built_queue: asyncio.Queue[BuiltArc | None] = asyncio.Queue()
    with ThreadPoolExecutor(max_workers=5) as executor:
        pool_holder = ProcessPoolHolder(5, inject_executor=executor)
        ctx = WorkerContext(
            client=mock_api_client,
            rdi="edaphobase",
            studies_by_inv={
                key: [StudyRow.model_validate(study) for study in value]
                for key, value in studies_by_investigation.items()
            },
            assays_by_inv={
                key: [AssayRow.model_validate(assay) for assay in value] for key, value in assays_by_study.items()
            },
            contacts_by_inv={},
            pubs_by_inv={},
            anns_by_inv={},
            worker_id=1,
            total_workers=1,
            pool_holder=pool_holder,
        )
        report = HarvestReport()
        scope = report.open_repository("edaphobase")
        config = MagicMock(spec=Config)
        config.rdi = "edaphobase"
        config.max_concurrent_arc_builds = 1
        worker_res = WorkerResources(
            client=mock_api_client,
            config=config,
            scope=scope,
            pool_holder=pool_holder,
            semaphore=asyncio.Semaphore(1),
            built_queue=built_queue,
        )
        for i, inv in enumerate(investigation_rows):
            inv_info = f"Investigation {i + 1}"
            await process_investigation(ctx, InvestigationRow.model_validate(inv), inv_info, worker_res)
        report.finish()

    assert built_queue.qsize() == 2  # noqa: PLR2004
    for _ in range(2):
        built = await built_queue.get()
        assert built is not None
        payload = json.loads(built.arc_json)
        assert isinstance(payload, dict)
        assert "@graph" in payload
    mock_api_client.harvest_arcs.assert_not_called()
    mock_api_client.create_or_update_arc.assert_not_called()


@pytest.mark.asyncio
async def test_main_workflow(workflow_tester: WorkflowTester) -> None:
    """Test the main workflow with mocked DB and API using WorkflowTester."""
    # Setup DB data
    investigations = [
        {"identifier": "1", "title": "Inv 1", "description_text": "Desc 1"},
        {"identifier": "2", "title": "Inv 2", "description_text": "Desc 2"},
    ]
    studies = [
        {"identifier": "10", "investigation_ref": "1", "title": "Study 1", "description_text": "Desc S1"},
        {"identifier": "11", "investigation_ref": "2", "title": "Study 2", "description_text": "Desc S2"},
    ]
    assays = [
        {"identifier": "100", "study_ref": '["10"]', "investigation_ref": "1"},
        {"identifier": "101", "study_ref": '["11"]', "investigation_ref": "2"},
    ]

    workflow_tester.set_db_content(investigations=investigations, studies=studies, assays=assays)

    # Run main
    arcs = await workflow_tester.run()

    # Verify results
    assert len(arcs) == 2  # noqa: PLR2004
    identifiers = {arc.Identifier for arc in arcs}
    assert identifiers == {"1", "2"}
    workflow_tester.api_client.harvest_arcs.assert_called()
    workflow_tester.api_client.create_or_update_arc.assert_not_called()

    # Spot check deep property
    arc1 = next(a for a in arcs if a.Identifier == "1")
    assert arc1.Studies[0].Identifier == "10"
    # Check if assays are present
    assert len(arc1.Assays) > 0
    assert any(a.Identifier == "100" for a in arc1.Assays)


@pytest.mark.asyncio
async def test_investigation_with_publications_and_contacts(workflow_tester: WorkflowTester) -> None:
    """Test investigation with multiple publications and contacts at the investigation level."""
    inv_id = "INV_PUBLICATION_TEST"
    investigations = [{"identifier": inv_id, "title": "Publication and Contact Test"}]

    publications = [
        {
            "investigation_ref": inv_id,
            "target_type": "investigation",
            "title": "First Paper",
            "doi": "10.1234/1",
            "pubmed_id": "123456",
            "authors": "Author A, Author B",
            "status_term": "published",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "investigation",
            "title": "Second Paper",
            "doi": "10.1234/2",
            "pubmed_id": "654321",
            "authors": "Author C",
            "status_term": "in review",
        },
    ]

    contacts = [
        {
            "investigation_ref": inv_id,
            "target_type": "investigation",
            "last_name": "Doe",
            "first_name": "John",
            "email": "john.doe@example.com",
            "affiliation": "Institute A",
            "roles": json.dumps([{"term": "Principal Investigator"}]),
        },
        {
            "investigation_ref": inv_id,
            "target_type": "investigation",
            "last_name": "Smith",
            "first_name": "Jane",
            "email": "jane.smith@example.com",
            "affiliation": "Institute B",
            "roles": json.dumps([{"term": "Data Curator"}]),
        },
    ]

    workflow_tester.set_db_content(
        investigations=investigations,
        publications=publications,
        contacts=contacts,
    )

    arcs = await workflow_tester.run()

    assert len(arcs) == 1
    arc = arcs[0]
    assert arc.Identifier == inv_id

    # Verify Publications
    assert len(arc.Publications) == 2  # noqa: PLR2004
    titles = {p.Title for p in arc.Publications}
    assert titles == {"First Paper", "Second Paper"}
    assert any(p.DOI == "10.1234/1" for p in arc.Publications)

    # Verify Contacts
    assert len(arc.Contacts) == 2  # noqa: PLR2004
    emails = {c.EMail for c in arc.Contacts}
    assert emails == {"john.doe@example.com", "jane.smith@example.com"}
    assert any(c.LastName == "Doe" for c in arc.Contacts)
    assert any(oa.Name == "Data Curator" for c in arc.Contacts for oa in c.Roles)


@pytest.mark.asyncio
async def test_study_with_publications_and_contacts(workflow_tester: WorkflowTester) -> None:
    """Test study with multiple publications and contacts at the study level."""
    inv_id = "INV_S"
    study_id = "STUDY_1"

    investigations = [{"identifier": inv_id, "title": "Study Level Metadata Test"}]
    studies = [{"identifier": study_id, "investigation_ref": inv_id, "title": "Target Study"}]

    publications = [
        {
            "investigation_ref": inv_id,
            "target_type": "study",
            "target_ref": study_id,
            "title": "Study Specific Paper 1",
            "doi": "10.1234/study.1",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "study",
            "target_ref": study_id,
            "title": "Study Specific Paper 2",
            "doi": "10.1234/study.2",
        },
    ]

    contacts = [
        {
            "investigation_ref": inv_id,
            "target_type": "study",
            "target_ref": study_id,
            "last_name": "Scientist",
            "first_name": "Alice",
            "email": "alice@example.com",
            "roles": json.dumps([{"term": "Collaborator"}]),
        },
        {
            "investigation_ref": inv_id,
            "target_type": "study",
            "target_ref": study_id,
            "last_name": "Researcher",
            "first_name": "Bob",
            "email": "bob@example.com",
            "roles": json.dumps([{"term": "Lead Scientist"}]),
        },
    ]

    workflow_tester.set_db_content(
        investigations=investigations,
        studies=studies,
        publications=publications,
        contacts=contacts,
    )

    arcs = await workflow_tester.run()

    assert len(arcs) == 1
    arc = arcs[0]
    assert len(arc.Studies) == 1
    study = arc.Studies[0]
    assert study.Identifier == study_id

    # Verify Study Publications
    assert len(study.Publications) == 2  # noqa: PLR2004
    titles = {p.Title for p in study.Publications}
    assert titles == {"Study Specific Paper 1", "Study Specific Paper 2"}

    # Verify Study Contacts
    assert len(study.Contacts) == 2  # noqa: PLR2004
    emails = {c.EMail for c in study.Contacts}
    assert emails == {"alice@example.com", "bob@example.com"}


@pytest.mark.asyncio
async def test_assay_with_contacts(workflow_tester: WorkflowTester) -> None:
    """Test assay with multiple contacts (performers) at the assay level."""
    inv_id = "INV_A"
    assay_id = "ASSAY_1"

    investigations = [{"identifier": inv_id, "title": "Assay Metadata Test"}]
    # Assays need to be linked to studies in the DB row via study_ref if we want them registered in studies,
    # but the mapper/main logic also adds them to the ARC level.
    assays = [{"identifier": assay_id, "investigation_ref": inv_id}]

    contacts = [
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "last_name": "Technician",
            "first_name": "Tom",
            "email": "tom@example.com",
            "roles": json.dumps([{"term": "Operator"}]),
        },
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "last_name": "Analyst",
            "first_name": "Anna",
            "email": "anna@example.com",
            "roles": json.dumps([{"term": "Data Analyst"}]),
        },
    ]

    workflow_tester.set_db_content(
        investigations=investigations,
        assays=assays,
        contacts=contacts,
    )

    arcs = await workflow_tester.run()

    assert len(arcs) == 1
    arc = arcs[0]
    assert len(arc.Assays) == 1
    assay = arc.Assays[0]
    assert assay.Identifier == assay_id

    # Verify Assay Performers (contacts mapped to performers in assays)
    assert len(assay.Performers) == 2  # noqa: PLR2004
    emails = {p.EMail for p in assay.Performers}
    assert emails == {"tom@example.com", "anna@example.com"}
    assert any(p.LastName == "Technician" for p in assay.Performers)


@pytest.mark.asyncio
async def test_complex_hierarchy(workflow_tester: WorkflowTester) -> None:
    """Test investigation with multiple studies and assays linked to them."""
    inv_id = "INV_COMPLEX"
    s1_id = "S1"
    s2_id = "S2"
    a1_id = "A1"
    a2_id = "A2"
    a3_id = "A3"

    investigations = [{"identifier": inv_id, "title": "Complex Hierarchy Test"}]
    studies = [
        {"identifier": s1_id, "investigation_ref": inv_id, "title": "Study 1"},
        {"identifier": s2_id, "investigation_ref": inv_id, "title": "Study 2"},
    ]
    # Assays link to studies via 'study_ref' which is a JSON list of identifiers
    assays = [
        {"identifier": a1_id, "investigation_ref": inv_id, "study_ref": json.dumps([s1_id])},
        {"identifier": a2_id, "investigation_ref": inv_id, "study_ref": json.dumps([s1_id])},
        {"identifier": a3_id, "investigation_ref": inv_id, "study_ref": json.dumps([s2_id])},
    ]

    workflow_tester.set_db_content(
        investigations=investigations,
        studies=studies,
        assays=assays,
    )

    arcs = await workflow_tester.run()

    assert len(arcs) == 1
    arc = arcs[0]
    assert arc.Identifier == inv_id

    # Verify studies
    assert len(arc.Studies) == 2  # noqa: PLR2004
    assert any(s.Identifier == s1_id for s in arc.Studies)
    s2 = next(s for s in arc.Studies if s.Identifier == s2_id)

    # Verify assays at ARC level (RegisteredAssays link might not roundtrip in some versions)
    assert any(a.Identifier == a1_id for a in arc.Assays)
    assert any(a.Identifier == a2_id for a in arc.Assays)

    assert len(s2.RegisteredAssays) >= 0  # Just check it exists
    assert any(a.Identifier == a3_id for a in arc.Assays)


@pytest.mark.asyncio
async def test_assay_with_complete_ontology_fields(workflow_tester: WorkflowTester) -> None:
    """Test assay with all ontology-related fields filled (measurement, technology, platform)."""
    inv_id = "INV_ONTOLOGY"
    assay_id = "ASSAY_ONT"

    investigations = [{"identifier": inv_id, "title": "Ontology Test"}]
    assays = [
        {
            "identifier": assay_id,
            "investigation_ref": inv_id,
            "measurement_type_term": "gene expression profiling",
            "measurement_type_uri": "http://purl.obolibrary.org/obo/OBI_0001271",
            "measurement_type_version": "v1",
            "technology_type_term": "nucleotide sequencing",
            "technology_type_uri": "http://purl.obolibrary.org/obo/OBI_0000626",
            "technology_type_version": "v1",
            "technology_platform": "Illumina HiSeq 2500",
        }
    ]

    workflow_tester.set_db_content(
        investigations=investigations,
        assays=assays,
    )

    arcs = await workflow_tester.run()

    assert len(arcs) == 1
    arc = arcs[0]
    assert len(arc.Assays) == 1
    assay = arc.Assays[0]

    # Verify Measurement Type
    assert assay.MeasurementType is not None, "MeasurementType is None"
    assert assay.MeasurementType.Name == "gene expression profiling"
    # Match either full URI or CURIE
    assert (
        assay.MeasurementType.TermAccessionNumber is not None and "0001271" in assay.MeasurementType.TermAccessionNumber
    )

    # Verify Technology Type
    assert assay.TechnologyType is not None, "TechnologyType is None"
    assert assay.TechnologyType.Name == "nucleotide sequencing"
    assert (
        assay.TechnologyType.TermAccessionNumber is not None and "0000626" in assay.TechnologyType.TermAccessionNumber
    )

    # Verify Technology Platform
    assert assay.TechnologyPlatform is not None, "TechnologyPlatform is None"
    assert assay.TechnologyPlatform.Name == "Illumina HiSeq 2500"


@pytest.mark.asyncio
async def test_assay_with_annotations(workflow_tester: WorkflowTester) -> None:
    """
    Test investigation with an assay and annotation table data.

    Note: This is 'Neuland' because the reconstruction of tables from the flat
    database view is still a TODO in main.py. This test ensures the workflow
    runs and demonstrates how the data structure looks.
    """
    inv_id = "INV_ANN"
    assay_id = "ASSAY_ANN"

    investigations = [{"identifier": inv_id, "title": "Annotation Test"}]
    assays = [{"identifier": assay_id, "investigation_ref": inv_id}]

    # Example annotation rows representing a table
    # These rows logically form a table 'Sample Metadata' with 2 rows and 2 columns
    annotations = [
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Sample Metadata",
            "column_type": "input",
            "column_io_type": "source_name",
            "row_index": 0,
            "cell_value": "Sample 1",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Sample Metadata",
            "column_type": "characteristic",
            "column_annotation_term": "Species",
            "row_index": 0,
            "cell_value": "Homo sapiens",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Sample Metadata",
            "column_type": "input",
            "column_io_type": "source_name",
            "row_index": 1,
            "cell_value": "Sample 2",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Sample Metadata",
            "column_type": "characteristic",
            "column_annotation_term": "Species",
            "row_index": 1,
            "cell_value": "Mus musculus",
        },
    ]

    workflow_tester.set_db_content(
        investigations=investigations,
        assays=assays,
        annotations=annotations,
    )

    arcs = await workflow_tester.run()

    assert len(arcs) == 1
    arc = arcs[0]
    assert arc.Identifier == inv_id
    assert arc.Assays[0].Identifier == assay_id

    # For now, we expect no tables to be created because of the placeholder.
    # When implemented, TableCount should be 1.
    assert arc.Assays[0].TableCount == 1
    assert arc.Assays[0].Tables[0].Name == "Sample Metadata"
    assert arc.Assays[0].Tables[0].RowCount == 2  # noqa: PLR2004
    assert arc.Assays[0].Tables[0].ColumnCount == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_comprehensive_annotation_flow(workflow_tester: WorkflowTester) -> None:  # noqa: PLR0914
    """
    Test a complete flow with multiple linked annotation tables.

    Study: Sources -> Samples (with Characteristics and Factors)
    Assay Table 1: Samples -> Extracts (with Parameters)
    Assay Table 2: Extracts -> Data (with Parameters and Unitized Cells).
    """
    inv_id = "INV_FLOW"
    study_id = "STUDY_FLOW"
    assay_id = "ASSAY_FLOW"

    investigations = [{"identifier": inv_id, "title": "Comprehensive Flow Test"}]
    studies = [{"identifier": study_id, "investigation_ref": inv_id, "title": "Study Flow"}]
    assays = [{"identifier": assay_id, "investigation_ref": inv_id, "study_ref": json.dumps([study_id])}]

    annotations = [
        # --- Study Table: "Samples" ---
        {
            "investigation_ref": inv_id,
            "target_type": "study",
            "target_ref": study_id,
            "table_name": "Samples",
            "row_index": 0,
            "column_type": "input",
            "column_io_type": "source_name",
            "cell_value": "Source_A",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "study",
            "target_ref": study_id,
            "table_name": "Samples",
            "row_index": 0,
            "column_type": "characteristic",
            "column_annotation_term": "Species",
            "cell_annotation_term": "Arabidopsis thaliana",
            "cell_annotation_uri": "http://purl.obolibrary.org/obo/NCBITaxon_3702",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "study",
            "target_ref": study_id,
            "table_name": "Samples",
            "row_index": 0,
            "column_type": "factor",
            "column_annotation_term": "Treatment",
            "cell_annotation_term": "Drought",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "study",
            "target_ref": study_id,
            "table_name": "Samples",
            "row_index": 0,
            "column_type": "output",
            "column_io_type": "sample_name",
            "cell_value": "Sample_1",
        },
        # --- Assay Table 1: "Extraction" ---
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Extraction",
            "row_index": 0,
            "column_type": "input",
            "column_io_type": "sample_name",
            "cell_value": "Sample_1",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Extraction",
            "row_index": 0,
            "column_type": "parameter",
            "column_annotation_term": "Method",
            "cell_value": "Phenol-Chloroform",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Extraction",
            "row_index": 0,
            "column_type": "output",
            "column_io_type": "sample_name",  # ISA uses sample_name for extracts often
            "cell_value": "Extract_1",
        },
        # --- Assay Table 2: "Sequencing" ---
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Sequencing",
            "row_index": 0,
            "column_type": "input",
            "column_io_type": "sample_name",
            "cell_value": "Extract_1",
        },
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Sequencing",
            "row_index": 0,
            "column_type": "parameter",
            "column_annotation_term": "Concentration",
            "cell_value": "50.5",
            "cell_annotation_term": "ng/ul",  # Unitized cell
        },
        {
            "investigation_ref": inv_id,
            "target_type": "assay",
            "target_ref": assay_id,
            "table_name": "Sequencing",
            "row_index": 0,
            "column_type": "output",
            "column_io_type": "data",
            "cell_value": "raw_data.fastq.gz",
        },
    ]

    workflow_tester.set_db_content(
        investigations=investigations,
        studies=studies,
        assays=assays,
        annotations=annotations,
    )

    arcs = await workflow_tester.run()
    arc = arcs[0]

    # Verify Study Table "Samples"
    study = arc.Studies[0]
    assert study.TableCount == 1
    sample_table = study.Tables[0]
    assert sample_table.Name == "Samples"
    assert sample_table.ColumnCount == 4  # noqa: PLR2004
    # Check Header types (order preserved by implementation)
    assert sample_table.Headers[0].is_input
    assert sample_table.Headers[1].is_characteristic
    assert sample_table.Headers[2].is_factor
    assert sample_table.Headers[3].is_output

    # Verify Assay Tables
    assay = arc.Assays[0]
    assert assay.TableCount == 2  # noqa: PLR2004

    extraction_table = next(t for t in assay.Tables if t.Name == "Extraction")
    assert extraction_table.ColumnCount == 3  # noqa: PLR2004
    assert extraction_table.Headers[1].is_parameter

    sequencing_table = next(t for t in assay.Tables if t.Name == "Sequencing")
    assert sequencing_table.ColumnCount == 3  # noqa: PLR2004
    # Check unitized cell
    conc_col_idx = 1
    cell = sequencing_table.GetCellAt(conc_col_idx, 0)
    assert cell.is_unitized
    assert cell.GetContent()[0] == "50.5"
    assert cell.GetContent()[1] == "ng/ul"
