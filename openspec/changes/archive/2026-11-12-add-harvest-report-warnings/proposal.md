# Proposal

## Why

Shared `HarvestReport` now has a per-repository warnings channel (`record_warning`, `warned_datasets` /
`fairagro:warnings`) from middleware #630 / shared 14.3.0. SQL-to-ARC still only logs non-fatal Edaphobase
accommodations (plain `study_ref`, duplicate-row merges, contact coercions) while successfully harvesting those
investigations, so operators cannot see warned-dataset counts in the JSON-LD report.

## What Changes

- Bump `fairagro-middleware-shared` to **≥14.3.0** (lock to a release that exposes `record_warning`).
- Collect structured build warnings in the worker for non-fatal accommodations that still produce an ARC.
- Return those warnings with the ARC JSON across the process boundary (no ARC/.NET pickling).
- On definitive upload success, call `scope.record_warning(...)` for each warning (does **not** change harvested /
  failed / skipped counts) in addition to `record_harvested` / composition counts.
- Extend OpenSpec `harvest-report` (and conversion/building notes as needed) for the warning drive path.
- Unit tests for warning recording and JSON-LD presence when shared serializer emits `fairagro:warnedDatasets` /
  `fairagro:warnings`.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `harvest-report`: Drive shared `record_warning` for non-fatal harvested-dataset outcomes; bump shared dependency
  contract.
- `sql-to-arc-conversion`: Worker build result MAY include JSON-serializable warning payloads alongside the ARC JSON
  string (still no ARC object IPC).
- `arc-building`: Builder MUST surface Edaphobase accommodation events as structured warnings (not logs alone) when an
  ARC is still produced.

## Impact

- Deps: `middleware/sql_to_arc/pyproject.toml`, `uv.lock`
- Code: `builder.py` (collect warnings), worker return type, `processor.py` / `pipeline.py` (`BuiltArc` carries
  warnings; apply on harvest success), tests under `middleware/sql_to_arc/tests/`
- Specs: `openspec/specs/harvest-report`, deltas for conversion / arc-building as above
