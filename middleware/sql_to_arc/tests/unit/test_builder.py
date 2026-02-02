"""Unit tests for the ARC builder module."""

import json
from typing import Any

import pytest

from middleware.sql_to_arc.builder import build_single_arc_task
from middleware.sql_to_arc.models import ArcBuildData


@pytest.fixture
def sample_investigation() -> dict[str, Any]:
    """Return a sample investigation dictionary."""
    return {
        "identifier": "inv1",
        "title": "Inv Title",
        "description_text": "Inv Desc",
        "submission_date": None,
        "public_release_date": None,
    }


@pytest.fixture
def sample_studies() -> list[dict[str, Any]]:
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
def sample_assays() -> list[dict[str, Any]]:
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
def sample_contacts() -> list[dict[str, Any]]:
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
def sample_publications() -> list[dict[str, Any]]:
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


def test_build_simple_arc(sample_investigation: dict[str, Any]) -> None:
    """Test building a basic ARC structure from investigation data."""
    arc_data = ArcBuildData(
        investigation_row=sample_investigation, studies=[], assays=[], contacts=[], publications=[], annotations=[]
    )
    arc_json = build_single_arc_task(arc_data)
    assert isinstance(arc_json, str)

    res = json.loads(arc_json)
    # RO-Crate JSON-LD usually has a @graph
    graph = res.get("@graph", [])
    # Find the investigation (Dataset with identifier or specific type)
    inv = next((item for item in graph if item.get("@id") == "inv1" or item.get("identifier") == "inv1"), None)
    assert inv is not None


def test_build_arc_with_study_and_assay(
    sample_investigation: dict[str, Any], sample_studies: list[dict[str, Any]], sample_assays: list[dict[str, Any]]
) -> None:
    """Test building an ARC with nested study and assay structures."""
    arc_data = ArcBuildData(
        investigation_row=sample_investigation,
        studies=sample_studies,
        assays=sample_assays,
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
    sample_investigation: dict[str, Any],
    sample_studies: list[dict[str, Any]],
    sample_contacts: list[dict[str, Any]],
    sample_publications: list[dict[str, Any]],
) -> None:
    """Test building an ARC with contacts and publications at both investigation and study levels."""
    arc_data = ArcBuildData(
        investigation_row=sample_investigation,
        studies=sample_studies,
        assays=[],
        contacts=sample_contacts,
        publications=sample_publications,
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


def test_build_ignores_irrelevant_data(sample_investigation: dict[str, Any]) -> None:
    """Test that data linked to other investigations is correctly filtered out."""
    # Data for other investigation
    other_study = {"identifier": "styX", "investigation_ref": "inv2"}

    arc_data = ArcBuildData(
        investigation_row=sample_investigation,
        studies=[other_study],
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
