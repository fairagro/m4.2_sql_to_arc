"""Tests for database SQL fixes."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.models import StudyRow


@pytest.mark.asyncio
async def test_stream_by_investigation_selects_all_columns() -> None:
    """Verify _stream_by_investigation uses literal_column('*') for correct column capture."""
    # This tests the SQLAlchemy SQL generation fix we applied
    db = Database("postgresql://dummy")
    # Mock the engine and connection
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    db.engine = mock_engine
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # Mock stream to return an empty async iterator
    async def async_iter() -> AsyncGenerator[None, None]:
        if False:
            yield  # Trick to make it an async generator

    mock_result = MagicMock()
    mock_result.mappings.return_value = async_iter()
    mock_conn.stream.return_value = mock_result

    # Call _stream_by_investigation
    ids = ["INV001"]
    # We consume it
    async for _ in db._stream_by_investigation(StudyRow, ids, "study"):
        pass

    # Inspect the call to conn.stream()
    assert mock_conn.stream.called
    stmt = mock_conn.stream.call_args[0][0]

    # Verify the statement selects *
    # In SQLAlchemy 2.0, the statement object should show the column as *
    # stmt.selected_columns contains the columns in the SELECT clause
    # literal_column("*") is translated to textual "*"

    # Check if any column is literal "*"
    columns = list(stmt.selected_columns)
    column_names = [str(c) for c in columns]
    assert "*" in column_names or '"*"' in column_names or any("*" in name for name in column_names)

    # Also check that it's from the correct table
    assert StudyRow.__view_name__ in str(stmt)


@pytest.mark.asyncio
async def test_stream_investigations_selects_all_columns() -> None:
    """Verify stream_investigations uses literal_column('*') correctly."""
    db = Database("postgresql://dummy")
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    db.engine = mock_engine
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    async def async_iter() -> AsyncGenerator[None, None]:
        if False:
            yield

    mock_result = MagicMock()
    mock_result.mappings.return_value = async_iter()
    mock_conn.stream.return_value = mock_result

    mock_stats = MagicMock()
    async for _ in db.stream_investigations(mock_stats):
        pass

    assert mock_conn.stream.called
    stmt = mock_conn.stream.call_args[0][0]

    columns = list(stmt.selected_columns)
    column_names = [str(c) for c in columns]
    assert "*" in column_names or '"*"' in column_names
    assert "vInvestigation" in str(stmt)
