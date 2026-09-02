"""Smoke tests for the demo Middleware API harvest endpoints."""

from __future__ import annotations

import importlib.util
import sys
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from middleware.api_client import ArcResult, HarvestResult


def _load_demo_api_module() -> Any:
    """Load ``dev_environment/demo_api_main.py`` without requiring package install."""
    repo_root = Path(__file__).resolve().parents[4]
    module_path = repo_root / "dev_environment" / "demo_api_main.py"
    spec = importlib.util.spec_from_file_location("demo_api_main", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_api_main"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def demo_api(tmp_path: Path) -> Any:
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
def client(demo_api: Any) -> TestClient:
    """HTTP test client bound to the demo API app."""
    return TestClient(demo_api.app)


def test_demo_api_harvest_create_arcs_complete(client: TestClient, demo_api: Any) -> None:
    """Create → submit ARC → complete must return HarvestResult/ArcResult-shaped JSON."""
    create_resp = client.post("/v3/harvests", json={"rdi": "demo-rdi", "expected_datasets": 1})
    assert create_resp.status_code == HTTPStatus.OK
    harvest = HarvestResult.model_validate(create_resp.json())
    assert harvest.rdi == "demo-rdi"
    assert harvest.status.value == "RUNNING"
    assert harvest.statistics.expected_datasets == 1

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
