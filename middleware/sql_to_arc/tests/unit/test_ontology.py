"""Unit tests for ontology source derivation and OntologyAnnotation wiring."""

from __future__ import annotations

import json

from arctrl import ARC

from middleware.sql_to_arc.builder import _assemble_arc, build_single_arc_task
from middleware.sql_to_arc.context import ArcBuildData
from middleware.sql_to_arc.mapper import map_assay, map_investigation
from middleware.sql_to_arc.models import AnnotationTableRow, AssayRow, InvestigationRow, StudyRow
from middleware.sql_to_arc.ontology import (
    OntologySourceRegistry,
    derive_ontology_source_name,
    make_ontology_annotation,
)


def test_derive_ontology_source_name_obo_purl() -> None:
    """OBO-style term IRIs yield the ontology prefix."""
    assert derive_ontology_source_name("http://purl.obolibrary.org/obo/ENVO_00002001") == "ENVO"
    assert derive_ontology_source_name("https://www.ebi.ac.uk/efo/EFO_0000001") == "EFO"
    assert derive_ontology_source_name("http://purl.obolibrary.org/obo/ENVO_00002001?view=full") == "ENVO"


def test_derive_ontology_source_name_unparseable() -> None:
    """Missing or non-OBO URIs do not invent a source name."""
    assert derive_ontology_source_name(None) is None
    assert derive_ontology_source_name("") is None
    assert derive_ontology_source_name("http://example.org/prot") is None
    assert derive_ontology_source_name("https://host/user_12345") is None
    assert derive_ontology_source_name("https://host/user_12345/profile") is None


def test_make_oa_sets_tsr_and_registers_osr() -> None:
    """Versioned OBO URI sets tsr and registers an OntologySourceReference."""
    registry = OntologySourceRegistry()
    oa = make_ontology_annotation(
        "soil texture",
        "http://purl.obolibrary.org/obo/ENVO_00002001",
        "2024-01-01",
        registry,
    )
    assert oa.Name == "soil texture"
    assert oa.TermSourceREF == "ENVO"
    assert len(registry) == 1
    inv = map_investigation(InvestigationRow(identifier="inv1", title="T", description_text="D"))
    arc = ARC.from_arc_investigation(inv)
    registry.apply_to_investigation(arc)
    assert len(arc.OntologySourceReferences) == 1
    assert arc.OntologySourceReferences[0].Name == "ENVO"
    assert arc.OntologySourceReferences[0].Version == "2024-01-01"


def test_make_oa_missing_term_does_not_invent() -> None:
    """No term → empty annotation; no OSR registration."""
    registry = OntologySourceRegistry()
    oa = make_ontology_annotation(None, "http://purl.obolibrary.org/obo/ENVO_00002001", "2024-01-01", registry)
    assert oa.is_empty()
    assert len(registry) == 0


def test_make_oa_unparseable_uri_leaves_tsr_empty() -> None:
    """Unparseable URI does not invent tsr or OSR."""
    registry = OntologySourceRegistry()
    oa = make_ontology_annotation("Proteomics", "http://example.org/prot", "v1", registry)
    assert oa.Name == "Proteomics"
    assert not oa.TermSourceREF
    assert len(registry) == 0


def test_map_assay_passes_version_into_oa() -> None:
    """Assay measurement/technology versions participate in OSR registration."""
    registry = OntologySourceRegistry()
    row = AssayRow(
        identifier="1",
        study_ref=["sty1"],
        investigation_ref="inv1",
        measurement_type_term="soil",
        measurement_type_uri="http://purl.obolibrary.org/obo/ENVO_00002001",
        measurement_type_version="2024-01-01",
        technology_type_term="Mass Spectrometry",
        technology_type_uri="http://example.org/ms",
        technology_type_version="v1",
    )
    assay = map_assay(row, registry)
    assert assay.MeasurementType is not None
    assert assay.MeasurementType.TermSourceREF == "ENVO"
    assert assay.TechnologyType is not None
    assert not assay.TechnologyType.TermSourceREF
    assert len(registry) == 1


def test_assemble_arc_includes_ontology_source_references() -> None:
    """Built ARC object model carries OSRs when view triples provide version+OBO URI."""
    data = ArcBuildData(
        investigation_row=InvestigationRow(identifier="inv-osr", title="T", description_text="D"),
        studies=[],
        assays=[
            AssayRow(
                identifier="asy1",
                study_ref=[],
                investigation_ref="inv-osr",
                measurement_type_term="soil",
                measurement_type_uri="http://purl.obolibrary.org/obo/ENVO_00002001",
                measurement_type_version="2024-01-01",
            )
        ],
        contacts=[],
        publications=[],
        annotations=[],
    )
    arc, _warnings = _assemble_arc(data)
    assert len(arc.OntologySourceReferences) == 1
    assert arc.OntologySourceReferences[0].Name == "ENVO"
    assert arc.OntologySourceReferences[0].Version == "2024-01-01"
    assay = arc.GetAssay("asy1")
    assert assay.MeasurementType is not None
    assert assay.MeasurementType.TermSourceREF == "ENVO"


def test_annotation_table_registers_osr_and_sets_tsr() -> None:
    """Annotation column/cell OAs use shared helper (version is not stuffed into tsr)."""
    data = ArcBuildData(
        investigation_row=InvestigationRow(identifier="inv-ann", title="T", description_text="D"),
        studies=[
            StudyRow(identifier="sty1", investigation_ref="inv-ann", title="Study"),
        ],
        assays=[],
        contacts=[],
        publications=[],
        annotations=[
            AnnotationTableRow(
                investigation_ref="inv-ann",
                target_type="study",
                target_ref="sty1",
                table_name="characteristics",
                column_type="characteristic",
                row_index=0,
                column_annotation_term="soil texture",
                column_annotation_uri="http://purl.obolibrary.org/obo/ENVO_00002001",
                column_annotation_version="2024-01-01",
                cell_annotation_term="clay",
                cell_annotation_uri="http://purl.obolibrary.org/obo/ENVO_00002001",
                cell_annotation_version="2024-01-01",
            )
        ],
    )
    arc, _warnings = _assemble_arc(data)
    assert len(arc.OntologySourceReferences) == 1
    assert arc.OntologySourceReferences[0].Name == "ENVO"
    assert arc.OntologySourceReferences[0].Version == "2024-01-01"
    study = arc.GetStudy("sty1")
    table = study.GetTable("characteristics")
    header = table.Headers[0]
    assert header.is_characteristic
    oa = header.ToTerm()
    assert oa.TermSourceREF == "ENVO"
    assert oa.TermSourceREF != "2024-01-01"
    cell = table.GetCellAt(0, 0)
    assert cell.is_term
    assert cell.AsTerm.TermSourceREF == "ENVO"


def test_build_preserves_tsr_in_rocrate_json() -> None:
    """RO-Crate JSON keeps TermSourceREF; OSR array may be omitted by arctrl."""
    data = ArcBuildData(
        investigation_row=InvestigationRow(identifier="inv-osr", title="T", description_text="D"),
        studies=[],
        assays=[
            AssayRow(
                identifier="asy1",
                study_ref=[],
                investigation_ref="inv-osr",
                measurement_type_term="soil",
                measurement_type_uri="http://purl.obolibrary.org/obo/ENVO_00002001",
                measurement_type_version="2024-01-01",
            )
        ],
        contacts=[],
        publications=[],
        annotations=[],
    )
    arc_json = build_single_arc_task(data).arc_json
    arc = ARC.from_rocrate_json_string(arc_json)
    assay = arc.GetAssay("asy1")
    assert assay.MeasurementType is not None
    assert assay.MeasurementType.TermSourceREF == "ENVO"
    assert "ENVO" in json.dumps(json.loads(arc_json))
