"""Smoke tests for the demo Middleware API harvest endpoints."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Iterator
from http import HTTPStatus
from pathlib import Path
from typing import Protocol, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.api_client import ArcResult, HarvestResult


class _ClearableMapping(Protocol):
    """Minimal store protocol; tests only call ``clear()``."""

    def clear(self) -> None: ...


class DemoApiModule(Protocol):
    """Typed surface of ``dev_environment/demo_api_main.py`` used by these tests."""

    app: FastAPI
    OUTPUT_ROOT: Path
    _harvests: _ClearableMapping
    _resolve_under_base: Callable[[Path, str], Path]


def _load_demo_api_module() -> DemoApiModule:
    """Load ``dev_environment/demo_api_main.py`` without requiring package install."""
    repo_root = Path(__file__).resolve().parents[4]
    module_path = repo_root / "dev_environment" / "demo_api_main.py"
    spec = importlib.util.spec_from_file_location("demo_api_main", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_api_main"] = module
    spec.loader.exec_module(module)
    return cast(DemoApiModule, module)


@pytest.fixture
def demo_api(tmp_path: Path) -> Iterator[DemoApiModule]:
    """Provide the demo FastAPI app with an isolated harvest store and output dir."""
    module = _load_demo_api_module()
    module._harvests.clear()
    module.OUTPUT_ROOT = tmp_path / "arcs"

    mock_arc = MagicMock()
    mock_arc.WriteAsync = MagicMock(return_value=None)

    with (
        patch.object(module, "ARC") as mock_arc_cls,
        patch.object(module, "start_as_task", new=AsyncMock(return_value=None)),
    ):
        mock_arc_cls.from_rocrate_json_string.return_value = mock_arc
        yield module

    module._harvests.clear()


@pytest.fixture
def client(demo_api: DemoApiModule) -> TestClient:
    """HTTP test client bound to the demo API app."""
    return TestClient(demo_api.app)


def test_demo_api_harvest_create_arcs_complete(client: TestClient, demo_api: DemoApiModule) -> None:
    """Create → submit ARC → complete must return HarvestResult/ArcResult-shaped JSON."""
    create_resp = client.post("/v3/harvests", json={"rdi": "demo-rdi", "expected_datasets": 1})
    assert create_resp.status_code == HTTPStatus.OK
    harvest = HarvestResult.model_validate(create_resp.json())
    assert harvest.rdi == "demo-rdi"
    assert harvest.status.value == "RUNNING"
    assert harvest.statistics.expected_datasets == 1

    bool_resp = client.post("/v3/harvests", json={"rdi": "demo-rdi", "expected_datasets": True})
    assert bool_resp.status_code == HTTPStatus.OK
    assert HarvestResult.model_validate(bool_resp.json()).statistics.expected_datasets is None

    arc_resp = client.post(
        f"/v3/harvests/{harvest.harvest_id}/arcs",
        json={"arc": {"identifier": "inv-1", "@context": {}, "@graph": []}},
    )
    assert arc_resp.status_code == HTTPStatus.OK
    arc_result = ArcResult.model_validate(arc_resp.json())
    assert arc_result.arc_id == "inv-1"
    assert arc_result.status.value == "created"

    complete_resp = client.post(f"/v3/harvests/{harvest.harvest_id}/complete")
    assert complete_resp.status_code == HTTPStatus.OK
    completed = HarvestResult.model_validate(complete_resp.json())
    assert completed.status.value == "COMPLETED"
    assert completed.statistics.arcs_submitted == 1
    assert completed.completed_at is not None

    get_resp = client.get(f"/v3/harvests/{harvest.harvest_id}")
    assert get_resp.status_code == HTTPStatus.OK
    assert HarvestResult.model_validate(get_resp.json()).status.value == "COMPLETED"

    live = client.get("/live")
    assert live.status_code == HTTPStatus.OK
    assert live.json() == {"status": "ok"}

    payload = demo_api.OUTPUT_ROOT / "inv-1.payload.json"
    assert payload.is_file()


def test_resolve_under_base_rejects_traversal(demo_api: DemoApiModule, tmp_path: Path) -> None:
    """Containment helper must reject path segments that escape the base dir."""
    base = tmp_path / "arcs"
    base.mkdir()
    with pytest.raises(ValueError, match="Unsafe relative path"):
        demo_api._resolve_under_base(base, "../etc")
    with pytest.raises(ValueError, match="Unsafe relative path"):
        demo_api._resolve_under_base(base, "a/b")
    resolved = demo_api._resolve_under_base(base, "inv-1.payload.json")
    assert resolved.parent == base.resolve()
    assert resolved.name == "inv-1.payload.json"


def test_demo_api_persist_failure_returns_error(demo_api: DemoApiModule, client: TestClient) -> None:
    """Failed ARC writes must not look like a successful created submission."""
    create_resp = client.post("/v3/harvests", json={"rdi": "demo-rdi", "expected_datasets": 1})
    harvest = HarvestResult.model_validate(create_resp.json())

    with patch.object(demo_api, "start_as_task", new=AsyncMock(side_effect=RuntimeError("write boom"))):
        arc_resp = client.post(
            f"/v3/harvests/{harvest.harvest_id}/arcs",
            json={"arc": {"identifier": "inv-fail", "@context": {}, "@graph": []}},
        )

    assert arc_resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "Failed to persist ARC" in arc_resp.json()["detail"]
    get_resp = client.get(f"/v3/harvests/{harvest.harvest_id}")
    assert HarvestResult.model_validate(get_resp.json()).statistics.arcs_submitted == 0
