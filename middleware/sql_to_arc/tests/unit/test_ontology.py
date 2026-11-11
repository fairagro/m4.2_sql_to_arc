"""Unit tests for ontology source derivation and OntologyAnnotation wiring."""

from __future__ import annotations

import json

from arctrl import ARC

from middleware.sql_to_arc.builder import _assemble_arc, build_single_arc_task
from middleware.sql_to_arc.context import ArcBuildData
from middleware.sql_to_arc.mapper import _make_oa, map_assay, map_investigation
from middleware.sql_to_arc.models import AssayRow, InvestigationRow
from middleware.sql_to_arc.ontology import OntologySourceRegistry, derive_ontology_source_name


def test_derive_ontology_source_name_obo_purl() -> None:
    """OBO-style term IRIs yield the ontology prefix."""
    assert derive_ontology_source_name("http://purl.obolibrary.org/obo/ENVO_00002001") == "ENVO"
    assert derive_ontology_source_name("https://www.ebi.ac.uk/efo/EFO_0000001") == "EFO"


def test_derive_ontology_source_name_unparseable() -> None:
    """Missing or non-OBO URIs do not invent a source name."""
    assert derive_ontology_source_name(None) is None
    assert derive_ontology_source_name("") is None
    assert derive_ontology_source_name("http://example.org/prot") is None


def test_make_oa_sets_tsr_and_registers_osr() -> None:
    """Versioned OBO URI sets tsr and registers an OntologySourceReference."""
    registry = OntologySourceRegistry()
    oa = _make_oa(
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
    oa = _make_oa(None, "http://purl.obolibrary.org/obo/ENVO_00002001", "2024-01-01", registry)
    assert oa.is_empty()
    assert len(registry) == 0


def test_make_oa_unparseable_uri_leaves_tsr_empty() -> None:
    """Unparseable URI does not invent tsr or OSR."""
    registry = OntologySourceRegistry()
    oa = _make_oa("Proteomics", "http://example.org/prot", "v1", registry)
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
    arc = _assemble_arc(data)
    assert len(arc.OntologySourceReferences) == 1
    assert arc.OntologySourceReferences[0].Name == "ENVO"
    assert arc.OntologySourceReferences[0].Version == "2024-01-01"
    assay = arc.GetAssay("asy1")
    assert assay.MeasurementType is not None
    assert assay.MeasurementType.TermSourceREF == "ENVO"


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
    arc_json = build_single_arc_task(data)
    arc = ARC.from_rocrate_json_string(arc_json)
    assay = arc.GetAssay("asy1")
    assert assay.MeasurementType is not None
    assert assay.MeasurementType.TermSourceREF == "ENVO"
    assert "ENVO" in json.dumps(json.loads(arc_json))
