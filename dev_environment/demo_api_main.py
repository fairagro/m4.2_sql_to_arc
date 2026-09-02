"""
Demo API Mock for the FAIRagro SQL-to-ARC converter.

This module provides a lightweight FastAPI server that simulates the Middleware API.
It implements the harvest lifecycle used by ``ApiClient.harvest_arcs`` and writes
accepted ARC RO-Crate payloads to the local file system via arctrl.
"""

from __future__ import annotations

import json
import os
import re
import traceback
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arctrl import ARC, start_as_task
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

# Root directory under which all ARC data and error logs are stored.
OUTPUT_ROOT = Path("/data/arcs")

_SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})


@dataclass
class _HarvestRecord:
    """In-memory harvest session for the demo mock."""

    harvest_id: str
    rdi: str
    status: str
    started_at: str
    expected_datasets: int | None = None
    completed_at: str | None = None
    arcs_submitted: int = 0
    arcs_new: int = 0


_harvests: dict[str, _HarvestRecord] = {}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _get_target_owner() -> tuple[int, int] | None:
    uid_value = os.environ.get("LOCAL_UID")
    gid_value = os.environ.get("LOCAL_GID")
    if uid_value is None or gid_value is None:
        return None

    try:
        return int(uid_value), int(gid_value)
    except ValueError:
        print(f"Invalid LOCAL_UID/LOCAL_GID: {uid_value}/{gid_value}")
        return None


def _chown_tree(path: Path) -> None:
    owner = _get_target_owner()
    if owner is None or not path.exists():
        return

    uid, gid = owner

    def apply_ownership(target: Path) -> None:
        os.chown(target, uid, gid)

    apply_ownership(path)
    if path.is_dir():
        for root, dirs, files in os.walk(path):
            root_path = Path(root)
            apply_ownership(root_path)
            for name in dirs:
                apply_ownership(root_path / name)
            for name in files:
                apply_ownership(root_path / name)


def _handle_error(arc_dir: Path, rdi: str, arc_id: str, exc: Exception) -> None:
    tb = traceback.format_exc()
    print(f"Error writing ARC for {rdi}/{arc_id} (dir={arc_dir}): {exc}\n{tb}")


def _generate_random_arc_id() -> str:
    return f"arc_{os.urandom(4).hex()}"


def _derive_safe_arc_id(base_dir: Path, raw_id: object) -> tuple[str, Path]:
    """
    Derive a safe ARC identifier and corresponding directory path.

    Always returns a valid (arc_id, path) pair that is guaranteed to be
    contained within base_dir. Falls back to a random ID when the provided
    raw_id cannot be used safely.
    """
    base_real = Path(os.path.realpath(base_dir))

    def _fallback() -> tuple[str, Path]:
        rid = _generate_random_arc_id()
        return rid, base_real / rid

    if not (isinstance(raw_id, str) and raw_id.strip()):
        return _fallback()

    safe_name = os.path.normpath(Path(raw_id.strip()).name)
    if not safe_name or safe_name in {".", ".."} or not _SAFE_NAME_PATTERN.match(safe_name):
        return _fallback()

    candidate_real = Path(os.path.realpath(base_real / safe_name))
    if not str(candidate_real).startswith(str(base_real) + os.sep):
        return _fallback()

    return safe_name, candidate_real


def _arc_result(arc_id: str, rdi: str, now: str) -> dict[str, Any]:
    return {
        "arc_id": arc_id,
        "status": "created",
        "metadata": {
            "arc_hash": "demo_hash",
            "status": "ACTIVE",
            "first_seen": now,
            "last_seen": now,
        },
        "events": [],
        "message": "",
        "client_id": None,
    }


def _harvest_result(record: _HarvestRecord) -> dict[str, Any]:
    return {
        "harvest_id": record.harvest_id,
        "rdi": record.rdi,
        "status": record.status,
        "started_at": record.started_at,
        "completed_at": record.completed_at,
        "statistics": {
            "expected_datasets": record.expected_datasets,
            "arcs_submitted": record.arcs_submitted,
            "arcs_new": record.arcs_new,
            "arcs_updated": 0,
            "arcs_unchanged": 0,
            "arcs_missing": 0,
            "errors": 0,
        },
        "errors": [],
        "message": "",
        "client_id": None,
    }


async def _persist_arc_payload(rdi: str, arc_payload: dict[str, Any]) -> dict[str, Any]:
    """Write an ARC payload to disk and return an ApiClient-compatible ArcResult dict."""
    output_path = OUTPUT_ROOT
    output_path.mkdir(parents=True, exist_ok=True)
    _chown_tree(output_path)

    now = _now_iso()
    arc_id, arc_dir = _derive_safe_arc_id(output_path, arc_payload.get("identifier"))

    payload_path = arc_dir.with_suffix(".payload.json")
    with open(payload_path, "w", encoding="utf-8") as handle:
        json.dump(arc_payload, handle, indent=2)
    _chown_tree(payload_path)

    try:
        arc_json = json.dumps(arc_payload)
        arc = ARC.from_rocrate_json_string(arc_json)
        await start_as_task(arc.WriteAsync(str(arc_dir)))
        _chown_tree(arc_dir)
        print(f"Saved ARC structure for {rdi} as {arc_id} using arctrl")
    except (json.JSONDecodeError, OSError, RuntimeError) as exc:
        _handle_error(arc_dir, rdi, arc_id, exc)
    except Exception as exc:  # noqa: BLE001
        _handle_error(arc_dir, rdi, arc_id, exc)

    return _arc_result(arc_id, rdi, now)


def _require_harvest(harvest_id: str) -> _HarvestRecord:
    record = _harvests.get(harvest_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Harvest not found")
    return record


@app.post("/v3/harvests")
async def create_harvest(request: Request) -> dict[str, Any]:
    """Start a demo harvest run (``RUNNING``)."""
    data = await request.json()
    rdi = str(data.get("rdi") or "unknown")
    expected = data.get("expected_datasets")
    expected_datasets = expected if isinstance(expected, int) else None

    harvest_id = f"harvest-{uuid.uuid4()}"
    record = _HarvestRecord(
        harvest_id=harvest_id,
        rdi=rdi,
        status="RUNNING",
        started_at=_now_iso(),
        expected_datasets=expected_datasets,
    )
    _harvests[harvest_id] = record
    print(f"Created demo harvest {harvest_id} for rdi={rdi}")
    return _harvest_result(record)


@app.get("/v3/harvests/{harvest_id}")
async def get_harvest(harvest_id: str) -> dict[str, Any]:
    """Return a demo harvest by id."""
    return _harvest_result(_require_harvest(harvest_id))


@app.post("/v3/harvests/{harvest_id}/arcs")
async def submit_arc_in_harvest(harvest_id: str, request: Request) -> dict[str, Any]:
    """Accept an ARC under an active harvest and write it to disk."""
    record = _require_harvest(harvest_id)
    if record.status != "RUNNING":
        raise HTTPException(status_code=409, detail=f"Harvest is {record.status}")

    data = await request.json()
    arc_payload = data.get("arc", data)
    if not isinstance(arc_payload, dict):
        raise HTTPException(status_code=400, detail="ARC payload must be an object")

    result = await _persist_arc_payload(record.rdi, arc_payload)
    record.arcs_submitted += 1
    record.arcs_new += 1
    return result


@app.post("/v3/harvests/{harvest_id}/complete")
async def complete_harvest(harvest_id: str) -> dict[str, Any]:
    """Mark a demo harvest as ``COMPLETED``."""
    record = _require_harvest(harvest_id)
    record.status = "COMPLETED"
    record.completed_at = _now_iso()
    print(f"Completed demo harvest {harvest_id}")
    return _harvest_result(record)


@app.patch("/v3/harvests/{harvest_id}")
async def patch_harvest(harvest_id: str, request: Request) -> dict[str, Any]:
    """Set a terminal harvest status (``COMPLETED`` / ``FAILED`` / ``CANCELLED``)."""
    record = _require_harvest(harvest_id)
    data = await request.json()
    status = str(data.get("status") or "").upper()
    if status not in _TERMINAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unsupported status: {status}")
    record.status = status
    record.completed_at = _now_iso()
    print(f"Patched demo harvest {harvest_id} → {status}")
    return _harvest_result(record)


@app.post("/v3/arcs")
async def upload_arc(request: Request) -> dict[str, Any]:
    """Legacy single-ARC upload (kept for manual debugging)."""
    rdi = request.query_params.get("rdi")
    data = await request.json()
    arc_payload = data.get("arc", data)
    if rdi is None:
        rdi = str(data.get("rdi", "unknown"))
    if not isinstance(arc_payload, dict):
        raise HTTPException(status_code=400, detail="ARC payload must be an object")
    return await _persist_arc_payload(str(rdi), arc_payload)


@app.get("/live")
def live() -> dict[str, str]:
    """Liveness probe for the demo API."""
    return {"status": "ok"}
