## Why

Operators need the PEP 440 package/image version for every SQL-to-ARC conversion run. `--version` already prints and
exits, but a normal job does not log the version at start and the final harvest report does not carry it. Shared
`HarvestReport.software_version` (API #598 / shared ≥14.2.0) and Harvester #508 establish the fleet pattern; this
product still locks shared 12.3.0 and omits the field.

## What Changes

- Bump `fairagro-middleware-shared` (and lockfile) to **≥14.2.0** so `HarvestReport.software_version` is available.
- At conversion job start, resolve `importlib.metadata.version("sql_to_arc")` (same source as `--version`) and log it at
  INFO once before conversion.
- When constructing the run `HarvestReport`, set `software_version` to that installed distribution version (Harvester
  parity).
- Keep existing `--version` CLI behavior unchanged.
- Tests cover start log + report field wiring; OpenSpec deltas under harvest-report / sql-to-arc-conversion.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `harvest-report`: Require setting `software_version` on the run report from the installed `sql_to_arc` distribution.
- `sql-to-arc-conversion`: Require an INFO start log of the PEP 440 version on every conversion run (not only
  `--version`).

## Impact

- Code: `middleware/sql_to_arc/src/middleware/sql_to_arc/main.py`, `processor.py`; unit tests under
  `middleware/sql_to_arc/tests/`.
- Dependencies: `fairagro-middleware-shared` bump in `middleware/sql_to_arc/pyproject.toml` + root `uv.lock` (may pull
  related shared/api-client resolution).
- No change to DB views, ARC building, or upload semantics.

## Non-goals

- Changing `--version` output format or exit behavior.
- Soft-fail / `None` when metadata is missing (`read_distribution_version`); hard `version("sql_to_arc")` like
  Harvester.
- API HTTP version endpoints (API #588) — out of scope for this batch job.
