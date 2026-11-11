"""Validate committed RO-Crate fixtures with DataHUB-equivalent arc-export."""

from __future__ import annotations

from pathlib import Path

import pytest

from middleware.arc_validation import validate_rocrate

pytestmark = pytest.mark.system_local

_FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "arc_export"


def test_arc_export_fixture_passes(arc_export_fixture_dir: Path, arc_export_image: str) -> None:
    """Each committed known-good fixture must pass shared arc-export validation."""
    crate_path = arc_export_fixture_dir / "ro-crate-metadata.json"
    crate = crate_path.read_text(encoding="utf-8")
    result = validate_rocrate(crate, image=arc_export_image)
    assert result.ok, (
        f"{crate_path.relative_to(_FIXTURES_ROOT.parent)} failed arc-export "
        f"(exit {result.exit_code}): {result.cause_excerpt or result.stderr or result.stdout}"
    )


def test_known_good_fixture_present(arc_export_fixture_dirs: list[Path]) -> None:
    """MVP includes at least the known_good fixture directory."""
    names = {path.name for path in arc_export_fixture_dirs}
    assert "known_good" in names


def test_known_bad_fixture_fails_with_cause_excerpt(arc_export_image: str) -> None:
    """Known-bad fixture must fail validation with a readable cause excerpt."""
    crate_path = _FIXTURES_ROOT / "known_bad" / "ro-crate-metadata.json"
    assert crate_path.is_file(), f"Missing known-bad fixture at {crate_path}"
    result = validate_rocrate(crate_path.read_text(encoding="utf-8"), image=arc_export_image)
    assert not result.ok
    excerpt = (result.cause_excerpt or result.stderr or result.stdout or "").strip()
    assert excerpt, "expected a non-empty cause_excerpt (or stderr/stdout) for known-bad fixture"
