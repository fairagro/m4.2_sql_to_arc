# Design

## Context

See proposal.md — Why. Shared `RepositoryScope.record_warning` exists in `fairagro-middleware-shared` ≥14.3.0. Today
`build_single_arc_task` returns only an ARC JSON `str`; Edaphobase accommodations are logged inside the worker and never
reach the main-process harvest report. `BuiltArc` already carries composition counts applied on upload success.

## Goals / Non-Goals

**Goals:**

- End-to-end: accommodation → structured warning → `record_warning` on harvest success → JSON-LD
  `fairagro:warnedDatasets` / `fairagro:warnings`.
- Keep JSON-only / no-ARC-pickle worker IPC.
- Minimal first warning kinds: plain `study_ref`, duplicate assay-row merge, and existing contact coercions already
  aggregated in builder helpers (native roles / missing given name) when counts &gt; 0.

**Non-Goals:**

- Changing hard-failure semantics (`DuplicateAssayRowError` / `DuplicateStudyRowError`).
- Warning on missing optional views, pool recreate, or report serialize failures (run/ops noise, not per-dataset harvest
  accommodations).
- Harvester-specific warning kinds; shared report schema changes (already shipped upstream).

## Decisions

1. **Return a small pure-Python result from the worker** — frozen dataclass / NamedTuple with `arc_json: str` and
   `warnings: tuple[BuildWarning, ...]` (`message: str`, optional `kind: str`). Rationale: avoids wrapping megabyte ARC
   JSON inside another JSON document; still pickles only strings (no ARC/.NET). Alternative rejected: single envelope
   JSON with embedded ARC string (double-escape cost).

2. **Apply warnings on harvest success** — store warnings on `BuiltArc`; in `_apply_upload_outcomes`, after
   `record_harvested`, call `record_warning(message, record_id=inv_id)` per warning. Rationale: matches AC (“still
   produce a harvested ARC”). Upload failures do not attribute build accommodations as warned-but-failed noise.

3. **One report entry per aggregated log family** — reuse builder aggregators (`_log_edaphobase_*`): if a helper would
   emit a warning log for count &gt; 0, also append one structured `BuildWarning` with a stable `kind` (e.g.
   `plain_study_ref`, `duplicate_assay_rows`, `contact_native_roles`, `contact_missing_given_name`). Rationale: matches
   today’s “at most N warnings per investigation” log policy; avoids per-row spam.

4. **Dependency pin** — `fairagro-middleware-shared>=14.3.0` and refresh lock. Fail closed in CI if API missing.

## Risks / Trade-offs

- **Worker return type change** — all call sites / tests of `build_single_arc_task` must unwrap `.arc_json`. Mitigate
  with focused unit/integration updates.
- **Warning volume** — aggregated kinds keep report size bounded; if future kinds need per-row detail, extend later.
- **Order vs harvested** — shared API allows warned + harvested independently; we always harvest first then warn for
  clearer operator reading.

## Migration Plan

1. Land shared bump + code + tests on the issue branch.
2. No runtime config flag; behaviour is additive on the report wire.
3. Archive OpenSpec change after merge.

## Open Questions

- None for MVP; additional warning kinds can follow once operators request them.
