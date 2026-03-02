"""Data models for the SQL-to-ARC conversion process."""

from datetime import datetime
from typing import Any, NamedTuple

from pydantic import BaseModel, ConfigDict, field_validator


class InvestigationRow(BaseModel):
    """Pydantic model for investigation database rows."""

    identifier: str
    title: str = ""
    description_text: str = ""
    submission_date: datetime | None = None
    public_release_date: datetime | None = None

    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True, from_attributes=True)

    @field_validator("title", "description_text", mode="before")
    @classmethod
    def empty_string_on_none(cls, v: Any) -> str:
        """Replace None with empty string for required text fields."""
        return v if v is not None else ""


class StudyRow(BaseModel):
    """Pydantic model for study database rows."""

    identifier: str
    investigation_ref: str
    title: str = ""
    description_text: str | None = None
    submission_date: datetime | None = None
    public_release_date: datetime | None = None

    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True, from_attributes=True)


class AssayRow(BaseModel):
    """Pydantic model for assay database rows."""

    identifier: str
    study_ref: str | None = None
    investigation_ref: str
    measurement_type_term: str | None = None
    measurement_type_uri: str | None = None
    technology_type_term: str | None = None
    technology_type_uri: str | None = None
    technology_platform: str | None = None

    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True, from_attributes=True)


class PublicationRow(BaseModel):
    """Pydantic model for publication database rows."""

    investigation_ref: str | None = None
    study_ref: str | None = None
    doi: str = ""
    pubmed_id: str = ""
    authors: str = ""
    title: str = ""
    status_term: str | None = None
    status_uri: str | None = None

    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True, from_attributes=True)


class ContactRow(BaseModel):
    """Pydantic model for contact database rows."""

    investigation_ref: str | None = None
    study_ref: str | None = None
    assay_ref: str | None = None
    last_name: str = ""
    first_name: str = ""
    mid_initials: str = ""
    email: str = ""
    phone: str = ""
    fax: str = ""
    postal_address: str = ""
    affiliation: str = ""
    roles: str | None = None  # JSON string

    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True, from_attributes=True)


class ArcBuildData(NamedTuple):
    """Data bundle for building a single ARC."""

    investigation_row: InvestigationRow
    studies: list[StudyRow]
    assays: list[AssayRow]
    contacts: list[ContactRow]
    publications: list[PublicationRow]
    annotations: list[dict[str, Any]]
