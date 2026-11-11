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
from middleware.sql_to_arc.ontology import OntologySourceRegistry, derive_ontology_source_name


def _make_oa(
    term: str | None,
    uri: str | None,
    version: str | None,
    registry: OntologySourceRegistry | None = None,
) -> OntologyAnnotation:
    """Map a view ontology triple to OntologyAnnotation; optionally register an OSR.

    Does not invent terms or URIs when absent. TermSourceREF is set only when a source
    short name can be derived from the URI. An OntologySourceReference is registered
    when both a derived source name and a non-empty version are present.
    """
    if not term:
        return OntologyAnnotation()

    source = derive_ontology_source_name(uri)
    if registry is not None and source is not None and version and version.strip():
        registry.register(source, version.strip())

    if source is not None:
        return OntologyAnnotation(name=term, tan=uri or "", tsr=source)
    return OntologyAnnotation(name=term, tan=uri or "")


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


def map_assay(row: AssayRow, registry: OntologySourceRegistry | None = None) -> ArcAssay:
    """Map a database row to an ArcAssay object."""
    assay = ArcAssay.create(
        identifier=row.identifier,
        measurement_type=_make_oa(
            row.measurement_type_term,
            row.measurement_type_uri,
            row.measurement_type_version,
            registry,
        ),
        technology_type=_make_oa(
            row.technology_type_term,
            row.technology_type_uri,
            row.technology_type_version,
            registry,
        ),
        technology_platform=_make_oa(
            row.technology_platform,  # Spec says platform is text but mapping to OA is allowed
            None,
            None,
            registry,
        )
        if row.technology_platform
        else None,
    )

    return assay


def map_publication(row: PublicationRow, registry: OntologySourceRegistry | None = None) -> Publication:
    """Map a database row to a Publication object."""
    status = _make_oa(row.status_term, row.status_uri, row.status_version, registry)

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


def map_contact(row: ContactRow, registry: OntologySourceRegistry | None = None) -> Person:
    """Map a database row to a Person object."""
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
                        registry,
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
