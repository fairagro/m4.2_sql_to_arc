"""Unit tests for database validation in the SQL-to-ARC converter."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncConnection

from middleware.sql_to_arc.database import SchemaValidator
from middleware.sql_to_arc.models import (
    BaseRow,
    MissingRequiredColumnsError,
    RequiredColumnsNullError,
    spec_field,
)


class ValidationTestRow(BaseRow):
    """Test model for validation."""

    __view_name__ = "vTest"
    id: str = spec_field(required=True)
    optional: str | None = spec_field(default=None)
    overridable: str = spec_field(required=True, default="default", allow_spec_override=True)


@pytest.mark.asyncio
async def test_schema_validator_missing_required_column() -> None:
    """Test that missing required columns raise MissingRequiredColumnsError."""
    engine = MagicMock()
    conn = AsyncMock(spec=AsyncConnection)

    mock_inspect = MagicMock()
    mock_inspect.get_columns.return_value = [{"name": "optional"}]
    conn.run_sync.side_effect = lambda f: f(mock_inspect)

    with patch("middleware.sql_to_arc.database.inspect", return_value=mock_inspect):
        validator = SchemaValidator(engine)
        with pytest.raises(MissingRequiredColumnsError) as excinfo:
            await validator._validate_model(conn, ValidationTestRow)

    assert "id" in str(excinfo.value)


@pytest.mark.asyncio
async def test_schema_validator_missing_optional_column(caplog: pytest.LogCaptureFixture) -> None:
    """Test that missing optional columns log a warning."""
    engine = MagicMock()
    conn = AsyncMock(spec=AsyncConnection)

    mock_inspect = MagicMock()
    mock_inspect.get_columns.return_value = [{"name": "id"}, {"name": "overridable"}]
    conn.run_sync.side_effect = lambda f: f(mock_inspect)

    # Mock NULL check query results
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    conn.execute.return_value = mock_result

    with patch("middleware.sql_to_arc.database.inspect", return_value=mock_inspect):
        validator = SchemaValidator(engine)
        with caplog.at_level(logging.WARNING):
            await validator._validate_model(conn, ValidationTestRow)

    assert "is missing optional columns: optional" in caplog.text


@pytest.mark.asyncio
async def test_schema_validator_ignores_internal_model_fields(caplog: pytest.LogCaptureFixture) -> None:
    """Internal non-spec_field attributes must not be reported as missing DB columns."""

    class RowWithInternalFlag(BaseRow):
        __view_name__ = "vInternal"
        id: str = spec_field(required=True)
        internal_flag: bool = Field(default=False, exclude=True)

    engine = MagicMock()
    conn = AsyncMock(spec=AsyncConnection)
    mock_inspect = MagicMock()
    mock_inspect.get_columns.return_value = [{"name": "id"}]
    conn.run_sync.side_effect = lambda f: f(mock_inspect)
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    conn.execute.return_value = mock_result

    with patch("middleware.sql_to_arc.database.inspect", return_value=mock_inspect):
        validator = SchemaValidator(engine)
        with caplog.at_level(logging.WARNING):
            await validator._validate_model(conn, RowWithInternalFlag)

    assert "internal_flag" not in caplog.text
    assert "missing optional columns" not in caplog.text


@pytest.mark.asyncio
async def test_schema_validator_required_null_raises() -> None:
    """Test that NULL values in required columns raise RequiredColumnsNullError."""
    engine = MagicMock()
    conn = AsyncMock(spec=AsyncConnection)

    mock_inspect = MagicMock()
    mock_inspect.get_columns.return_value = [{"name": "id"}, {"name": "overridable"}, {"name": "optional"}]
    conn.run_sync.side_effect = lambda f: f(mock_inspect)

    # Mock NULL check for 'id' to return 5 nulls
    mock_result = MagicMock()
    mock_result.scalar.return_value = 5
    conn.execute.return_value = mock_result

    with patch("middleware.sql_to_arc.database.inspect", return_value=mock_inspect):
        validator = SchemaValidator(engine)
        with pytest.raises(RequiredColumnsNullError) as excinfo:
            await validator._check_null_values(conn, ValidationTestRow, {"id", "overridable", "optional"})

    assert "id" in str(excinfo.value)


@pytest.mark.asyncio
async def test_schema_validator_override_null_warns(caplog: pytest.LogCaptureFixture) -> None:
    """Test that NULL values in overridable columns log a warning."""
    engine = MagicMock()
    conn = AsyncMock(spec=AsyncConnection)

    mock_inspect = MagicMock()
    mock_inspect.get_columns.return_value = [{"name": "id"}, {"name": "overridable"}]
    conn.run_sync.side_effect = lambda f: f(mock_inspect)

    # Mock NULL check: 0 for id, 3 for overridable
    mock_result_zero = MagicMock()
    mock_result_zero.scalar.return_value = 0

    mock_result_three = MagicMock()
    mock_result_three.scalar.return_value = 3

    conn.execute.side_effect = [mock_result_zero, mock_result_three]

    with patch("middleware.sql_to_arc.database.inspect", return_value=mock_inspect):
        validator = SchemaValidator(engine)
        with caplog.at_level(logging.WARNING):
            await validator._check_null_values(conn, ValidationTestRow, {"id", "overridable"})

    assert 'Column "overridable" contains 3 NULL values' in caplog.text
    assert "replaced by model defaults" in caplog.text
