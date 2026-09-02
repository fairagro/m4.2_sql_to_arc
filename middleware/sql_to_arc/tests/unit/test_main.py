"""Unit tests for the sql_to_arc main module.

This module contains tests for argument parsing, investigation processing,
and workflow logic in the sql_to_arc pipeline.
"""

import asyncio
import concurrent.futures
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from middleware.api_client import (
    ApiClient,
    ApiClientError,
    HarvestError,
    HarvestErrorType,
    HarvestResult,
    HarvestStatus,
)
from middleware.shared.report import HarvestReport, JsonLdReportSerializer, RepositoryScope
from middleware.sql_to_arc.builder import DuplicateAssayRowError, build_single_arc_task
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.context import RelatedDataBatch, WorkerContext
from middleware.sql_to_arc.main import main, parse_args
from middleware.sql_to_arc.models import InvestigationRow
from middleware.sql_to_arc.process_pool import ProcessPoolHolder
from middleware.sql_to_arc.processor import (
    BuiltArc,
    CompositionCounts,
    WorkerResources,
    process_investigation,
    process_investigations,
)


def _harvest_ok(rdi: str = "test", harvest_id: str = "harvest-1") -> HarvestResult:
    return HarvestResult(
        harvest_id=harvest_id,
        rdi=rdi,
        status=HarvestStatus.COMPLETED,
        started_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-01T00:01:00Z",
    )


async def _consume_arcs(arcs: AsyncIterator[Any]) -> list[Any]:
    collected: list[Any] = []
    async for arc in arcs:
        collected.append(arc)
    return collected


def _make_worker_res(
    *,
    client: ApiClient,
    scope: RepositoryScope,
    pool_holder: ProcessPoolHolder,
    built_queue: asyncio.Queue[BuiltArc | None],
    rdi: str = "test_rdi",
) -> WorkerResources:
    config = MagicMock(spec=Config)
    config.rdi = rdi
    config.max_concurrent_arc_builds = 1
    config.max_concurrent_tasks = 1
    config.arc_generation_timeout_minutes = 1
    config.max_studies = 5000
    config.max_assays = 10000
    return WorkerResources(
        client=client,
        config=config,
        scope=scope,
        pool_holder=pool_holder,
        semaphore=asyncio.Semaphore(1),
        built_queue=built_queue,
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
async def test_process_investigation_builds_and_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    """process_investigation should build ARC via executor and enqueue it for harvest."""
    mock_client = AsyncMock(spec=ApiClient)

    investigation = InvestigationRow(identifier="1", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    built_queue: asyncio.Queue[BuiltArc | None] = asyncio.Queue()

    loop_future: asyncio.Future[str] = asyncio.Future()
    loop_future.set_result('{"identifier": "1"}')

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

    await process_investigation(
        ctx,
        investigation,
        "Inv 1",
        _make_worker_res(client=mock_client, scope=scope, pool_holder=pool_holder, built_queue=built_queue),
    )
    report.finish()

    loop_mock.run_in_executor.assert_called_once_with(injected_executor, build_single_arc_task, ANY)
    assert built_queue.qsize() == 1
    built = await built_queue.get()
    assert built is not None
    assert built.investigation_id == "1"
    assert built.composition.studies == 1
    assert built.composition.assays == 2  # noqa: PLR2004
    mock_client.harvest_arcs.assert_not_called()
    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 0
    assert entry.failed_datasets == 0


@pytest.mark.asyncio
async def test_process_investigation_invalid_arc_json_records_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed ARC JSON must record failed with investigation id, not enqueue."""
    mock_client = AsyncMock(spec=ApiClient)

    investigation = InvestigationRow(identifier="inv-bad-json", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    built_queue: asyncio.Queue[BuiltArc | None] = asyncio.Queue()

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

    await process_investigation(
        ctx,
        investigation,
        "Inv 1",
        _make_worker_res(client=mock_client, scope=scope, pool_holder=pool_holder, built_queue=built_queue),
    )
    report.finish()

    assert built_queue.empty()
    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 0
    assert entry.failed_datasets == 1
    assert entry.failures[0].record_id == "inv-bad-json"
    assert entry.failures[0].kind.value == "dataset"
    assert "Invalid ARC JSON" in entry.failures[0].message
    mock_client.harvest_arcs.assert_not_called()


@pytest.mark.asyncio
async def test_process_investigation_bare_exception_records_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bare Exception from the worker (e.g. arctrl) must record failed, not escape the task."""
    mock_client = AsyncMock(spec=ApiClient)

    investigation = InvestigationRow(identifier="inv-dup", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    built_queue: asyncio.Queue[BuiltArc | None] = asyncio.Queue()

    loop_future: asyncio.Future[str] = asyncio.Future()
    loop_future.set_exception(
        Exception(
            "Cannot create study with name ea195a914ab1df58a84f29a7cf64a1a6, "
            "as study names must be unique and study at index 7 has the same name."
        )
    )
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

    await process_investigation(
        ctx,
        investigation,
        "Inv 1",
        _make_worker_res(client=mock_client, scope=scope, pool_holder=pool_holder, built_queue=built_queue),
    )
    report.finish()

    assert built_queue.empty()
    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 0
    assert entry.failed_datasets == 1
    assert entry.failures[0].record_id == "inv-dup"
    assert entry.failures[0].kind.value == "dataset"
    assert "Build failed" in entry.failures[0].message
    mock_client.harvest_arcs.assert_not_called()


@pytest.mark.asyncio
async def test_process_investigation_duplicate_assay_includes_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Conflicting duplicate assay failures must list the conflicting field names."""
    mock_client = AsyncMock(spec=ApiClient)
    investigation = InvestigationRow(identifier="inv-conflict", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    built_queue: asyncio.Queue[BuiltArc | None] = asyncio.Queue()

    loop_future: asyncio.Future[str] = asyncio.Future()
    loop_future.set_exception(DuplicateAssayRowError("assay-xyz", ["title", "measurement_type_term"]))
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

    await process_investigation(
        ctx,
        investigation,
        "Inv 1",
        _make_worker_res(client=mock_client, scope=scope, pool_holder=pool_holder, built_queue=built_queue),
    )
    report.finish()

    assert built_queue.empty()
    failure = report.repository_reports[0].failures[0]
    assert failure.kind.value == "dataset"
    assert "assay-xyz" in failure.message
    assert "fields: title, measurement_type_term" in failure.message


@pytest.mark.asyncio
async def test_process_investigation_skips_when_study_limit_exceeded() -> None:
    """Investigations above max_studies are skipped without build or enqueue."""
    mock_client = AsyncMock(spec=ApiClient)
    investigation = InvestigationRow(identifier="inv-big", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    built_queue: asyncio.Queue[BuiltArc | None] = asyncio.Queue()

    pool_holder = ProcessPoolHolder(1, inject_executor=MagicMock(spec=concurrent.futures.ProcessPoolExecutor))
    ctx = WorkerContext(
        client=mock_client,
        rdi="test_rdi",
        studies_by_inv={"inv-big": [MagicMock(), MagicMock(), MagicMock()]},
        assays_by_inv={"inv-big": []},
        contacts_by_inv={},
        pubs_by_inv={},
        anns_by_inv={},
        worker_id=1,
        total_workers=1,
        pool_holder=pool_holder,
        arc_generation_timeout_minutes=1,
        max_studies=2,
        max_assays=10000,
    )

    await process_investigation(
        ctx,
        investigation,
        "Inv 1",
        _make_worker_res(client=mock_client, scope=scope, pool_holder=pool_holder, built_queue=built_queue),
    )
    report.finish()

    assert built_queue.empty()
    entry = report.repository_reports[0]
    assert entry.skipped_datasets == 1
    assert entry.harvested_datasets == 0
    assert entry.failed_datasets == 0
    assert entry.failures == ()
    mock_client.harvest_arcs.assert_not_called()


@pytest.mark.asyncio
async def test_process_investigation_skips_when_assay_limit_exceeded() -> None:
    """Investigations above max_assays are skipped without build or enqueue."""
    mock_client = AsyncMock(spec=ApiClient)
    investigation = InvestigationRow(identifier="inv-assays", title="Inv", description_text="Desc")
    report = HarvestReport()
    scope = report.open_repository("test_rdi")
    built_queue: asyncio.Queue[BuiltArc | None] = asyncio.Queue()

    pool_holder = ProcessPoolHolder(1, inject_executor=MagicMock(spec=concurrent.futures.ProcessPoolExecutor))
    ctx = WorkerContext(
        client=mock_client,
        rdi="test_rdi",
        studies_by_inv={"inv-assays": [MagicMock()]},
        assays_by_inv={"inv-assays": [MagicMock(), MagicMock()]},
        contacts_by_inv={},
        pubs_by_inv={},
        anns_by_inv={},
        worker_id=1,
        total_workers=1,
        pool_holder=pool_holder,
        arc_generation_timeout_minutes=1,
        max_studies=5000,
        max_assays=1,
    )

    await process_investigation(
        ctx,
        investigation,
        "Inv 1",
        _make_worker_res(client=mock_client, scope=scope, pool_holder=pool_holder, built_queue=built_queue),
    )
    report.finish()

    assert built_queue.empty()
    entry = report.repository_reports[0]
    assert entry.skipped_datasets == 1
    assert entry.harvested_datasets == 0
    assert entry.failed_datasets == 0
    assert entry.failures == ()
    mock_client.harvest_arcs.assert_not_called()


@pytest.mark.asyncio
async def test_process_investigations_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test full process_investigations flow with batching and harvest_arcs."""
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

    async def mock_harvest_arcs(
        *,
        rdi: str,
        arcs: AsyncIterator[Any],
        expected_datasets: int | None = None,
    ) -> HarvestResult:
        await _consume_arcs(arcs)
        assert expected_datasets == 2  # noqa: PLR2004
        return _harvest_ok(rdi=rdi)

    mock_client.harvest_arcs.side_effect = mock_harvest_arcs

    mock_config = MagicMock(spec=Config)
    mock_config.configure_mock(
        max_concurrent_arc_builds=2,
        max_concurrent_tasks=4,
        db_batch_size=10,
        rdi="test",
        debug_limit=10,
        arc_generation_timeout_minutes=30,
        max_studies=5000,
        max_assays=10000,
    )

    async def mock_process_inv(*_args: Any, **_kwargs: Any) -> None:
        pass

    monkeypatch.setattr("middleware.sql_to_arc.processor.process_investigation", mock_process_inv)

    report = await process_investigations(mock_db, mock_client, mock_config)

    assert isinstance(report, HarvestReport)
    assert len(report.repository_reports) == 1
    assert report.repository_reports[0].expected_datasets == 2  # noqa: PLR2004
    assert report.repository_reports[0].harvest_id == "harvest-1"
    mock_client.harvest_arcs.assert_called_once()
    mock_db.stream_investigations.assert_called()
    call_kwargs = mock_db.stream_investigations.call_args.kwargs
    assert isinstance(call_kwargs["scope"], RepositoryScope)
    assert call_kwargs["limit"] == 10  # noqa: PLR2004
    mock_client.create_or_update_arc.assert_not_called()


@pytest.mark.asyncio
async def test_process_investigations_records_harvest_item_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per-item harvest errors must record_failed; remaining submits record_harvested."""
    mock_db = MagicMock()
    mock_db.count_investigations = AsyncMock(return_value=2)

    async def mock_gen(**_kwargs: Any) -> AsyncGenerator[Any, None]:
        for item in (
            InvestigationRow(identifier="ok-1", title="T1", description_text="D1"),
            InvestigationRow(identifier="bad-1", title="T2", description_text="D2"),
        ):
            yield item

    mock_db.stream_investigations.side_effect = mock_gen

    async def mock_fetch_related(*_args: Any, **_kwargs: Any) -> RelatedDataBatch:
        return RelatedDataBatch(
            studies_by_inv={"ok-1": [MagicMock()], "bad-1": [MagicMock()]},
            assays_by_inv={"ok-1": [MagicMock()], "bad-1": []},
            contacts_by_inv={},
            pubs_by_inv={},
            anns_by_inv={},
            study_count=2,
            assay_count=1,
        )

    monkeypatch.setattr("middleware.sql_to_arc.processor._fetch_and_group_related_data", mock_fetch_related)

    async def mock_process_inv(
        _ctx: WorkerContext,
        investigation: InvestigationRow,
        inv_info: str,
        res: WorkerResources,
    ) -> None:
        inv_id = str(investigation.identifier)
        await res.built_queue.put(
            BuiltArc(
                arc_json=f'{{"identifier": "{inv_id}"}}',
                investigation_id=inv_id,
                inv_info=inv_info,
                composition=CompositionCounts(studies=1, assays=0),
            )
        )

    monkeypatch.setattr("middleware.sql_to_arc.processor.process_investigation", mock_process_inv)

    mock_client = AsyncMock(spec=ApiClient)

    async def mock_harvest_arcs(
        *,
        rdi: str,
        arcs: AsyncIterator[Any],
        expected_datasets: int | None = None,
    ) -> HarvestResult:
        _ = expected_datasets
        await _consume_arcs(arcs)
        result = _harvest_ok(rdi=rdi)
        return result.model_copy(
            update={
                "errors": [
                    HarvestError(
                        arc_id="bad-1",
                        error_type=HarvestErrorType.SUBMISSION_FAILED,
                        message="nope",
                    )
                ]
            }
        )

    mock_client.harvest_arcs.side_effect = mock_harvest_arcs

    mock_config = MagicMock(spec=Config)
    mock_config.configure_mock(
        max_concurrent_arc_builds=2,
        max_concurrent_tasks=4,
        db_batch_size=10,
        rdi="test",
        debug_limit=None,
        arc_generation_timeout_minutes=30,
        max_studies=5000,
        max_assays=10000,
    )

    report = await process_investigations(mock_db, mock_client, mock_config)
    entry = report.repository_reports[0]
    assert entry.harvest_id == "harvest-1"
    assert entry.harvested_datasets == 1
    assert entry.failed_datasets == 1
    assert entry.failures[0].record_id == "bad-1"
    assert entry.total_studies == 1
    mock_client.create_or_update_arc.assert_not_called()


@pytest.mark.asyncio
async def test_process_investigations_aborted_harvest_records_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catastrophic harvest_arcs failure must fail submitted investigations without legacy fallback."""
    mock_db = MagicMock()
    mock_db.count_investigations = AsyncMock(return_value=1)

    async def mock_gen(**_kwargs: Any) -> AsyncGenerator[Any, None]:
        yield InvestigationRow(identifier="inv-x", title="T1", description_text="D1")

    mock_db.stream_investigations.side_effect = mock_gen

    async def mock_fetch_related(*_args: Any, **_kwargs: Any) -> RelatedDataBatch:
        return RelatedDataBatch(
            studies_by_inv={},
            assays_by_inv={},
            contacts_by_inv={},
            pubs_by_inv={},
            anns_by_inv={},
            study_count=0,
            assay_count=0,
        )

    monkeypatch.setattr("middleware.sql_to_arc.processor._fetch_and_group_related_data", mock_fetch_related)

    async def mock_process_inv(
        _ctx: WorkerContext,
        investigation: InvestigationRow,
        inv_info: str,
        res: WorkerResources,
    ) -> None:
        inv_id = str(investigation.identifier)
        await res.built_queue.put(
            BuiltArc(
                arc_json=f'{{"identifier": "{inv_id}"}}',
                investigation_id=inv_id,
                inv_info=inv_info,
                composition=CompositionCounts(studies=0, assays=0),
            )
        )

    monkeypatch.setattr("middleware.sql_to_arc.processor.process_investigation", mock_process_inv)

    mock_client = AsyncMock(spec=ApiClient)

    async def mock_harvest_arcs(
        *,
        rdi: str,
        arcs: AsyncIterator[Any],
        expected_datasets: int | None = None,
    ) -> HarvestResult:
        _ = rdi
        _ = expected_datasets
        await _consume_arcs(arcs)
        raise ApiClientError("nope")

    mock_client.harvest_arcs.side_effect = mock_harvest_arcs

    mock_config = MagicMock(spec=Config)
    mock_config.configure_mock(
        max_concurrent_arc_builds=1,
        max_concurrent_tasks=2,
        db_batch_size=10,
        rdi="test",
        debug_limit=None,
        arc_generation_timeout_minutes=30,
        max_studies=5000,
        max_assays=10000,
    )

    report = await process_investigations(mock_db, mock_client, mock_config)
    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 0
    assert entry.failed_datasets == 1
    assert entry.failures[0].record_id == "inv-x"
    assert "Harvest upload failed" in entry.failures[0].message
    mock_client.create_or_update_arc.assert_not_called()


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
