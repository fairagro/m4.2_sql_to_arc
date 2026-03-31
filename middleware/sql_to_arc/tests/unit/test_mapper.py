"""Unit tests for the mapper module."""

import datetime

import pytest
from arctrl import (
    ArcAssay,
    ArcInvestigation,
    ArcStudy,
    Person,
    Publication,
)
from pydantic import ValidationError

from middleware.sql_to_arc.mapper import (
    map_annotation,
    map_assay,
    map_contact,
    map_investigation,
    map_publication,
    map_study,
)
from middleware.sql_to_arc.models import (
    AssayRow,
    ContactRow,
    InvestigationRow,
    PublicationRow,
    StudyRow,
)


def test_map_investigation() -> None:
    """Test mapping of investigation data."""
    now = datetime.datetime.now()
    row = InvestigationRow(
        identifier="123",
        title="Test Investigation",
        description_text="Test Description",
        submission_date=now,
        public_release_date=now,
    )

    arc = map_investigation(row)

    assert isinstance(arc, ArcInvestigation)
    assert arc.Identifier == "123"
    assert arc.Title == "Test Investigation"
    assert arc.Description == "Test Description"
    assert arc.SubmissionDate == now.isoformat()
    assert arc.PublicReleaseDate == now.isoformat()


def test_map_investigation_defaults() -> None:
    """Test mapping of investigation data with missing optional fields."""
    row = InvestigationRow(
        identifier="456",
        title="Default Title",
        description_text="Default Description",
    )

    arc = map_investigation(row)

    assert arc.Identifier == "456"
    assert arc.Title == "Default Title"
    assert arc.Description == "Default Description"
    assert arc.SubmissionDate is None
    assert arc.PublicReleaseDate is None


def test_map_study() -> None:
    """Test mapping of study data."""
    now = datetime.datetime.now()
    row = StudyRow(
        identifier="1",
        investigation_ref="inv1",
        title="Test Study",
        description_text="Study Description",
        submission_date=now,
        public_release_date=now,
    )

    study = map_study(row)

    assert isinstance(study, ArcStudy)
    assert study.Identifier == "1"
    assert study.Title == "Test Study"
    assert study.Description == "Study Description"
    assert study.SubmissionDate == now.isoformat()
    assert study.PublicReleaseDate == now.isoformat()


def test_map_investigation_string_dates() -> None:
    """Test mapping of investigation data with string dates."""
    row = InvestigationRow(
        identifier="789",
        title="Title",
        description_text="Description",
        submission_date=datetime.datetime.strptime("2023-01-01", "%Y-%m-%d"),
        public_release_date=datetime.datetime.strptime("2023-12-31", "%Y-%m-%d"),
    )
    arc = map_investigation(row)
    assert arc.SubmissionDate == "2023-01-01T00:00:00"
    assert arc.PublicReleaseDate == "2023-12-31T00:00:00"


def test_map_assay() -> None:
    """Test mapping of assay data."""
    row = AssayRow(
        identifier="1",
        study_ref='["sty1"]',  # type: ignore[arg-type]
        investigation_ref="inv1",
        measurement_type_term="Proteomics",
        measurement_type_uri="http://example.org/prot",
        technology_type_term="Mass Spectrometry",
        technology_type_uri="http://example.org/ms",
    )

    assay = map_assay(row)

    assert isinstance(assay, ArcAssay)
    assert assay.Identifier == "1"
    # Check OntologyAnnotations
    assert assay.MeasurementType is not None
    assert assay.MeasurementType.Name == "Proteomics"
    assert assay.MeasurementType.TermAccessionNumber == "http://example.org/prot"
    assert assay.TechnologyType is not None
    assert assay.TechnologyType.Name == "Mass Spectrometry"
    assert assay.TechnologyType.TermAccessionNumber == "http://example.org/ms"


def test_map_assay_with_platform() -> None:
    """Test mapping of assay data including technology platform."""
    row = AssayRow(
        identifier="2",
        study_ref='["sty1"]',  # type: ignore[arg-type]
        investigation_ref="inv1",
        technology_platform="Orbitrap",
    )
    assay = map_assay(row)
    assert assay.Identifier == "2"
    assert assay.TechnologyPlatform is not None
    assert assay.TechnologyPlatform.Name == "Orbitrap"


def test_map_publication() -> None:
    """Test mapping of publication data."""
    row = PublicationRow(
        investigation_ref="inv1",
        target_type="investigation",
        pubmed_id="12345",
        doi="10.1234/5678",
        authors="Doe J, Smith A",
        title="A Great Paper",
        status_term="Published",
    )

    pub = map_publication(row)

    assert isinstance(pub, Publication)
    assert pub.PubMedID == "12345"
    assert pub.DOI == "10.1234/5678"
    assert pub.Authors == "Doe J, Smith A"
    assert pub.Title == "A Great Paper"
    assert pub.Status is not None
    assert pub.Status.Name == "Published"


def test_map_contact() -> None:
    """Test mapping of contact data."""
    row = ContactRow(
        investigation_ref="inv1",
        target_type="investigation",
        last_name="Doe",
        first_name="John",
        email="john@example.com",
        roles='[{"term": "Principal Investigator", "uri": "http://roles", "version": "1.0"}]',  # type: ignore[arg-type]
    )

    person = map_contact(row)

    assert isinstance(person, Person)
    assert person.LastName == "Doe"
    assert person.FirstName == "John"
    assert person.EMail == "john@example.com"
    assert len(person.Roles) == 1
    assert person.Roles[0] is not None
    assert person.Roles[0].Name == "Principal Investigator"
    assert person.Roles[0].TermAccessionNumber == "http://roles"


def test_map_contact_invalid_roles() -> None:
    """Test mapping of contact data with invalid roles JSON."""
    with pytest.raises(ValidationError):
        ContactRow(
            investigation_ref="inv1",
            target_type="investigation",
            last_name="Smith",
            roles="{invalid-json}",  # type: ignore[arg-type]
        )


def test_map_annotation() -> None:
    """Test the map_annotation helper function."""
    row = {"data": "test_value"}
    assert map_annotation(row) == row
