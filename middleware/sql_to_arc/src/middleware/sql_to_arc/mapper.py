"""Mapper module to convert database rows to ARCTRL objects."""

from datetime import datetime

from arctrl import (
    ArcAssay,
    ArcInvestigation,
    ArcStudy,
    OntologyAnnotation,
    Person,
    Publication,
)

from middleware.sql_to_arc.models import (
    AssayRow,
    ContactRow,
    InvestigationRow,
    PublicationRow,
    StudyRow,
)


def _make_oa(term: str | None, uri: str | None, _version: str | None) -> OntologyAnnotation:
    # _version is deliberately ignored: the DB version field belongs to
    # OntologySourceReference.Version, not OntologyAnnotation. Mapping it
    # correctly would require registering OntologySourceReference objects on
    # the investigation and is out of scope. See arc-building/design.md.
    if not term:
        return OntologyAnnotation()
    return OntologyAnnotation(name=term, tan=uri or "", tsr="")


def _format_date(d: datetime | None) -> str | None:
    """Format dates as ISO strings."""
    if d is None:
        return None
    return d.isoformat()


def map_investigation(row: InvestigationRow) -> ArcInvestigation:
    """Map a database row to an ArcInvestigation object."""
    # Handle potential None values for dates
    submission_date = row.submission_date
    public_release_date = row.public_release_date

    identifier = row.identifier
    if not identifier.strip():
        # It's a required field
        # But we might start empty
        pass

    inv = ArcInvestigation.create(
        identifier=identifier,
        title=row.title,
        description=row.description_text,
        submission_date=_format_date(submission_date),
        public_release_date=_format_date(public_release_date),
    )
    return inv


def map_study(row: StudyRow) -> ArcStudy:
    """Map a database row to an ArcStudy object."""
    submission_date = row.submission_date
    public_release_date = row.public_release_date

    return ArcStudy.create(
        identifier=row.identifier,
        title=row.title,
        description=row.description_text,
        submission_date=_format_date(submission_date),
        public_release_date=_format_date(public_release_date),
    )


def map_assay(row: AssayRow) -> ArcAssay:
    """Map a database row to an ArcAssay object."""
    assay = ArcAssay.create(
        identifier=row.identifier,
        measurement_type=_make_oa(row.measurement_type_term, row.measurement_type_uri, None),
        technology_type=_make_oa(row.technology_type_term, row.technology_type_uri, None),
        technology_platform=_make_oa(
            row.technology_platform,  # Spec says platform is text but mapping to OA is allowed
            None,
            None,
        )
        if row.technology_platform
        else None,
    )

    return assay


def map_publication(row: PublicationRow) -> Publication:
    """Map a database row to a Publication object."""
    # Publication(doi, pubMedID, authors, title, status)

    status = _make_oa(row.status_term, row.status_uri, None)

    return Publication(
        doi=row.doi,
        pub_med_id=row.pubmed_id,
        authors=row.authors,
        title=row.title,
        status=status,
    )


def _contact_given_name(first_name: str | None) -> str:
    """Return a given name suitable for ARCtrl (None is rejected at serialization)."""
    if first_name and first_name.strip():
        return first_name.strip()
    return ""


def map_contact(row: ContactRow) -> Person:
    """Map a database row to a Person object."""
    # Person(lastName, firstName, midInitials, email, phone, fax, address, affiliation, roles)

    # row.roles is now already a list (it was Json[JsonList] and validated/parsed by Pydantic)
    roles = []
    if row.roles:
        for r in row.roles:
            if isinstance(r, dict):
                term = r.get("term")
                uri = r.get("uri")
                version = r.get("version")
                roles.append(
                    _make_oa(
                        term if isinstance(term, str) else None,
                        uri if isinstance(uri, str) else None,
                        version if isinstance(version, str) else None,
                    )
                )

    return Person(
        last_name=row.last_name,
        first_name=_contact_given_name(row.first_name),
        mid_initials=row.mid_initials,
        email=row.email,
        phone=row.phone,
        fax=row.fax,
        address=row.postal_address,
        affiliation=row.affiliation,
        roles=roles,
    )
