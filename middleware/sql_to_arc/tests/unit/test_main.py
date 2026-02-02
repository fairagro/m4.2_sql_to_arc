"""Unit tests for the sql_to_arc main module.

This module contains tests for argument parsing, investigation processing,
and workflow logic in the sql_to_arc pipeline.
"""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from middleware.sql_to_arc.main import parse_args
from middleware.sql_to_arc.models import RelatedDataBatch, WorkerContext
from middleware.sql_to_arc.processor import (
    process_investigation,
    process_investigations,
)
from middleware.sql_to_arc.stats import ProcessingStats


class TestParseArgs:
    """Test suite for parse_args function."""

    def test_parse_args_default(self) -> None:
        """Test parse_args with default config."""
        with patch("sys.argv", ["prog"]):
            args = parse_args()
            assert args.config == Path("config.yaml")

    def test_parse_args_custom_config(self) -> None:
        """Test parse_args with custom config file."""
        with patch("sys.argv", ["prog", "-c", "/path/to/config.yaml"]):
            args = parse_args()
            assert args.config == Path("/path/to/config.yaml")


@pytest.mark.asyncio
async def test_process_investigation_builds_and_uploads(monkeypatch: pytest.MonkeyPatch) -> None:
    """process_investigation should build ARC via executor and upload it."""
    mock_client = AsyncMock()
    mock_client.create_or_update_arc.return_value = MagicMock(arcs=[MagicMock(id="1")])

    investigation = {"identifier": "1", "title": "Inv", "description_text": "Desc"}
    stats = ProcessingStats()
    semaphore = asyncio.Semaphore(1)

    # Mock the loop.run_in_executor to return a JSON string
    loop_future: asyncio.Future[str] = asyncio.Future()
    loop_future.set_result('{"Identifier": "1"}')

    loop_mock = MagicMock()
    loop_mock.run_in_executor.return_value = loop_future
    monkeypatch.setattr("asyncio.get_event_loop", MagicMock(return_value=loop_mock))

    executor = MagicMock()

    ctx = WorkerContext(
        client=mock_client,
        rdi="test_rdi",
        studies_by_inv={},
        assays_by_inv={},
        contacts_by_inv={},
        pubs_by_inv={},
        anns_by_inv={},
        worker_id=1,
        total_workers=1,
        executor=executor,
        arc_generation_timeout_minutes=1,
    )

    await process_investigation(ctx, investigation, stats, "Inv 1", semaphore)

    loop_mock.run_in_executor.assert_called_once()
    mock_client.create_or_update_arc.assert_called_once()


@pytest.mark.asyncio
async def test_process_investigations_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test full process_investigations flow with batching and streaming."""
    mock_db = MagicMock()

    # Mock DB stream methods
    async def mock_gen(data: list[dict[str, Any]]) -> AsyncGenerator[dict[str, Any], None]:
        for item in data:
            yield item

    mock_db.stream_investigations.side_effect = lambda **_: mock_gen([{"identifier": "1"}, {"identifier": "2"}])

    # Mock related data fetch
    async def mock_fetch_related(*_args: Any, **_kwargs: Any) -> RelatedDataBatch:
        return RelatedDataBatch(
            studies_by_inv={},
            assays_by_inv={},
            contacts_by_inv={},
            pubs_by_inv={},
            anns_by_inv={},
            study_count=1,
            assay_count=0,
        )

    monkeypatch.setattr("middleware.sql_to_arc.processor._fetch_and_group_related_data", mock_fetch_related)

    mock_client = AsyncMock()
    mock_config = MagicMock(
        max_concurrent_arc_builds=2,
        max_concurrent_tasks=4,
        db_batch_size=10,
        rdi="test",
        debug_limit=10,
        arc_generation_timeout_minutes=30,
    )

    # Mock process_investigation to simplify
    async def mock_process_inv(*args: Any, **kwargs: Any) -> None:
        pass

    monkeypatch.setattr("middleware.sql_to_arc.processor.process_investigation", mock_process_inv)

    stats = await process_investigations(mock_db, mock_client, mock_config)

    assert stats.found_datasets == 2  # noqa: PLR2004
    assert stats.total_studies == 1
    mock_db.stream_investigations.assert_called_with(limit=10)
