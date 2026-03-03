"""Unit tests for database validation in the SQL-to-ARC converter."""

import logging

import pytest

from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.models import (
    BaseRow,
    InvestigationRow,
    spec_field,
)


class OverrideRow(BaseRow):
    """Test model for spec_override behavior."""

    identifier: str | None = spec_field(required=True, allow_spec_override=True)
    title: str = spec_field(required=True)


@pytest.mark.asyncio
async def test_validate_row_missing_required_aborts(caplog: pytest.LogCaptureFixture) -> None:
    """Test that missing required columns raise MissingRequiredColumnsError."""
    # title is required for InvestigationRow
    row = {"identifier": "1", "description_text": "Present"}

    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception) as excinfo:
            InvestigationRow.model_validate(row)

        assert "Missing required columns" in str(excinfo.value)


@pytest.mark.asyncio
async def test_validate_row_missing_optional_warns(caplog: pytest.LogCaptureFixture) -> None:
    """Test that missing optional columns cause a warning but proceed."""
    # submission_date is optional
    row = {"identifier": "1", "title": "Test", "description_text": "Present"}

    with caplog.at_level(logging.WARNING):
        model = InvestigationRow.model_validate(row)
        assert model.submission_date is None
        assert model.public_release_date is None
        assert 'Table "InvestigationRow" is missing optional columns' in caplog.text
        assert "submission_date" in caplog.text
        assert "public_release_date" in caplog.text


@pytest.mark.asyncio
async def test_validate_row_description_text_exception() -> None:
    """Test that missing required columns raise Exception."""
    # title is required and must exist.
    row = {"identifier": "1", "description_text": "Desc"}

    with pytest.raises(Exception) as excinfo:
        InvestigationRow.model_validate(row)

    assert "Missing required columns" in str(excinfo.value)
    assert "title" in str(excinfo.value)


@pytest.mark.asyncio
async def test_validate_row_extra_columns_warn(caplog: pytest.LogCaptureFixture) -> None:
    """Test that extra columns are accepted but logged as warning."""
    row = {
        "identifier": "1",
        "title": "Test",
        "description_text": "Present",
        "unexpected_column": "x",
    }

    with caplog.at_level(logging.WARNING):
        model = InvestigationRow.model_validate(row)
        assert model.identifier == "1"
        assert "extra columns not defined in model" in caplog.text
        assert "unexpected_column" in caplog.text


@pytest.mark.asyncio
async def test_validate_row_numeric_to_string_warns(caplog: pytest.LogCaptureFixture) -> None:
    """Test that numeric values for string fields are coerced with warning."""
    row = {
        "identifier": 123,
        "title": "Test",
        "description_text": "Present",
    }

    with caplog.at_level(logging.WARNING):
        model = InvestigationRow.model_validate(row)
        assert model.identifier == "123"
        assert "Numeric values found for string fields" in caplog.text
        assert "identifier" in caplog.text


@pytest.mark.asyncio
async def test_validate_row_required_null_raises() -> None:
    """Test that NULL values in required columns raise Exception."""
    row = {
        "identifier": "1",
        "title": None,
        "description_text": "Present",
    }

    with pytest.raises(Exception) as excinfo:
        InvestigationRow.model_validate(row)

    assert "Required columns contain NULL" in str(excinfo.value)
    assert "title" in str(excinfo.value)


@pytest.mark.asyncio
async def test_validate_row_spec_override_uses_default_for_required_null(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that spec_override allows default for required NULL values with warning."""
    row = {
        "identifier": None,
        "title": "Test",
    }

    with caplog.at_level(logging.WARNING):
        model = OverrideRow.model_validate(row)
        assert model.identifier is None
        assert "spec_override" in caplog.text
        assert "identifier" in caplog.text


@pytest.mark.asyncio
async def test_validate_row_spec_override_uses_default_for_type_mismatch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that spec_override replaces coercible mismatches with default value."""
    row = {
        "identifier": 123,
        "title": "Test",
    }

    with caplog.at_level(logging.WARNING):
        model = OverrideRow.model_validate(row)
        assert model.identifier is None
        assert "spec_override" in caplog.text
        assert "identifier" in caplog.text


@pytest.mark.asyncio
async def test_database_validate_and_map_skips_required_null_row(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that database mapping skips rows with NULL in required columns."""
    row = {
        "identifier": "1",
        "title": None,
        "description_text": "Present",
    }

    with caplog.at_level(logging.WARNING):
        result = Database._validate_and_map(row, InvestigationRow, "investigation")
        assert result is None
        assert "Skipping investigation due to validation error" in caplog.text
        assert "Required columns contain NULL" in caplog.text
