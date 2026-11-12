# Tasks

## 1. Dependency

- [x] 1.1 Bump `fairagro-middleware-shared` to `>=14.3.0` in `middleware/sql_to_arc/pyproject.toml` and refresh
      `uv.lock` (`uv lock` / `uv sync`); verify `RepositoryScope.record_warning` importable

## 2. Builder warnings + worker result

- [x] 2.1 Add `BuildWarning` / `ArcBuildResult` (arc JSON + warnings tuple); change `build_single_arc_task` to return
      `ArcBuildResult`; collect structured warnings from Edaphobase accommodation helpers when counts &gt; 0 — unit
      tests for plain `study_ref` and duplicate assay merge
- [x] 2.2 Update all call sites/tests that expect a bare `str` from `build_single_arc_task` to use `.arc_json`

## 3. Report wiring

- [x] 3.1 Extend `BuiltArc` with warnings; propagate from processor; on upload success in `_apply_upload_outcomes`, call
      `scope.record_warning` per warning after `record_harvested` — unit test asserting warned count / JSON-LD
      `fairagro:warnedDatasets` without changing failed/skipped

## 4. Verify

- [x] 4.1 Run focused `uv run pytest` on affected unit/integration tests;
      `openspec validate add-harvest-report-warnings`; ruff format/check on touched Python

## Workflow follow-up

- Draft PR after user commit (`Fixes #339`)
- Archive change after merge / last `go`
