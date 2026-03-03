"""Tests for Database class handling of missing tables and views.

This module tests error handling when database tables or views do not exist,
ensuring that ProgrammingError exceptions are properly caught and logged.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import ProgrammingError

from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.stats import ProcessingStats


@pytest.mark.asyncio
async def test_stream_investigations_missing_table(caplog: pytest.LogCaptureFixture) -> None:
    """Test stream_investigations when the table is missing."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        # Simulate ProgrammingError for missing relation
        error_msg = 'relation "vInvestigation" does not exist'
        mock_conn.stream.side_effect = ProgrammingError("SELECT", {}, Exception(error_msg))

        db = Database("postgresql://localhost/db")
        results = [row async for row in db.stream_investigations(stats=ProcessingStats())]

        assert len(results) == 0
        assert 'Table or view "vInvestigation" does not exist' in caplog.text


@pytest.mark.asyncio
async def test_stream_annotation_tables_missing_table(caplog: pytest.LogCaptureFixture) -> None:
    """Test stream_annotation_tables when the table is missing."""
    with patch("middleware.sql_to_arc.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

        # Simulate ProgrammingError for missing relation
        error_msg = 'relation "vannotationtable" does not exist'
        mock_conn.stream.side_effect = ProgrammingError("SELECT", {}, Exception(error_msg))

        db = Database("postgresql://localhost/db")
        results = [row async for row in db.stream_annotation_tables(["1"])]

        assert len(results) == 0
        assert 'Table or view "vAnnotationTable" does not exist' in caplog.text
