"""Unit tests for the sql_to_arc main module.

This module contains tests for argument parsing, investigation processing,
and workflow logic in the sql_to_arc pipeline.
"""

import asyncio
import concurrent.futures
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from middleware.api_client import ApiClient, ApiClientError
from middleware.shared.report import HarvestReport, JsonLdReportSerializer, RepositoryScope
from middleware.sql_to_arc.builder import build_single_arc_task
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.context import RelatedDataBatch, WorkerContext
from middleware.sql_to_arc.main import main, parse_args
from middleware.sql_to_arc.models import InvestigationRow
from middleware.sql_to_arc.process_pool import ProcessPoolHolder
from middleware.sql_to_arc.processor import (
    process_investigation,
    process_investigations,
)


class TestParseArgs:
    """Test suite for parse_args function."""

    @staticmethod
    def test_parse_args_default() -> None:
        """Test parse_args with default config."""
        with patch("sys.argv", ["prog"]):
            args = parse_args()
            assert args.config == Path("config.yaml")

    @staticmethod
    def test_parse_args_custom_config() -> None:
        """Test parse_args with custom config file."""
        with patch("sys.argv", ["prog", "-c", "/path/to/config.yaml"]):
            args = parse_args()
            assert args.config == Path("/path/to/config.yaml")


@pytest.mark.asyncio
async def test_process_investigation_builds_and_uploads(monkeypatch: pytest.MonkeyPatch) -> None:
    """process_investigation should build ARC via executor and upload it."""
    mock_client = AsyncMock(spec=ApiClient)
    mock_client.create_or_update_arc.return_value = MagicMock(arcs=[MagicMock(id="1")])

    investigation = InvestigationRow(identifier="1", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    semaphore = asyncio.Semaphore(1)

    loop_future: asyncio.Future[str] = asyncio.Future()
    loop_future.set_result('{"Identifier": "1"}')

    loop_mock = MagicMock()
    loop_mock.run_in_executor.return_value = loop_future
    monkeypatch.setattr("asyncio.get_running_loop", MagicMock(return_value=loop_mock))

    injected_executor = MagicMock(spec=concurrent.futures.ProcessPoolExecutor)
    pool_holder = ProcessPoolHolder(1, inject_executor=injected_executor)

    ctx = WorkerContext(
        client=mock_client,
        rdi="test_rdi",
        studies_by_inv={"1": [MagicMock()]},
        assays_by_inv={"1": [MagicMock(), MagicMock()]},
        contacts_by_inv={},
        pubs_by_inv={},
        anns_by_inv={},
        worker_id=1,
        total_workers=1,
        pool_holder=pool_holder,
        arc_generation_timeout_minutes=1,
    )

    await process_investigation(ctx, investigation, scope, "Inv 1", semaphore)
    report.finish()

    loop_mock.run_in_executor.assert_called_once_with(injected_executor, build_single_arc_task, ANY)
    mock_client.create_or_update_arc.assert_called_once()
    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 1
    assert entry.total_studies == 1
    assert entry.total_assays == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_process_investigation_upload_failure_records_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Upload failures must record failed with investigation id, not harvested."""
    mock_client = AsyncMock(spec=ApiClient)
    mock_client.create_or_update_arc.side_effect = ApiClientError("nope")

    investigation = InvestigationRow(identifier="inv-x", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    semaphore = asyncio.Semaphore(1)

    loop_future: asyncio.Future[str] = asyncio.Future()
    loop_future.set_result('{"Identifier": "inv-x"}')
    loop_mock = MagicMock()
    loop_mock.run_in_executor.return_value = loop_future
    monkeypatch.setattr("asyncio.get_running_loop", MagicMock(return_value=loop_mock))

    pool_holder = ProcessPoolHolder(1, inject_executor=MagicMock(spec=concurrent.futures.ProcessPoolExecutor))
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
        pool_holder=pool_holder,
        arc_generation_timeout_minutes=1,
    )

    await process_investigation(ctx, investigation, scope, "Inv 1", semaphore)
    report.finish()

    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 0
    assert entry.failed_datasets == 1
    assert entry.failed_records[0].record_id == "inv-x"
    assert entry.total_studies is None
    assert entry.total_assays is None


@pytest.mark.asyncio
async def test_process_investigation_invalid_arc_json_records_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed ARC JSON must record failed with investigation id, not harvested."""
    mock_client = AsyncMock(spec=ApiClient)

    investigation = InvestigationRow(identifier="inv-bad-json", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    semaphore = asyncio.Semaphore(1)

    loop_future: asyncio.Future[str] = asyncio.Future()
    loop_future.set_result("not-json")
    loop_mock = MagicMock()
    loop_mock.run_in_executor.return_value = loop_future
    monkeypatch.setattr("asyncio.get_running_loop", MagicMock(return_value=loop_mock))

    pool_holder = ProcessPoolHolder(1, inject_executor=MagicMock(spec=concurrent.futures.ProcessPoolExecutor))
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
        pool_holder=pool_holder,
        arc_generation_timeout_minutes=1,
    )

    await process_investigation(ctx, investigation, scope, "Inv 1", semaphore)
    report.finish()

    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 0
    assert entry.failed_datasets == 1
    assert entry.failed_records[0].record_id == "inv-bad-json"
    assert "Invalid ARC JSON" in entry.failed_records[0].message
    mock_client.create_or_update_arc.assert_not_called()


@pytest.mark.asyncio
async def test_process_investigations_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test full process_investigations flow with batching and streaming."""
    mock_db = MagicMock()
    mock_db.count_investigations = AsyncMock(return_value=2)

    async def mock_gen(**_kwargs: Any) -> AsyncGenerator[Any, None]:
        data = [
            InvestigationRow(identifier="1", title="T1", description_text="D1"),
            InvestigationRow(identifier="2", title="T2", description_text="D2"),
        ]
        for item in data:
            yield item

    mock_db.stream_investigations.side_effect = mock_gen

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

    mock_client = AsyncMock(spec=ApiClient)
    mock_config = MagicMock(spec=Config)
    mock_config.configure_mock(
        max_concurrent_arc_builds=2,
        max_concurrent_tasks=4,
        db_batch_size=10,
        rdi="test",
        debug_limit=10,
        arc_generation_timeout_minutes=30,
    )

    async def mock_process_inv(*_args: Any, **_kwargs: Any) -> None:
        pass

    monkeypatch.setattr("middleware.sql_to_arc.processor.process_investigation", mock_process_inv)

    report = await process_investigations(mock_db, mock_client, mock_config)

    assert isinstance(report, HarvestReport)
    assert len(report.repository_reports) == 1
    assert report.repository_reports[0].expected_datasets == 2  # noqa: PLR2004
    mock_db.stream_investigations.assert_called()
    call_kwargs = mock_db.stream_investigations.call_args.kwargs
    assert isinstance(call_kwargs["scope"], RepositoryScope)
    assert call_kwargs["limit"] == 10  # noqa: PLR2004


@pytest.mark.asyncio
async def test_main_serializer_failure_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Serializer failures during stdout emission are logged and do not raise."""
    finished = HarvestReport(start_time=datetime(2026, 1, 1, 0, 0, tzinfo=UTC))
    finished.open_repository("test-rdi")
    finished.finish(end_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC))

    mock_config = MagicMock(spec=Config)
    mock_config.log_level = "INFO"
    mock_config.otel = MagicMock(endpoint=None, log_console_spans=False)

    with (
        patch("middleware.sql_to_arc.main.ConfigWrapper") as mock_wrapper_cls,
        patch("middleware.sql_to_arc.main.Config.from_config_wrapper", return_value=mock_config),
        patch("middleware.sql_to_arc.main.configure_logging"),
        patch("middleware.sql_to_arc.main.initialize_tracing") as mock_tracing,
        patch("middleware.sql_to_arc.main.run_conversion", new=AsyncMock(return_value=finished)),
        patch.object(JsonLdReportSerializer, "render", side_effect=ValueError("boom")),
    ):
        mock_wrapper_cls.from_yaml_file.return_value = MagicMock()
        mock_tracing.return_value = (MagicMock(), MagicMock())
        await main(["-c", "config.yaml"])

    assert "Failed to serialise harvest report" in caplog.text
