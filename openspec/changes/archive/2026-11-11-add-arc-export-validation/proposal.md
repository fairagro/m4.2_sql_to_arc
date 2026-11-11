## Why

DataHUB CI rejects some client-written ARCs at `arc-export`. SQL-to-ARC should catch the same failures in client CI
before upload. The shared package `fairagro-middleware-arc-validation` (API #317) is on PyPI; the harvester already
gates RO-Crate fixtures the same way (#474 / PR #602). This change mirrors that pattern for SQL-to-ARC outputs.

## What Changes

- Depend on `fairagro-middleware-arc-validation>=14.2.0` (dev/test).
- Commit a small set of real RO-Crate fixtures from SQL-to-ARC (at least one known-good; one known-bad for clear
  `cause_excerpt`).
- Add `system_local` pytest that calls `validate_rocrate` (Docker `arc-export`, DataHUB-equivalent defaults).
- Add a Feature-PR CI job with Docker; pin image digest; PATH wrapper for `/arc-export` → `arc-export` (same as
  harvester).
- Keep pre-push free of Docker (`system_local` already excluded).
- Document local run and how to add a fixture after a DataHUB failure.

## Capabilities

### New Capabilities

- `arc-export-validation`: Gate committed SQL-to-ARC RO-Crate fixtures with DataHUB-equivalent `arc-export` via the
  shared validation library (`system_local` + CI).

### Modified Capabilities

- (none)

## Impact

- `middleware/sql_to_arc` test tree + `pyproject.toml` / `uv.lock`
- New docs (product-local) for the fixture gate
- Feature-PR workflow (new Docker job; not folded into reusable-code-quality)
- No change to converter runtime upload path
