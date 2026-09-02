"""Tests for validation fixes and spec overrides."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

import middleware.sql_to_arc.database
from middleware.sql_to_arc.database import SchemaValidator
from middleware.sql_to_arc.models import InvestigationRow, RequiredColumnsNullError, spec_field


def test_investigation_row_spec_override() -> None:
    """Test that allow_spec_override correctly replaces None with default values."""
    # description_text has allow_spec_override=True and default=""
    data = {
        "identifier": "INV001",
        "title": "Test Investigation",
        "description_text": None,  # SQL NULL
    }

    # Should not raise ValidationError
    row = InvestigationRow.model_validate(data)

    assert row.description_text == ""
    assert row.identifier == "INV001"


def test_investigation_row_no_override_fails() -> None:
    """Test that fields without allow_spec_override still fail on None."""
    # identifier does NOT have allow_spec_override=True
    data = {"identifier": None, "title": "Test Investigation", "description_text": "Some description"}

    with pytest.raises(ValidationError) as excinfo:
        InvestigationRow.model_validate(data)

    assert "identifier" in str(excinfo.value)


@pytest.mark.asyncio
async def test_schema_validator_warnings_on_null_with_override(mocker: MockerFixture) -> None:
    """Test that SchemaValidator issues a warning when required fields contain NULL but allow override."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()

    # Simple mock that returns 5 for everything
    mock_result = MagicMock()
    mock_result.scalar.return_value = 5
    mock_conn.execute.return_value = mock_result

    validator = SchemaValidator(mock_engine)

    # We'll use a field that is definitely required but allowed to override
    # Let's mock a field in investigation that has spec_required=True

    class MockRow(InvestigationRow):
        required_with_override: str = spec_field(required=True, allow_spec_override=True, default="override")

    db_columns = {"required_with_override"}

    mocker.patch.object(middleware.sql_to_arc.database.logger, "warning", side_effect=RuntimeError("Warning reached"))

    with pytest.raises(RuntimeError, match="Warning reached"):
        await validator._check_null_values(mock_conn, MockRow, db_columns)


@pytest.mark.asyncio
async def test_schema_validator_error_on_null_without_override() -> None:
    """Test that SchemaValidator raises an error when required fields contain NULL and no override is allowed."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_conn.execute.return_value = mock_result

    validator = SchemaValidator(mock_engine)
    db_columns = {"identifier", "title", "description_text"}

    # identifier is required and has no override
    # Note: _check_null_values iterates over model fields.
    # We want to ensure it raises RequiredColumnsNullError when it hits identifier.

    with pytest.raises(RequiredColumnsNullError) as excinfo:
        await validator._check_null_values(mock_conn, InvestigationRow, db_columns)

    assert "identifier" in str(excinfo.value)
