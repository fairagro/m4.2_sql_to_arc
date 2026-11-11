# ARC export fixture gate (`system_local`)

Representative RO-Crate fixtures from SQL-to-ARC are validated with the same DataHUB check (`arc-export`) via
`fairagro-middleware-arc-validation`, so mapping regressions that break export are caught in client CI before upload.

This mirrors the harvester client gate (`m4.2_middleware_harvester` #474 / PR #602).

## Requirements

- Docker (socket access to pull/run images)
- Dev dependency: `fairagro-middleware-arc-validation` (installed with `uv sync --dev --all-packages`)

## Run locally

```bash
uv sync --dev --all-packages
uv run pytest -m system_local middleware/sql_to_arc/tests/system_local -v --no-cov
```

Default commit-stage / pre-push pytest **excludes** `system_local` (no Docker required on every push).

### Image / PATH note

`ghcr.io/nfdi4plants/arc-export` ships the binary as `/arc-export`, while the validation package invokes the command
`arc-export`. The test suite builds a thin local tag (`fairagro-arc-export-path:ci`) that symlinks
`/usr/local/bin/arc-export` → `/arc-export`, unless you already set `FAIRAGRO_ARC_EXPORT_IMAGE`.

Base image digest SoT: `middleware/sql_to_arc/tests/system_local/arc-export-base.digest` (CI and local wrapper build
both read it). Override the final image anytime:

```bash
export FAIRAGRO_ARC_EXPORT_IMAGE='ghcr.io/nfdi4plants/arc-export@sha256:…'  # only if PATH is fixed
# or any image where `arc-export` is on PATH
```

## Fixture layout

```text
middleware/sql_to_arc/tests/fixtures/arc_export/<name>/ro-crate-metadata.json
```

MVP names:

- `known_good` — must pass `validate_rocrate`
- `known_bad` — must fail with a readable `cause_excerpt`

## Add a fixture after a DataHUB / production failure

1. Capture the failing RO-Crate (or regenerate from the SQL-to-ARC investigation that failed `arc-export`).
2. Add it under `tests/fixtures/arc_export/<name>/` (new directory with `ro-crate-metadata.json`).
3. Run `uv run pytest -m system_local middleware/sql_to_arc/tests/system_local -v --no-cov` — expect **fail** with a
   readable `cause_excerpt` for a new known-good candidate that is still broken.
4. Fix the mapper / builder; re-run until green; commit fixture + fix together when possible.
