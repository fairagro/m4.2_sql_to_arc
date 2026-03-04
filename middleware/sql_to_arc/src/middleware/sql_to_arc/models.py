"""Data models for the SQL-to-ARC conversion process."""

import logging
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, Json
from pydantic_core import PydanticUndefined

logger = logging.getLogger(__name__)

# JSON types representing the expected structure after parsing
type JsonList = list[Any]


def spec_field(
    *,
    required: bool | None = None,
    allow_spec_override: bool = False,
    default: Any = PydanticUndefined,
    **kwargs: Any,
) -> Any:
    """Define database-mapped fields with ARC spec metadata."""
    # We store the explicitly provided value (True, False, or None)
    # The model validator will infer the value if it stays None
    return Field(
        default=default,
        json_schema_extra={
            "spec_required": required,
            "spec_override": allow_spec_override,
        },
        **kwargs,
    )


class MissingRequiredColumnsError(ValueError):
    """Raised when required database columns are missing for a row model."""

    def __init__(self, model_name: str, columns: list[str]) -> None:
        """Initialize exception with model name and missing required columns."""
        self.model_name = model_name
        self.columns = columns
        super().__init__(f'Missing required columns for "{model_name}": {", ".join(columns)}')


class RequiredColumnsNullError(ValueError):
    """Raised when required database columns contain NULL values for a row model."""

    def __init__(self, model_name: str, columns: list[str]) -> None:
        """Initialize exception with model name and required NULL columns."""
        self.model_name = model_name
        self.columns = columns
        super().__init__(f'Required columns contain NULL for "{model_name}": {", ".join(columns)}')


class BaseRow(BaseModel):
    """Base model for database rows with centralized configuration."""

    __view_name__: ClassVar[str] = ""

    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True)


class InvestigationRow(BaseRow):
    """Pydantic model for investigation database rows."""

    __view_name__: ClassVar[str] = "vInvestigation"

    identifier: str = spec_field()
    title: str = spec_field()
    description_text: str = spec_field(default="", allow_spec_override=True)
    submission_date: datetime | None = spec_field(default=None)
    public_release_date: datetime | None = spec_field(default=None)


class StudyRow(BaseRow):
    """Pydantic model for study database rows."""

    __view_name__: ClassVar[str] = "vStudy"

    identifier: str = spec_field()
    investigation_ref: str = spec_field()
    title: str = spec_field()
    description_text: str | None = spec_field(default=None)
    submission_date: datetime | None = spec_field(default=None)
    public_release_date: datetime | None = spec_field(default=None)


class AssayRow(BaseRow):
    """Pydantic model for assay database rows."""

    __view_name__: ClassVar[str] = "vAssay"

    identifier: str = spec_field()
    investigation_ref: str = spec_field()
    study_ref: Json[JsonList] | None = spec_field(default=None)
    title: str | None = spec_field(default=None)
    description_text: str | None = spec_field(default=None)
    measurement_type_term: str | None = spec_field(default=None)
    measurement_type_uri: str | None = spec_field(default=None)
    measurement_type_version: str | None = spec_field(default=None)
    technology_type_term: str | None = spec_field(default=None)
    technology_type_uri: str | None = spec_field(default=None)
    technology_type_version: str | None = spec_field(default=None)
    technology_platform: str | None = spec_field(default=None)


class PublicationRow(BaseRow):
    """Pydantic model for publication database rows."""

    __view_name__: ClassVar[str] = "vPublication"

    investigation_ref: str = spec_field()
    target_type: str = spec_field()
    pubmed_id: str | None = spec_field(default=None)
    doi: str | None = spec_field(default=None)
    authors: str | None = spec_field(default=None)
    title: str | None = spec_field(default=None)
    status_term: str | None = spec_field(default=None)
    status_uri: str | None = spec_field(default=None)
    status_version: str | None = spec_field(default=None)
    target_ref: str | None = spec_field(default=None)


class ContactRow(BaseRow):
    """Pydantic model for contact database rows."""

    __view_name__: ClassVar[str] = "vContact"

    investigation_ref: str = spec_field()
    target_type: str = spec_field()
    last_name: str | None = spec_field(default=None)
    first_name: str | None = spec_field(default=None)
    mid_initials: str | None = spec_field(default=None)
    email: str | None = spec_field(default=None)
    phone: str | None = spec_field(default=None)
    fax: str | None = spec_field(default=None)
    postal_address: str | None = spec_field(default=None)
    affiliation: str | None = spec_field(default=None)
    roles: Json[JsonList] | None = spec_field(default=None)
    target_ref: str | None = spec_field(default=None)
