"""Data models for the SQL-to-ARC conversion process."""

import logging
import numbers
from collections.abc import Mapping
from datetime import datetime
from types import NoneType
from typing import Any, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticUndefined

logger = logging.getLogger(__name__)


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
    """Base model for database rows with centralized DB-row validation."""

    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=True)

    @staticmethod
    def _field_metadata(field_info: Any) -> dict[str, Any]:
        """Return normalized metadata dictionary for a Pydantic field."""
        json_schema_extra = field_info.json_schema_extra
        return json_schema_extra if isinstance(json_schema_extra, dict) else {}

    @staticmethod
    def _field_default(field_info: Any) -> Any:
        """Return default value for a field, including default_factory values."""
        val = field_info.get_default(call_default_factory=True)
        return None if val is PydanticUndefined else val

    @staticmethod
    def _field_accepts_string(annotation: Any) -> bool:
        """Return whether a field annotation accepts string values."""
        if annotation is str:
            return True

        origin = get_origin(annotation)
        if origin is None:
            return False

        return str in get_args(annotation)

    @staticmethod
    def _field_accepts_none(annotation: Any) -> bool:
        """Return whether a field annotation accepts None values."""
        if annotation is NoneType:
            return True

        origin = get_origin(annotation)
        if origin is None:
            return False

        return type(None) in get_args(annotation)

    @classmethod
    def _validate_db_row_columns(cls, row: Mapping[str, Any]) -> list[str]:
        """Validate DB row columns for a model and return missing optional fields."""
        present_columns = set(row.keys())
        missing_required: list[str] = []
        missing_optional: list[str] = []

        for field_name, field_info in cls.model_fields.items():
            if field_name in present_columns:
                continue

            extra_dict = cls._field_metadata(field_info)
            is_required = extra_dict.get("spec_required")

            # Infer required from annotation if not explicitly set
            if is_required is None:
                is_required = not cls._field_accepts_none(field_info.annotation)

            # A field is only required in the DB if it's required AND has no default
            has_default = not field_info.is_required()
            if is_required and not has_default:
                missing_required.append(field_name)
            else:
                missing_optional.append(field_name)

        if missing_required:
            raise MissingRequiredColumnsError(cls.__name__, sorted(missing_required))

        return missing_optional

    @classmethod
    def _process_field_value(
        cls,
        data: dict[str, Any],
        field_name: str,
        field_info: Any,
    ) -> tuple[bool, bool, bool]:
        """Process a field value and report validation actions.

        Returns a tuple with flags:
        - required_null_error
        - numeric_to_string_coercion
        - spec_override_default_applied
        """
        value = data[field_name]
        extra_dict = cls._field_metadata(field_info)
        is_required = extra_dict.get("spec_required")
        if is_required is None:
            is_required = not cls._field_accepts_none(field_info.annotation)

        is_spec_override = bool(extra_dict.get("spec_override"))

        if value is None and is_required:
            if is_spec_override:
                data[field_name] = cls._field_default(field_info)
                return False, False, True
            return True, False, False

        if isinstance(value, bool):
            return False, False, False

        is_numeric_to_string = isinstance(value, numbers.Number) and cls._field_accepts_string(field_info.annotation)
        if is_numeric_to_string and is_spec_override:
            data[field_name] = cls._field_default(field_info)
            return False, False, True

        return False, is_numeric_to_string, False

    @classmethod
    def _report_validation_issues(
        cls,
        required_null_fields: list[str],
        override_default_fields: list[str],
        coerced_fields: list[str],
        missing_optional: list[str],
    ) -> None:
        """Log warnings and raise errors for validation issues discovered."""
        if required_null_fields:
            raise RequiredColumnsNullError(cls.__name__, sorted(required_null_fields))

        if override_default_fields:
            logger.warning(
                'Table "%s": Required fields overridden by spec_override and replaced with defaults: %s.',
                cls.__name__,
                ", ".join(sorted(override_default_fields)),
            )

        if coerced_fields:
            logger.warning(
                'Table "%s": Numeric values found for string fields: %s. '
                "Coercing to string due to coerce_numbers_to_str=True.",
                cls.__name__,
                ", ".join(sorted(coerced_fields)),
            )

        if missing_optional:
            logger.warning(
                'Table "%s" is missing optional columns: %s. Using default values.',
                cls.__name__,
                ", ".join(missing_optional),
            )

    @model_validator(mode="before")
    @classmethod
    def validate_row(cls, data: Any) -> Any:
        """Central validation logic triggered by model_validate."""
        if not isinstance(data, Mapping):
            return data

        row_mapping = dict(data)

        # 1. Check for extra columns
        extra_columns = sorted(set(row_mapping.keys()) - set(cls.model_fields.keys()))
        if extra_columns:
            logger.warning(
                'Table "%s": Input contains extra columns not defined in model: %s. Accepting due to extra="allow".',
                cls.__name__,
                ", ".join(extra_columns),
            )

        # 2. Process field values (NULLs, Coercion, Overrides)
        coerced_fields: list[str] = []
        override_default_fields: list[str] = []
        required_null_fields: list[str] = []

        for field_name, field_info in cls.model_fields.items():
            if field_name not in row_mapping:
                continue

            required_null_error, numeric_to_string_coercion, override_applied = cls._process_field_value(
                row_mapping,
                field_name,
                field_info,
            )

            if required_null_error:
                required_null_fields.append(field_name)
            if numeric_to_string_coercion:
                coerced_fields.append(field_name)
            if override_applied:
                override_default_fields.append(field_name)

        # 3. Check for missing columns and report all issues
        missing_optional = cls._validate_db_row_columns(row_mapping)
        cls._report_validation_issues(
            required_null_fields,
            override_default_fields,
            coerced_fields,
            missing_optional,
        )

        return row_mapping


class InvestigationRow(BaseRow):
    """Pydantic model for investigation database rows."""

    identifier: str = spec_field()
    title: str = spec_field()
    description_text: str = spec_field(default="", allow_spec_override=True)
    submission_date: datetime | None = spec_field(default=None)
    public_release_date: datetime | None = spec_field(default=None)


class StudyRow(BaseRow):
    """Pydantic model for study database rows."""

    identifier: str = spec_field()
    investigation_ref: str = spec_field()
    title: str = spec_field()
    description_text: str | None = spec_field(default=None)
    submission_date: datetime | None = spec_field(default=None)
    public_release_date: datetime | None = spec_field(default=None)


class AssayRow(BaseRow):
    """Pydantic model for assay database rows."""

    identifier: str = spec_field()
    investigation_ref: str = spec_field()
    study_ref: str | None = spec_field(default=None)
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
    roles: str | None = spec_field(default=None)  # JSON string
    target_ref: str | None = spec_field(default=None)
