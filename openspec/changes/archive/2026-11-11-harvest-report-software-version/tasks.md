## 1. Dependency

- [x] 1.1 Bump `fairagro-middleware-shared` to `>=14.2.0` in `middleware/sql_to_arc/pyproject.toml`, refresh `uv.lock`,
      and verify
      `uv run python -c 'from middleware.shared.report import HarvestReport; HarvestReport(software_version="0")'`
      succeeds

## 2. Wiring

- [x] 2.1 Set `software_version=version("sql_to_arc")` when constructing `HarvestReport` in `process_investigations` and
      verify a unit test asserts the finished report field equals `version("sql_to_arc")`
- [x] 2.2 Log the installed PEP 440 version once at INFO in `main` after logging is configured and before
      `run_conversion`, and verify a unit test captures that log on a normal run
- [x] 2.3 Confirm `--version` still prints and exits without starting conversion (existing or updated unit test)

## 3. Specs / quality

- [x] 3.1 Keep change deltas coherent with implementation; run `openspec validate harvest-report-software-version` and
      verify it passes
- [x] 3.2 Run targeted unit tests (`test_main`, `test_reporting` / processor coverage) and verify they pass
