## 1. Dependency

- [ ] 1.1 Add `fairagro-middleware-arc-validation>=14.2.0` as a sql_to_arc **dev** dependency and refresh the lockfile;
      verify with `uv run python -c 'from middleware.arc_validation import validate_rocrate'`

## 2. Fixtures + system_local tests

- [ ] 2.1 Add fixture layout `middleware/sql_to_arc/tests/fixtures/arc_export/<name>/ro-crate-metadata.json` with at
      least one known-good and one known-bad RO-Crate (produce good fixture offline so it already passes `arc-export`
      locally)
- [ ] 2.2 Add `middleware/sql_to_arc/tests/system_local/` with digest SoT, PATH-wrapper helper (harvester mirror),
      parametrized known-good `validate_rocrate(...).ok` tests, and a known-bad case asserting failure + non-empty
      `cause_excerpt`; mark `system_local` and skip clearly when Docker is missing
- [ ] 2.3 Document local run in `docs/arc-export-fixtures.md` (Docker, pytest `-m system_local`, image override, how to
      add a fixture after DataHUB failure)

## 3. CI

- [ ] 3.1 Add a Feature-PR job (Docker on `ubuntu-latest`) that builds the PATH wrapper from the digest file, sets
      `FAIRAGRO_ARC_EXPORT_IMAGE`, and runs `uv run pytest -m system_local middleware/sql_to_arc/tests/system_local`;
      skip when the Feature `code` path filter is false

## 4. OpenSpec quality

- [ ] 4.1 Run `openspec validate add-arc-export-validation` and verify it passes

## Workflow follow-up

- After apply + user commit: draft PR with `Fixes #86`
- Last `go`: archive this change and sync `arc-export-validation` into main specs
