# ARC Export Validation — Design

## Context

Harvester #474 / PR #602 is the reference client gate. Shared package `fairagro-middleware-arc-validation` ≥14.2.0
provides `validate_rocrate` / `FAIRAGRO_ARC_EXPORT_IMAGE`. This repo’s pre-push pytest already excludes `system_local`.

## Key Decisions

1. **Mirror harvester layout** — Fixtures under `middleware/sql_to_arc/tests/fixtures/arc_export/<name>/` and helpers
   under `tests/system_local/` (digest SoT + PATH wrapper tag).

2. **Pre-baked fixtures** — Commit RO-Crate JSON; refresh offline when mappings change. Do not run demo-DB → convert
   inside the MVP CI job.

3. **Dev dependency** — `fairagro-middleware-arc-validation>=14.2.0` on `sql_to_arc` (test-only).

4. **Markers / CI** — `@pytest.mark.system_local`; Feature-PR job builds PATH wrapper from `arc-export-base.digest`,
   sets `FAIRAGRO_ARC_EXPORT_IMAGE`, runs the suite with `--no-cov`.

5. **Known-good / known-bad** — Known-good crates are produced via `build_single_arc_task` from representative view-row
   models. `known_bad` (and names in `NEGATIVE_FIXTURE_DIR_NAMES`) are never parametrized as pass cases.

6. **Docs** — Product-local `docs/arc-export-fixtures.md`.
