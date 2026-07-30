## Context

See `proposal.md` for motivation. Today `ProcessingStats` accumulates
`found_datasets` / `failed_*` / study/assay totals and `main.py` prints
`to_jsonld()`. Shared `middleware.shared.report` already provides the
counting + JSON-LD path the harvester uses. This change wires sql_to_arc to
that API end-to-end.

Constraints: single RDI per run; asyncio fan-out mutates one scope;
worker IPC stays JSON-only; no `os.environ`; bump
`fairagro-middleware-shared` to a build that exports `middleware.shared.report`
(harvester pins `>=11.0.1.dev29`).

## Goals / Non-Goals

**Goals:**

- Own all report statistics in `HarvestReport` / `RepositoryScope`
- Use every counting feature that applies: expected, harvest id, harvested,
  failed (with detail), skipped, studies, assays, finish + JSON-LD emit
- Align success semantics with the shared contract (harvested only after
  definitive upload success)
- Keep exit-code policy unchanged (partial failures → 0)

**Non-Goals:**

- Multi-RDI scopes or harvester plugin orchestration patterns
- Preserving the old PROV/`void` stdout document
- Changing `ApiClient` / Middleware API contracts
- A second serializer format

## Decisions

1. **Delete `ProcessingStats` rather than wrap it**
   — Parallel counters are explicitly forbidden by the shared contract and
   our `harvest-report` delta. Passing `RepositoryScope` (or a thin
   run-context holding `HarvestReport` + scope) through `database` /
   `processor` / `main` is clearer than a facade over the old model.

2. **Lifecycle ownership in `main` / `process_investigations`**
   — Create `HarvestReport(name="SQL to ARC Conversion Run")` at run start,
   `open_repository(config.rdi)`, pass the scope into processing, call
   `report.finish()` after the loop (success or partial failure), then
   `JsonLdReportSerializer().render(report)` to stdout. Duration comes from
   start/finish timestamps — drop manual `duration_seconds` assignment.

3. **`record_harvested` only after successful upload**
   — Matches shared/harvester guidance. Today `found_datasets` increments on
   stream sighting; that over-counts relative to harvested. Streaming a valid
   row MUST NOT call `record_harvested`.

4. **`set_expected_datasets` via optional pre-count when cheap**
   — Prefer a `COUNT(*)` (or equivalent) on `vInvestigation` before the
   stream when the dialect supports it, then apply `debug_limit` as an upper
   bound (`min(count, debug_limit)` when set). If the count query is
   unavailable or fails, leave expected unset (omit on the wire) rather than
   inventing a number from partial progress.

5. **`set_harvest_id` only when the API returns one**
   — `create_or_update_arc` today does not expose a harvest id to sql_to_arc.
   Leave harvest id unset (`null` on the wire) unless/until the client API
   returns a usable id. Still call the setter when such a value appears so
   the feature path stays wired.

6. **`record_failed` for aborting dataset failures; `record_skipped` for
   intentional skips**
   — Validation failures, build errors, timeouts, and upload errors use
   `record_failed(message, record_id=investigation_id)`. Reserve
   `record_skipped` for explicit intentional skips (none required today
   beyond keeping the call site ready if a skip path is added). Do not
   reclassify harvested → failed.

7. **`add_studies` / `add_assays` only for successfully harvested
   investigations**
   — Move composition increments from batch-level totals of all streamed
   rows to per-investigation counts after upload success (len of that
   investigation's studies/assays). Avoids inflating totals for failed
   datasets and matches harvester semantics.

8. **Thread-safe scope updates under asyncio**
   — Shared `RepositoryScope` already locks; concurrent tasks MAY call
   counting methods without an extra sql_to_arc lock.

9. **Emission helper local to sql_to_arc**
   — Small `emit_report(report)` (print serializer output, log on failure)
   similar to the harvester helper. Do not add a shared stdout helper.

10. **Dependency pin**
    — Raise `fairagro-middleware-shared` to `>=11.0.1.dev29` (or the first
    stable release that includes `middleware.shared.report`) and refresh
    the lockfile.

## Risks / Trade-offs

- **[Risk] Operators/scripts parse the old JSON-LD** → Mitigation: document
  **BREAKING** stdout change; point to `ns/harvest-report/v1/`.
- **[Risk] COUNT(*) adds a round-trip / may be slow on huge views** →
  Mitigation: single aggregate before stream; on failure, omit expected.
- **[Trade-off] found_datasets disappears as a metric** → Harvested + failed +
  skipped + optional expected replace it; log summaries read from the scope
  snapshot after finish.
- **[Risk] Dev builds without new shared package** → Mitigation: pin and
  `uv lock` in the same change; CI installs from PyPI/TestPyPI as today.

## Migration Plan

1. Bump shared dependency and confirm `from middleware.shared.report import …`
   works in the venv.
2. Introduce report lifecycle in `main` / processor; migrate call sites off
   `ProcessingStats`.
3. Update unit/integration tests to assert shared wire fields and counting
   semantics.
4. Remove `stats.py` / `test_stats.py` (or reduce to emission helper tests).
5. Smoke via demo stack: stdout matches shared JSON-LD shape.

## Open Questions

- None blocking. If `ApiClient.create_or_update_arc` later returns a harvest
  id, wire `set_harvest_id` without a spec change beyond using the already
  required setter path.
