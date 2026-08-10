"""Unit tests for the Database class in middleware.sql_to_arc.database.

These tests cover async methods for retrieving investigations, studies, assays,
contacts, publications, and annotation tables using mocked database connections.
"""

from collections.abc import AsyncIterable, Iterable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from middleware.shared.report import HarvestReport
from middleware.sql_to_arc.database import Database


class AsyncIterator:
    """Helper to mock an async iterator."""

    def __init__(self, data: Iterable[Any]) -> None:
        """Initialize the async iterator with the given data."""
        self.data = iter(data)

    def __aiter__(self) -> "AsyncIterator":
        """Return the async iterator."""
        return self

    async def __anext__(self) -> Any:
        """Return the next value in the iterator."""
        try:
            return next(self.data)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


async def collect_gen(gen: AsyncIterable[Any]) -> list[Any]:
    """Collect async generator results."""
    return [row async for row in gen]


@pytest.mark.asyncio
async def test_stream_investigations() -> None:
    """Test the stream_investigations method of the Database class."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        mock_result = AsyncMock()
        # Ensure mappings() is a regular mock, not an AsyncMock, so it returns immediately
        mock_result.mappings = MagicMock()
        mock_result.mappings.return_value = AsyncIterator([
            {"identifier": "1", "title": "Test Investigation", "description_text": "Test Desc"}
        ])
        mock_conn.stream.return_value = mock_result

        db = Database("sqlite+aiosqlite:///")
        scope = HarvestReport().open_repository("test")
        res = await collect_gen(db.stream_investigations(scope=scope, limit=5))

        assert len(res) == 1
        assert res[0].identifier == "1"
        assert res[0].title == "Test Investigation"
        assert res[0].description_text == "Test Desc"
        mock_conn.stream.assert_called()


@pytest.mark.asyncio
async def test_stream_investigations_null_identifier_records_unknown() -> None:
    """Validation failures with null identifier must use record_id 'unknown', not 'None'."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        mock_result = AsyncMock()
        mock_result.mappings = MagicMock()
        # Missing title (required) and identifier is null → validation fails.
        mock_result.mappings.return_value = AsyncIterator([
            {"identifier": None, "description_text": "orphan"},
        ])
        mock_conn.stream.return_value = mock_result

        db = Database("sqlite+aiosqlite:///")
        report = HarvestReport()
        scope = report.open_repository("test")
        res = await collect_gen(db.stream_investigations(scope=scope))

        assert res == []
        report.finish()
        entry = report.repository_reports[0]
        assert entry.failed_datasets == 1
        assert entry.failures[0].record_id == "unknown"
        assert entry.failures[0].kind.value == "dataset"


@pytest.mark.asyncio
async def test_stream_studies() -> None:
    """Test the stream_studies method of the Database class."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        mock_result = AsyncMock()
        mock_result.mappings = MagicMock()
        mock_result.mappings.return_value = AsyncIterator([
            {"identifier": "10", "investigation_ref": "1", "title": "Test Study"}
        ])
        mock_conn.stream.return_value = mock_result

        db = Database("connection_string")
        res = await collect_gen(db.stream_studies(["1", "2"]))

        assert len(res) == 1
        assert res[0].identifier == "10"
        assert res[0].title == "Test Study"
        mock_conn.stream.assert_called()


@pytest.mark.asyncio
async def test_stream_assays() -> None:
    """Test the stream_assays method of the Database class."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        mock_result = AsyncMock()
        mock_result.mappings = MagicMock()
        mock_result.mappings.return_value = AsyncIterator([])
        mock_conn.stream.return_value = mock_result

        db = Database("connection_string")
        await collect_gen(db.stream_assays(["1"]))
        mock_conn.stream.assert_called()


@pytest.mark.asyncio
async def test_stream_contacts() -> None:
    """Test the stream_contacts method of the Database class."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        mock_result = AsyncMock()
        mock_result.mappings = MagicMock()
        mock_result.mappings.return_value = AsyncIterator([])
        mock_conn.stream.return_value = mock_result

        db = Database("connection_string")
        await collect_gen(db.stream_contacts(["1"]))
        mock_conn.stream.assert_called()


@pytest.mark.asyncio
async def test_stream_publications() -> None:
    """Test the stream_publications method of the Database class."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        mock_result = AsyncMock()
        mock_result.mappings = MagicMock()
        mock_result.mappings.return_value = AsyncIterator([])
        mock_conn.stream.return_value = mock_result

        db = Database("connection_string")
        await collect_gen(db.stream_publications(["1"]))
        mock_conn.stream.assert_called()


@pytest.mark.asyncio
async def test_stream_annotation_tables() -> None:
    """Test the stream_annotation_tables method of the Database class."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        mock_result = AsyncMock()
        mock_result.mappings = MagicMock()
        mock_result.mappings.return_value = AsyncIterator([])
        mock_conn.stream.return_value = mock_result

        db = Database("connection_string")
        await collect_gen(db.stream_annotation_tables(["1"]))
        mock_conn.stream.assert_called()
