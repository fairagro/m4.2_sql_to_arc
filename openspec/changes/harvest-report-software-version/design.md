## Context

See `proposal.md` — Why. Shared `HarvestReport.software_version` and JSON-LD emission shipped in
`fairagro-middleware-shared` ≥14.2.0 (API #598 / #645). Harvester sets
`HarvestReport(software_version=version("harvester"))` at orchestrator construction. This product still constructs
`HarvestReport(name="SQL to ARC Conversion Run")` in `process_investigations` and only reads metadata for `--version`.

## Goals / Non-Goals

**Goals**

- Fleet parity with Harvester: hard `importlib.metadata.version("sql_to_arc")` for both start log and report field.
- Minimal surface: bump shared, wire ctor + one INFO log, tests + OpenSpec deltas.

**Non-Goals**

- Soft `None` via `read_distribution_version` when metadata is missing.
- Changing `--version` formatting or adding new CLI flags.
- Restating the shared JSON-LD vocabulary in product specs.

## Decisions

1. **Bump shared to ≥14.2.0 before wiring** — reasoning: choose published PyPI shared over git pin so `software_version`
   exists at runtime; without the bump the ctor kwarg fails. Prefer locking the fleet release that shipped #645 over
   inventing a product shim.

2. **Set `software_version` at `HarvestReport` construction in `process_investigations`** — reasoning: choose ctor over
   post-hoc assignment because Harvester does the same and the report is owned there; avoid a second mutation path in
   `main`.

3. **INFO log in `main` after config/logging setup, before `run_conversion`** — reasoning: choose `main` over the
   processor so the log appears even if conversion fails early after config load, and so logging level from config is
   already applied. Still call `version("sql_to_arc")` (same as `--version`), not a duplicated string.

4. **Hard `version(...)`; do not catch `PackageNotFoundError` on the conversion path** — reasoning: choose Harvester
   parity over soft-fail; CI/image/`uv sync` installs the distribution. Dev-only “source tree without install” remains
   an operator setup issue, same as today for imports.

## Risks / Trade-offs

- [Shared/api-client resolution churn on lock bump] → Mitigate: run `uv lock` / `uv sync` and full unit tests; bump
  api-client only if the resolver requires it.
- [`PackageNotFoundError` on bare checkouts] → Mitigate: document that conversion expects an installed package (existing
  `--version` already does); no soft path in MVP.

## Migration Plan

1. Land dependency bump + code + tests on the issue branch.
2. No runtime data migration; first run after deploy emits version in logs and JSON-LD.
3. Rollback: revert PR (shared pin and wiring are coupled).

## Open Questions

None — option A locked with the user (Harvester 1:1).
