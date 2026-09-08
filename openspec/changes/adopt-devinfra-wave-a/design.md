# Adopt Devinfra Wave A — Design

## Context

Issue [#93](https://github.com/fairagro/m4.2_sql_to_arc/issues/93); explore
decisions on that issue (and pilot [#366](https://github.com/fairagro/m4.2_advanced_middleware_api/issues/366)).
This repo is almost empty of Wave A surfaces (no `scripts/ai`, no fixer
skills, no `principles.global.md`). It already has OpenSpec `opsx-*`, a
product `config-wrapper` skill, domain `openspec/specs/principles/`, and a
**local** `.agents/skills/arctrl/` (~318 lines) that predates Devinfra #35
(~471 lines at pin `906870bd…`).

Pilot pattern: middleware_api change `adopt-devinfra-wave-a` / draft PR
[#374](https://github.com/fairagro/m4.2_advanced_middleware_api/pull/374).
Reuse decisions; adapt overlays only.

## Goals / Non-Goals

**Goals:**

- Synced Wave A paths match Devinfra at one pinned SHA.
- Agents can run fixer/creator skills via `m42-ai` + `scripts/bin/gh`.
- Surface-bar rules in synced policy; default map in `.global.md`; product
  path rows only in local `docs/surface-quality-bar.md`.
- Shared foundation in `principles.global.md`; product contract in local
  `openspec/principles.md` (P3) without weakening Type Safety / Supported
  environment semantics from `.global`.
- Same SHA as the merged pilot (F1).

**Non-Goals:**

- Wave B/C; inventing domain spec deltas for tooling; waiting on #13;
  keeping a Finder/surface section in principles (superseded by #32).

## Decisions

### D1: Verbatim sync from pinned Devinfra SHA

Copy allowlisted paths from Devinfra at one SHA recorded in the adopt PR.
Do not hand-edit synced files after copy.

**Reason:** Fleet SoT; avoids drift vs API/harvester.  
**Alternatives:** Wait for #13; cherry-pick with local edits (rejected).

**Pin policy:** Start from provisional `906870bd18fa7fef3c5593f75440291e04ceb43e`
(pilot). Before merge here, re-read the **merged** pilot PR and use that
SHA if it changed.

### D2: A + thin Auth-B in one PR

Include `scripts/bin/gh`, `scripts/dev-tokens.sh`,
`scripts/set-dev-tokens.sh`; exclude `scripts/bin/git` and the rest of
Wave B.

**Reason:** Skills document these wrappers; thin slice stays reviewable.  
**Alternatives:** A-only (auth mismatch); full Wave B (too large).

### D3: `m42-ai` via `--project scripts/ai`

Do not add `scripts/ai` to the product root uv workspace.

**Reason:** Matches Devinfra docs and pilot D3; root already workspaces
`middleware/*` from the API git source.  
**Alternatives:** Workspace member now (optional later).

### D4: P3 local principles overlay

Add `openspec/principles.global.md` verbatim. Create
`openspec/principles.md` that extends `.global` and carries
**product-only** material drawn from today’s agent/project contract
(tech stack, module map, converter constraints: views-only SQL,
ConfigWrapper / `SQL_TO_ARC`, ProcessPool IPC via JSON, quality tool
expectations). Do **not** put Finder/surface path examples here.

Domain OpenSpec requirements remain in `openspec/specs/principles/spec.md`
(behavioral RFC 2119). Root `principles.md` is the agent-facing overlay,
not a replacement for that domain spec in this change.

**Reason:** Agents load shared rules from `.global` while keeping
converter-specific guidance.  
**Alternatives:** Delete domain principles spec (out of scope); fat local
file that duplicates `.global` (rejected).

### D5: Surface-bar overlay for sql_to_arc paths

Sync `docs/surface-quality-bar.global.md`. Create local
`docs/surface-quality-bar.md` with typical entries such as:

- `middleware/sql_to_arc/src/middleware/sql_to_arc/{processor,pipeline,builder,mapper,database,models,config}.py`
- `docs/sql_to_arc_database_views.md`
- `dev_environment/{compose,config}.{demo,dev}.yaml`, `demo_api_main.py`
- `openspec/specs/{sql-to-arc-conversion,arc-building,database-access,api-upload}/`

Do **not** copy API pilot rows (`/v3/…`, Celery, CouchDB) unless they
truly apply.

**Reason:** #32 landed; product Finder context without forking `.global`.  
**Alternatives:** Former O1-in-principles (superseded).

### D6: Replace local `arctrl`; keep `config-wrapper`

Overwrite `.agents/skills/arctrl/` with Devinfra’s first-party skill.
Keep `.agents/skills/config-wrapper/` (product-local, not Wave A vendor).

No `scan-secrets` tree exists here — nothing to delete; still align
AGENTS/excludes to vendor set `{gh,docker,hadolint,uv}`.

**Reason:** #35 / #93 allowlist; avoid arctrl drift.  
**Explore note (B):** Local skill is shorter and **outdated on arctrl 3.2+**
(e.g. `CompositeHeader.performer()` vs property; `start_as_task` import
path). Devinfra adds WriteContracts / `AddFile` / supplementary-file
sections that matter less for harvest JSON upload but are correct SoT.
Converter-relevant pitfalls (`gc.collect` in workers, no pickling ARC
objects, `technology_platform=None`) remain in the shared skill — no
need to preserve a local fork for those. Diff before overwrite; if any
truly unique tip remains, move to `AGENTS.md` (prefer shared skill).

### D7: `skip_specs: true`

No delta under `openspec/changes/.../specs/`.

**Reason:** Tooling/docs adoption; domain behaviour unchanged.  
**Alternatives:** Import Devinfra capability specs (out of scope).

## Risks / Trade-offs

- **[Risk] Pilot SHA moves before merge** → Re-pin from merged #374;
  document SHA in PR body.
- **[Risk] Auth-B token store format** → One-time
  `source ./scripts/set-dev-tokens.sh` if needed.
- **[Risk] arctrl overwrite** → Pre-overwrite diff (done in explore);
  verify converter still matches 3.2+ guidance after sync (separate from
  this adopt if code needs fixes).
- **[Risk] P3 vs domain `openspec/specs/principles/` confusion** →
  AGENTS.md clarifies: domain spec = requirements; root
  `principles.md` / `.global` = agent entry.
- **[Risk] Later #13 sync** → Do not hand-edit synced paths after merge.

## Migration Plan

1. Confirm pin SHA vs merged pilot; copy Wave A + thin Auth-B + arctrl.
2. Write P3 `openspec/principles.md` + sql_to_arc
   `docs/surface-quality-bar.md`; update `AGENTS.md`.
3. `uv run --project scripts/ai m42-ai --help` / `auth-status`;
   `uv run --project scripts/ai pytest`.
4. Smoke `/review-fixer` on one PR; brief create/issue-fixer.
5. Diff synced paths vs pin; merge.

Rollback: revert the adopt PR.
