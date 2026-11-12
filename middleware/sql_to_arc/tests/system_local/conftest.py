"""Docker helpers for arc-export system_local tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_SYSTEM_LOCAL_DIR = Path(__file__).resolve().parent
# Single SoT for the pinned base image (CI reads the same file).
ARC_EXPORT_BASE_DIGEST = (_SYSTEM_LOCAL_DIR / "arc-export-base.digest").read_text(encoding="utf-8").strip()
ARC_EXPORT_WRAPPER_TAG = "fairagro-arc-export-path:ci"
IMAGE_ENV_VAR = "FAIRAGRO_ARC_EXPORT_IMAGE"

FIXTURES_ROOT = _SYSTEM_LOCAL_DIR.parents[0] / "fixtures" / "arc_export"

# Directory names under FIXTURES_ROOT that must never be parametrized as known-good.
# Negative cases are asserted explicitly in test_known_bad_fixture_fails_with_cause_excerpt.
NEGATIVE_FIXTURE_DIR_NAMES = frozenset({"known_bad"})


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    probe = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["docker", "info"],
        check=False,
        capture_output=True,
        text=True,
    )
    return probe.returncode == 0


def _ensure_path_wrapper_image() -> str:
    """Build a local image where ``arc-export`` is on PATH (upstream image only has ``/arc-export``)."""
    dockerfile = f"FROM {ARC_EXPORT_BASE_DIGEST}\nRUN ln -sf /arc-export /usr/local/bin/arc-export\n"
    build = subprocess.run(  # noqa: S603
        ["docker", "build", "-t", ARC_EXPORT_WRAPPER_TAG, "-f-", "."],
        check=False,
        capture_output=True,
        text=True,
        input=dockerfile,
        cwd="/tmp",
    )
    if build.returncode != 0:
        msg = build.stderr or build.stdout or "docker build failed"
        pytest.fail(f"Failed to build arc-export PATH wrapper image: {msg}")
    return ARC_EXPORT_WRAPPER_TAG


def _discover_fixture_dirs(*, exclude: set[str] | None = None) -> list[Path]:
    skip = exclude or set()
    if not FIXTURES_ROOT.is_dir():
        return []
    return sorted(
        path
        for path in FIXTURES_ROOT.iterdir()
        if path.is_dir() and path.name not in skip and (path / "ro-crate-metadata.json").is_file()
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize each known-good RO-Crate fixture directory as its own test case."""
    if "arc_export_fixture_dir" not in metafunc.fixturenames:
        return
    dirs = _discover_fixture_dirs(exclude=set(NEGATIVE_FIXTURE_DIR_NAMES))
    metafunc.parametrize(
        "arc_export_fixture_dir",
        dirs,
        ids=[path.name for path in dirs],
    )


@pytest.fixture(scope="session")
def arc_export_image() -> str:
    """Resolve the Docker image for ``validate_rocrate`` (env override or local PATH wrapper)."""
    if not _docker_available():
        pytest.skip("Docker is required for system_local arc-export fixtures")
    override = os.environ.get(IMAGE_ENV_VAR, "").strip()
    if override:
        return override
    return _ensure_path_wrapper_image()


@pytest.fixture(scope="session")
def arc_export_fixture_dirs() -> list[Path]:
    """Known-good fixture directories that contain ``ro-crate-metadata.json``."""
    dirs = _discover_fixture_dirs(exclude=set(NEGATIVE_FIXTURE_DIR_NAMES))
    if not FIXTURES_ROOT.is_dir():
        pytest.fail(f"Missing fixtures root: {FIXTURES_ROOT}")
    if not dirs:
        pytest.fail(f"No known-good ro-crate-metadata.json fixtures under {FIXTURES_ROOT}")
    return dirs
