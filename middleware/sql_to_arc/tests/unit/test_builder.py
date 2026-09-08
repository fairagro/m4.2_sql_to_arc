"""Unit tests for the ARC builder module."""

import json
import logging
import pickle

import pytest
from arctrl import CompositeHeader, IOType

from middleware.shared.json_types import JsonObject, JsonValue
from middleware.sql_to_arc.builder import (
    _IO_TYPE_MAP,
    DuplicateAssayRowError,
    DuplicateStudyRowError,
    _build_header,
    _build_single_cell,
    build_single_arc_task,
)
from middleware.sql_to_arc.context import ArcBuildData
from middleware.sql_to_arc.models import (
    AnnotationTableRow,
    AssayRow,
    ContactRow,
    InvestigationRow,
    PublicationRow,
    StudyRow,
)


@pytest.fixture
def sample_investigation() -> JsonObject:
    """Return a sample investigation dictionary."""
    return {
        "identifier": "inv1",
        "title": "Inv Title",
        "description_text": "Inv Desc",
        "submission_date": None,
        "public_release_date": None,
    }


@pytest.fixture
def sample_studies() -> list[JsonObject]:
    """Return a list of sample study dictionaries."""
    return [
        {
            "identifier": "sty1",
            "investigation_ref": "inv1",
            "title": "Study Title",
            "description_text": "Study Desc",
            "submission_date": None,
            "public_release_date": None,
        }
    ]


@pytest.fixture
def sample_assays() -> list[JsonObject]:
    """Return a list of sample assay dictionaries."""
    return [
        {
            "identifier": "asy1",
            "investigation_ref": "inv1",
            "measurement_type_term": "MType",
            "measurement_type_uri": "http://mtype",
            "technology_type_term": "TType",
            "technology_type_uri": "http://ttype",
            # Link to study sty1
            "study_ref": '["sty1"]',
            "technology_platform": "Platform",
        }
    ]


@pytest.fixture
def sample_contacts() -> list[JsonObject]:
    """Return a list of sample contact dictionaries."""
    return [
        {
            "last_name": "Doe",
            "first_name": "John",
            "investigation_ref": "inv1",
            "target_type": "investigation",
            "target_ref": None,
        },
        {
            "last_name": "Smith",
            "first_name": "Jane",
            "investigation_ref": "inv1",
            "target_type": "study",
            "target_ref": "sty1",
        },
    ]


@pytest.fixture
def sample_publications() -> list[JsonObject]:
    """Return a list of sample publication dictionaries."""
    return [
        {
            "title": "Inv Pub",
            "investigation_ref": "inv1",
            "target_type": "investigation",
            "target_ref": None,
        },
        {
            "title": "Study Pub",
            "investigation_ref": "inv1",
            "target_type": "study",
            "target_ref": "sty1",
        },
    ]


def test_build_simple_arc(sample_investigation: JsonObject) -> None:
    """Test building a basic ARC structure from investigation data."""
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=[],
        assays=[],
        contacts=[],
        publications=[],
        annotations=[],
    )
    arc_json = build_single_arc_task(arc_data)
    assert isinstance(arc_json, str)

    res = json.loads(arc_json)
    # RO-Crate JSON-LD usually has a @graph
    graph = res.get("@graph", [])
    # Find the investigation (Dataset with identifier or specific type)
    inv = next((item for item in graph if item.get("@id") == "inv1" or item.get("identifier") == "inv1"), None)
    assert inv is not None


def test_build_arc_deduplicates_assay_rows_per_study_link(
    sample_investigation: JsonObject,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Duplicate vAssay rows (same identifier, different study_ref) must not call AddAssay twice."""
    studies = [
        StudyRow.model_validate({
            "identifier": "sty1",
            "investigation_ref": "inv1",
            "title": "Study 1",
        }),
        StudyRow.model_validate({
            "identifier": "sty2",
            "investigation_ref": "inv1",
            "title": "Study 2",
        }),
    ]
    shared_assay_id = "4740ff3d0c615791c7e794c18d64d9a3"
    assays = [
        AssayRow.model_validate({
            "identifier": shared_assay_id,
            "investigation_ref": "inv1",
            "study_ref": '["sty1"]',
        }),
        AssayRow.model_validate({
            "identifier": shared_assay_id,
            "investigation_ref": "inv1",
            "study_ref": '["sty2"]',
        }),
    ]
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=studies,
        assays=assays,
        contacts=[],
        publications=[],
        annotations=[],
    )
    with caplog.at_level(logging.WARNING, logger="middleware.sql_to_arc.builder"):
        arc_json = build_single_arc_task(arc_data)
    res = json.loads(arc_json)
    graph = res.get("@graph", [])
    assay_nodes = [
        item for item in graph if item.get("@id") == shared_assay_id or item.get("identifier") == shared_assay_id
    ]
    assert len(assay_nodes) == 1
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 1
    assert "merged 1 duplicate vAssay row" in warning_records[0].message
    assert "inv1" in warning_records[0].message


def test_build_arc_deduplicates_study_rows(
    sample_investigation: JsonObject,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Duplicate vStudy rows with the same identifier must not call AddRegisteredStudy twice."""
    shared_study_id = "ea195a914ab1df58a84f29a7cf64a1a6"
    studies = [
        StudyRow.model_validate({
            "identifier": shared_study_id,
            "investigation_ref": "inv1",
            "title": "Study A",
        }),
        StudyRow.model_validate({
            "identifier": shared_study_id,
            "investigation_ref": "inv1",
            "title": "Study A",
        }),
    ]
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=studies,
        assays=[],
        contacts=[],
        publications=[],
        annotations=[],
    )
    with caplog.at_level(logging.WARNING, logger="middleware.sql_to_arc.builder"):
        arc_json = build_single_arc_task(arc_data)
    res = json.loads(arc_json)
    graph = res.get("@graph", [])
    study_nodes = [
        item for item in graph if item.get("@id") == shared_study_id or item.get("identifier") == shared_study_id
    ]
    assert len(study_nodes) == 1
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 1
    assert "skipped 1 duplicate vStudy row" in warning_records[0].message


def test_build_arc_raises_on_conflicting_duplicate_study_rows(
    sample_investigation: JsonObject,
) -> None:
    """Duplicate study identifiers with conflicting metadata must raise."""
    shared_study_id = "dup-study"
    studies = [
        StudyRow.model_validate({
            "identifier": shared_study_id,
            "investigation_ref": "inv1",
            "title": "Title A",
        }),
        StudyRow.model_validate({
            "identifier": shared_study_id,
            "investigation_ref": "inv1",
            "title": "Title B",
        }),
    ]
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=studies,
        assays=[],
        contacts=[],
        publications=[],
        annotations=[],
    )
    with pytest.raises(DuplicateStudyRowError) as exc_info:
        build_single_arc_task(arc_data)
    assert exc_info.value.study_id == shared_study_id
    assert "title" in exc_info.value.fields


def test_build_arc_warns_on_missing_first_name(
    sample_investigation: JsonObject,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Contacts without first_name must serialize with an aggregated warning."""
    contacts = [
        ContactRow.model_validate({
            "investigation_ref": "inv1",
            "target_type": "investigation",
            "last_name": "Müller",
        }),
        ContactRow.model_validate({
            "investigation_ref": "inv1",
            "target_type": "investigation",
            "first_name": "Anna",
            "last_name": "Schmidt",
        }),
    ]
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=[],
        assays=[],
        contacts=contacts,
        publications=[],
        annotations=[],
    )
    with caplog.at_level(logging.WARNING, logger="middleware.sql_to_arc.builder"):
        build_single_arc_task(arc_data)
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 1
    assert "no first_name" in warning_records[0].message
    assert "1 contact" in warning_records[0].message
    assert "inv1" in warning_records[0].message


def test_build_arc_warns_on_native_json_roles(
    sample_investigation: JsonObject,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Native JSON roles from Edaphobase must be coerced with one aggregated warning."""
    roles_list = [{"term": "Author", "uri": "http://example.org/obo/NCIT_C42781", "version": ""}]
    contacts = [
        ContactRow.model_validate({
            "investigation_ref": "inv1",
            "target_type": "investigation",
            "first_name": "Anna",
            "last_name": "Müller",
            "roles": roles_list,
        }),
        ContactRow.model_validate({
            "investigation_ref": "inv1",
            "target_type": "investigation",
            "first_name": "Bob",
            "last_name": "Schmidt",
            "roles": json.dumps([{"term": "Curator", "uri": "http://example.org", "version": ""}]),
        }),
    ]
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=[],
        assays=[],
        contacts=contacts,
        publications=[],
        annotations=[],
    )
    with caplog.at_level(logging.WARNING, logger="middleware.sql_to_arc.builder"):
        build_single_arc_task(arc_data)
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 1
    assert "native JSON roles" in warning_records[0].message
    assert "1 contact" in warning_records[0].message
    assert "inv1" in warning_records[0].message


def test_duplicate_assay_row_error_pickle_roundtrip() -> None:
    """Exception must unpickle across process pool workers with assay_id and fields intact."""
    err = DuplicateAssayRowError("assay-1", ["title", "description_text"])
    restored = pickle.loads(pickle.dumps(err))
    assert isinstance(restored, DuplicateAssayRowError)
    assert restored.assay_id == "assay-1"
    assert restored.fields == ["title", "description_text"]
    assert "assay-1" in str(restored)


def test_build_arc_raises_on_conflicting_duplicate_assay_rows(
    sample_investigation: JsonObject,
) -> None:
    """Duplicate identifier with differing metadata must fail the investigation build."""
    shared_assay_id = "assay-conflict"
    assays = [
        AssayRow.model_validate({
            "identifier": shared_assay_id,
            "investigation_ref": "inv1",
            "study_ref": "sty1",
            "title": "First title",
        }),
        AssayRow.model_validate({
            "identifier": shared_assay_id,
            "investigation_ref": "inv1",
            "study_ref": "sty2",
            "title": "Second title",
        }),
    ]
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=[],
        assays=assays,
        contacts=[],
        publications=[],
        annotations=[],
    )
    with pytest.raises(DuplicateAssayRowError, match=shared_assay_id) as exc_info:
        build_single_arc_task(arc_data)
    assert "title" in exc_info.value.fields


def test_build_arc_with_study_and_assay(
    sample_investigation: JsonObject, sample_studies: list[JsonObject], sample_assays: list[JsonObject]
) -> None:
    """Test building an ARC with nested study and assay structures."""
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=[StudyRow.model_validate(s) for s in sample_studies],
        assays=[AssayRow.model_validate(a) for a in sample_assays],
        contacts=[],
        publications=[],
        annotations=[],
    )
    arc_json = build_single_arc_task(arc_data)
    res = json.loads(arc_json)
    graph = res.get("@graph", [])

    # Check for study and assay in the graph
    study = next((item for item in graph if item.get("@id") == "sty1" or item.get("identifier") == "sty1"), None)
    assay = next((item for item in graph if item.get("@id") == "asy1" or item.get("identifier") == "asy1"), None)

    assert study is not None
    assert assay is not None


def test_build_arc_with_contacts_and_pubs(
    sample_investigation: JsonObject,
    sample_studies: list[JsonObject],
    sample_contacts: list[JsonObject],
    sample_publications: list[JsonObject],
) -> None:
    """Test building an ARC with contacts and publications at both investigation and study levels."""
    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=[StudyRow.model_validate(s) for s in sample_studies],
        assays=[],
        contacts=[ContactRow.model_validate(c) for c in sample_contacts],
        publications=[PublicationRow.model_validate(p) for p in sample_publications],
        annotations=[],
    )
    arc_json = build_single_arc_task(arc_data)
    res = json.loads(arc_json)
    graph = res.get("@graph", [])

    # Check for contacts (usually Person type)
    doe = next((item for item in graph if item.get("familyName") == "Doe"), None)
    smith = next((item for item in graph if item.get("familyName") == "Smith"), None)

    assert doe is not None
    assert smith is not None


def test_build_ignores_irrelevant_data(sample_investigation: JsonObject) -> None:
    """Test that data linked to other investigations is correctly filtered out."""
    # Data for other investigation
    other_study = {
        "identifier": "styX",
        "investigation_ref": "inv2",
        "title": "Other Study",
    }

    arc_data = ArcBuildData(
        investigation_row=InvestigationRow.model_validate(sample_investigation),
        studies=[StudyRow.model_validate(other_study)],
        assays=[],
        contacts=[],
        publications=[],
        annotations=[],
    )
    arc_json = build_single_arc_task(arc_data)
    res = json.loads(arc_json)
    graph = res.get("@graph", [])

    # Check that styX is NOT in the graph
    sty_x = next((item for item in graph if item.get("@id") == "styX" or item.get("identifier") == "styX"), None)
    assert sty_x is None


# ---------------------------------------------------------------------------
# Helpers to build minimal AnnotationTableRow dicts
# ---------------------------------------------------------------------------


def _ann_row(**overrides: JsonValue) -> JsonObject:
    """Return a minimal AnnotationTableRow dict, optionally overriding any field."""
    base: JsonObject = {
        "investigation_ref": "inv1",
        "target_type": "study",
        "target_ref": "sty1",
        "table_name": "T",
        "column_type": "input",
        "row_index": 0,
        "column_io_type": None,
        "cell_value": None,
        "cell_annotation_term": None,
        "cell_annotation_uri": None,
        "cell_annotation_version": None,
        "column_annotation_term": None,
        "column_annotation_uri": None,
        "column_annotation_version": None,
        "column_value": None,
    }
    base.update(overrides)
    return base


def _row(data: JsonObject) -> AnnotationTableRow:
    """Validate a dict into an AnnotationTableRow."""
    return AnnotationTableRow.model_validate(data)


# ---------------------------------------------------------------------------
# IOType mapping tests
# ---------------------------------------------------------------------------


class TestIOTypeMapping:
    """_IO_TYPE_MAP translates snake_case DB values to canonical ARCitect strings."""

    @staticmethod
    @pytest.mark.parametrize(
        ("db_value", "canonical"),
        [
            ("source_name", "Source Name"),
            ("sample_name", "Sample Name"),
            ("data", "Data"),
            ("material_name", "Material"),
        ],
    )
    def test_map_covers_all_db_values(db_value: str, canonical: str) -> None:
        """Each DB snake_case value maps to the expected canonical ARCitect string."""
        assert _IO_TYPE_MAP[db_value] == canonical

    @staticmethod
    @pytest.mark.parametrize(
        ("db_value", "expected_tag"),
        [
            ("source_name", 0),  # IOType.Source
            ("sample_name", 1),  # IOType.Sample
            ("data", 2),  # IOType.Data
            ("material_name", 3),  # IOType.Material
        ],
    )
    def test_build_header_input_uses_named_iotype(db_value: str, expected_tag: int) -> None:
        """DB values must produce a named IOType (tag 0–3), never FreeType (tag 4)."""
        key = ("input", db_value, None, None, None, None, None)
        header = _build_header(key)
        assert header is not None
        assert header.is_input
        assert header.fields[0].tag == expected_tag

    @staticmethod
    @pytest.mark.parametrize(
        ("db_value", "expected_tag"),
        [
            ("sample_name", 1),
            ("data", 2),
            ("material_name", 3),
        ],
    )
    def test_build_header_output_uses_named_iotype(db_value: str, expected_tag: int) -> None:
        """DB output values must also produce a named IOType, never FreeType."""
        key = ("output", db_value, None, None, None, None, None)
        header = _build_header(key)
        assert header is not None
        assert header.is_output
        assert header.fields[0].tag == expected_tag

    @staticmethod
    def test_missing_io_type_defaults_to_source_name_for_input() -> None:
        """Missing column_io_type falls back to 'Source Name' (tag 0) for input."""
        key = ("input", None, None, None, None, None, None)
        header = _build_header(key)
        assert header is not None
        assert header.is_input
        assert header.fields[0].tag == 0

    @staticmethod
    def test_missing_io_type_defaults_to_sample_name_for_output() -> None:
        """Missing column_io_type falls back to 'Sample Name' (tag 1) for output."""
        key = ("output", None, None, None, None, None, None)
        header = _build_header(key)
        assert header is not None
        assert header.is_output
        assert header.fields[0].tag == 1


# ---------------------------------------------------------------------------
# Data cell tests
# ---------------------------------------------------------------------------


class TestDataCellBuilding:
    """_build_single_cell must emit CompositeCell.data() for data-typed IO columns."""

    @staticmethod
    def test_data_cell_has_correct_file_path() -> None:
        """A data-typed output column must produce a DataCell with the file path set."""
        header = CompositeHeader.output(IOType.of_string("Data"))
        row = _row(_ann_row(column_type="output", column_io_type="data", cell_value="raw.fastq.gz"))
        cell = _build_single_cell(row, header)
        assert cell.is_data
        assert cell.AsData.FilePath == "raw.fastq.gz"

    @staticmethod
    def test_data_cell_empty_when_no_cell_value() -> None:
        """A data-typed column with no cell_value must produce an empty DataCell, not a crash."""
        header = CompositeHeader.output(IOType.of_string("Data"))
        row = _row(_ann_row(column_type="output", column_io_type="data", cell_value=None))
        cell = _build_single_cell(row, header)
        assert cell.is_data
        assert cell.AsData.FilePath is None

    @staticmethod
    def test_source_name_column_emits_free_text() -> None:
        """A source_name input column must produce a free-text cell, not a DataCell."""
        header = CompositeHeader.input(IOType.of_string("Source Name"))
        row = _row(_ann_row(column_type="input", column_io_type="source_name", cell_value="SourceA"))
        cell = _build_single_cell(row, header)
        assert cell.is_free_text

    @staticmethod
    def test_sample_name_column_emits_free_text() -> None:
        """A sample_name output column must produce a free-text cell, not a DataCell."""
        header = CompositeHeader.output(IOType.of_string("Sample Name"))
        row = _row(_ann_row(column_type="output", column_io_type="sample_name", cell_value="SampleB"))
        cell = _build_single_cell(row, header)
        assert cell.is_free_text
