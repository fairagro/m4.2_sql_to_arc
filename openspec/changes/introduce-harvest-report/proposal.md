## Why

SQL-to-ARC still owns its own `ProcessingStats` counters and emits a bespoke
PROV/Schema.org JSON-LD report at end of run. `fairagro-middleware-shared`
now ships a shared `HarvestReport` accumulator (counting API +
`JsonLdReportSerializer`) used by the Middleware Harvester. Adopting it
aligns operator-facing stdout with the common harvest-report contract and
removes duplicated counter/serialization logic — without a 1:1 port of the
old wire shape.

## What Changes

- Replace `ProcessingStats` accumulation and `to_jsonld()` with
  `middleware.shared.report.HarvestReport` / `RepositoryScope` counting
  methods and `JsonLdReportSerializer` emission to stdout.
- Drive **all** shared counting features that apply to this single-RDI tool:
  run lifecycle (`HarvestReport` → `open_repository` → `finish`),
  `set_expected_datasets` when a total is known, `set_harvest_id` when the
  API yields one, `record_harvested` only after definitive upload success,
  `record_failed` (with message + investigation id) on failures,
  `record_skipped` for intentional dataset skips, and `add_studies` /
  `add_assays` for successfully harvested investigations.
- **BREAKING** (stdout contract): end-of-run JSON-LD switches from the
  sql_to_arc-only PROV/`void` shape to the shared harvester baseline
  (`schema:Action` + `schema:result` of `EntryPoint`s under
  `ns/harvest-report/v1/`).
- Bump `fairagro-middleware-shared` to a release that includes
  `middleware.shared.report` (e.g. `>=11.0.1.dev29`).
- Remove `stats.py` report serialization (and the stats model once call
  sites are migrated).

## Capabilities

### New Capabilities

- `harvest-report`: How sql_to_arc initialises, updates, finishes, and
  prints the shared `HarvestReport` (consumer wiring only — does not
  restate the shared library contract).

### Modified Capabilities

- `sql-to-arc-conversion`: End-of-run report requirement moves from custom
  provenance JSON-LD to shared HarvestReport emission; process lifecycle
  owns report start/finish.
- `api-upload`: Success/failure accounting goes through `RepositoryScope`
  (`record_harvested` / `record_failed`) instead of `ProcessingStats`.
- `database-access`: Invalid investigation rows update the shared scope
  (`record_failed`) instead of `ProcessingStats`.

## Impact

- **Code:** `main.py`, `processor.py`, `database.py`; delete or gut
  `stats.py`; tests (`test_stats.py`, `test_main.py`, processor/database
  unit + integration).
- **Dependency:** `fairagro-middleware-shared` version bump.
- **Operators:** stdout JSON-LD shape changes; parsers of the old report
  must switch to the shared vocabulary.
- **Non-goals:** Changing Middleware API / `api_client` behavior; adding
  multi-RDI scopes; keeping PROV/`actionStatus`/`void` terms; implementing
  new shared serializers beyond `JsonLdReportSerializer`.
