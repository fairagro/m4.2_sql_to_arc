"""Data models for the SQL-to-ARC conversion process."""

import json
from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, Json, model_validator
from pydantic_core import PydanticUndefined

from middleware.shared.json_types import JsonValue

# JSON array values as stored/parsed for Json[T] view fields
type JsonList = list[JsonValue]


def _is_plain_study_ref_string(value: JsonValue) -> bool:
    """Return whether study_ref is a single ID string, not a JSON array per view spec."""
    if value is None or not isinstance(value, str):
        return False
    stripped = value.strip()
    return bool(stripped) and stripped[0] not in "[{"


def _coerce_parsed_json_to_string(value: JsonValue) -> JsonValue:
    """Serialize native JSON (list/dict) from DB drivers for Json[T] fields."""
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


def _coerce_json_array_string(value: JsonValue) -> JsonValue:
    """Wrap a plain identifier as a JSON array string for Json[JsonList] fields."""
    if value is None or not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] in "[{":
        return value
    return json.dumps([stripped])


def spec_field(
    *,
    required: bool | None = None,
    allow_spec_override: bool = False,
    default: Any = PydanticUndefined,
    **kwargs: Any,
) -> Any:
    """Define database-mapped fields with ARC spec metadata.

    ``Any`` is required here: Pydantic ``Field()`` accepts heterogeneous kwargs and
    is used as a field specifier in annotations (not a concrete ``FieldInfo`` value).
    """
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

    @model_validator(mode="before")
    @classmethod
    def apply_spec_overrides(cls, data: Any) -> Any:
        """Replace NULL (None) with default values for fields that allow spec overrides."""
        if not isinstance(data, dict):
            return data

        for field_name, field_info in cls.model_fields.items():
            # Check if value is explicitly None (SQL NULL)
            if data.get(field_name) is None:
                json_extra = field_info.json_schema_extra
                allow_override = json_extra.get("spec_override", False) if isinstance(json_extra, dict) else False

                # If override is allowed, replace with the field's default value
                if allow_override:
                    # Only apply if a default exists
                    if field_info.default is not PydanticUndefined:
                        data[field_name] = field_info.default
                    elif field_info.get_default(call_default_factory=True) is not None:
                        # Pydantic's get_default handles factory calls safely
                        data[field_name] = field_info.get_default(call_default_factory=True)

        return data


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
    study_ref_plain_coerced: bool = Field(default=False, exclude=True, repr=False)
    title: str | None = spec_field(default=None)
    description_text: str | None = spec_field(default=None)
    measurement_type_term: str | None = spec_field(default=None)
    measurement_type_uri: str | None = spec_field(default=None)
    measurement_type_version: str | None = spec_field(default=None)
    technology_type_term: str | None = spec_field(default=None)
    technology_type_uri: str | None = spec_field(default=None)
    technology_type_version: str | None = spec_field(default=None)
    technology_platform: str | None = spec_field(default=None)

    @model_validator(mode="before")
    @classmethod
    def normalize_study_ref(cls, data: Any) -> Any:
        """Accept JSON array strings or a single study identifier (Edaphobase export)."""
        if isinstance(data, dict) and "study_ref" in data:
            raw_study_ref = data.get("study_ref")
            if isinstance(raw_study_ref, (list, dict)):
                data["study_ref"] = _coerce_parsed_json_to_string(raw_study_ref)
            elif _is_plain_study_ref_string(raw_study_ref):
                data["study_ref_plain_coerced"] = True
                data["study_ref"] = _coerce_json_array_string(raw_study_ref)
        return data


class PublicationRow(BaseRow):
    """Pydantic model for publication database rows."""

    __view_name__: ClassVar[str] = "vPublication"

    investigation_ref: str = spec_field()
    target_type: Literal["investigation", "study"] = spec_field()
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
    target_type: Literal["investigation", "study", "assay"] = spec_field()
    last_name: str | None = spec_field(default=None)
    first_name: str | None = spec_field(default=None)
    mid_initials: str | None = spec_field(default=None)
    email: str | None = spec_field(default=None)
    phone: str | None = spec_field(default=None)
    fax: str | None = spec_field(default=None)
    postal_address: str | None = spec_field(default=None)
    affiliation: str | None = spec_field(default=None)
    roles: Json[JsonList] | None = spec_field(default=None)
    roles_native_json_coerced: bool = Field(default=False, exclude=True, repr=False)
    given_name_missing_coerced: bool = Field(default=False, exclude=True, repr=False)
    target_ref: str | None = spec_field(default=None)

    @model_validator(mode="before")
    @classmethod
    def flag_missing_given_name(cls, data: Any) -> Any:
        """Mark contacts without first_name; mapper supplies empty given name for ARCtrl."""
        if isinstance(data, dict):
            first_name = data.get("first_name")
            if first_name is None or (isinstance(first_name, str) and not first_name.strip()):
                data["given_name_missing_coerced"] = True
        return data

    @model_validator(mode="before")
    @classmethod
    def normalize_roles(cls, data: Any) -> Any:
        """Accept JSON string or native JSON list from drivers (e.g. Edaphobase)."""
        if isinstance(data, dict) and "roles" in data:
            raw_roles = data.get("roles")
            if isinstance(raw_roles, (list, dict)):
                data["roles_native_json_coerced"] = True
            data["roles"] = _coerce_parsed_json_to_string(raw_roles)
        return data


class AnnotationTableRow(BaseRow):
    """Pydantic model for annotation table cell rows (vAnnotationTable).

    Each row represents a single cell, together with the column and table it belongs to.
    """

    __view_name__: ClassVar[str] = "vAnnotationTable"

    investigation_ref: str = spec_field()
    target_type: Literal["study", "assay"] = spec_field()
    target_ref: str = spec_field()
    table_name: str = spec_field()
    column_type: str = spec_field()
    row_index: int = spec_field()
    column_io_type: Literal["data", "material_name", "sample_name", "source_name"] | None = spec_field(default=None)
    column_value: str | None = spec_field(default=None)
    column_annotation_term: str | None = spec_field(default=None)
    column_annotation_uri: str | None = spec_field(default=None)
    column_annotation_version: str | None = spec_field(default=None)
    # Not part of the view contract — test/fallback header label only.
    column_name: str | None = Field(default=None)
    cell_value: str | None = spec_field(default=None)
    cell_annotation_term: str | None = spec_field(default=None)
    cell_annotation_uri: str | None = spec_field(default=None)
    cell_annotation_version: str | None = spec_field(default=None)
