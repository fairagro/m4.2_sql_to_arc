## 1. Dependency

- [ ] 1.1 Bump `fairagro-middleware-shared` to `>=11.0.1.dev29` (or newer with `middleware.shared.report`) in `middleware/sql_to_arc/pyproject.toml`
- [ ] 1.2 Run `uv lock` / `uv sync --dev --all-packages` and verify `from middleware.shared.report import HarvestReport, JsonLdReportSerializer, RepositoryScope` imports

## 2. Report lifecycle wiring

- [ ] 2.1 Add a small emit helper (serialize with `JsonLdReportSerializer`, print to stdout, log failures without changing exit codes)
- [ ] 2.2 In `main` / `process_investigations`: create `HarvestReport`, `open_repository(config.rdi)`, pass scope through processing, `finish()` after the loop, emit report
- [ ] 2.3 Replace post-run log summaries to read harvested/failed/skipped from the finished scope snapshot instead of `ProcessingStats`

## 3. Migrate counting call sites

- [ ] 3.1 `database.stream_investigations`: on validation failure call `scope.record_failed(...)`; remove `ProcessingStats` parameter
- [ ] 3.2 Add optional expected-dataset pre-count (`COUNT` / equivalent), apply `debug_limit` cap, call `scope.set_expected_datasets` when known
- [ ] 3.3 Upload success path: `scope.record_harvested()` then `add_studies` / `add_assays` for that investigation only
- [ ] 3.4 All failure paths (build errors, timeouts, upload errors, empty build): `scope.record_failed(message, record_id=...)`
- [ ] 3.5 Wire `scope.set_harvest_id` when an API-returned harvest id is available; otherwise leave unset
- [ ] 3.6 Ensure any intentional skip path calls `scope.record_skipped()` (add a clear hook even if unused today)
- [ ] 3.7 Delete `stats.py` and update all imports/types that referenced `ProcessingStats`

## 4. Tests

- [ ] 4.1 Replace `test_stats.py` with tests for emit helper / finished-report JSON-LD shape (shared vocabulary fields)
- [ ] 4.2 Update unit tests (`test_main`, `test_database`, processor tests) to use `HarvestReport` / scope assertions
- [ ] 4.3 Update integration workflow tests for new report emission and counting semantics (harvested only after success)
- [ ] 4.4 Assert failed records include investigation ids and that study/assay totals exclude failed investigations

## 5. Validate

- [ ] 5.1 Run `uv run ruff format .` and `uv run ruff check` on touched packages
- [ ] 5.2 Run `uv run pytest middleware/sql_to_arc/tests/ -v`
- [ ] 5.3 Run `openspec validate introduce-harvest-report --no-interactive`
