"""
Demo API Mock for the FAIRagro SQL-to-ARC converter.

This module provides a lightweight FastAPI server that simulates the Middleware API.
It receives ARC RO-Crate payloads, deserializes them using the arctrl library,
and writes the resulting ARC directory structure to the local file system.
"""

import json
import os
import traceback
from datetime import UTC, datetime
from pathlib import Path

from arctrl import ARC
from arctrl.py.fable_modules.fable_library.async_ import start_as_task  # type: ignore[import-untyped]
from fastapi import FastAPI, Request

app = FastAPI()


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
    """
    Log and store error information when ARC processing fails.

    Args:
        arc_dir: The directory where the ARC was supposed to be saved.
        rdi: The RDI identifier.
        arc_id: The ARC identifier.
        exc: The exception that occurred.
    """
    tb = traceback.format_exc()
    print(f"Error writing ARC for {rdi}/{arc_id}: {exc}")
    arc_dir.mkdir(parents=True, exist_ok=True)
    error_path = arc_dir / "error.txt"
    with open(error_path, "w", encoding="utf-8") as handle:
        handle.write(str(exc))
        handle.write("\n\n")
        handle.write(tb)
    _chown_tree(arc_dir)


@app.post("/v3/arcs")
async def upload_arc(request: Request) -> dict[str, str | dict[str, str]]:
    """
    Handle the submission of an ARC RO-Crate.

    This endpoint receives the RO-Crate JSON-LD payload, validates it,
    and uses the arctrl library to reconstruct the ARC directory structure.
    The resulting files are saved to the local 'demo_output' volume.

    Args:
        rdi: The identifier of the Research Data Infrastructure.
        payload: The request body containing the 'arc' (RO-Crate JSON).

    Returns:
        A dictionary matching the ArcResult schema expected by the ApiClient.
    """
    rdi = request.query_params.get("rdi")
    data = await request.json()
    arc_payload = data.get("arc", data)

    if rdi is None:
        rdi = data.get("rdi", "unknown")

    output_path = Path("/data/arcs")
    output_path.mkdir(parents=True, exist_ok=True)
    _chown_tree(output_path)  # Ensure the root output dir belongs to the host user

    # Derive a safe ARC identifier from the payload. The ARC identifier is used
    # as a directory name below, so ensure it cannot escape the output_path.
    raw_arc_id = arc_payload.get("identifier")
    if isinstance(raw_arc_id, str) and raw_arc_id.strip():
        candidate_id = raw_arc_id.strip()
        # Prevent absolute paths and directory components; keep only the final name.
        if Path(candidate_id).is_absolute():
            candidate_id = f"arc_{os.urandom(4).hex()}"
        safe_name = Path(candidate_id).name
        if not safe_name:
            arc_id = f"arc_{os.urandom(4).hex()}"
        else:
            arc_id = safe_name
    else:
        arc_id = f"arc_{os.urandom(4).hex()}"

    now = datetime.now(UTC).isoformat()
    arc_dir = output_path / arc_id
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

    return {
        "arc_id": arc_id,
        "status": "created",
        "metadata": {
            "rdi": rdi,
            "arc_hash": "demo_hash",
            "status": "ACTIVE",
            "first_seen": now,
            "last_seen": now,
        },
    }


@app.get("/live")
def live() -> dict[str, str]:
    """
    Liveness probe for the demo API.

    Returns:
        dict: A simple status indicator.
    """
    return {"status": "ok"}
