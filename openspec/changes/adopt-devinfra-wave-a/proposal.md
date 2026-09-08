# Adopt Devinfra Wave A — Proposal

## Why

Shared Devinfra Wave A (AI review / agent stack) is extracted and closed
upstream ([fairagro/m4.2_middleware_devinfra](https://github.com/fairagro/m4.2_middleware_devinfra)
#4–#6, #14–#16, [#32](https://github.com/fairagro/m4.2_middleware_devinfra/issues/32),
[#35](https://github.com/fairagro/m4.2_middleware_devinfra/issues/35)). This repo
still lacks the shared stack (`scripts/ai` / `m42-ai`, review/issue fixer
skills, `principles.global.md`, surface-bar `.global.md`, vendor skills) and
carries a **local** `.agents/skills/arctrl/` that has drifted from the
canonical skill. Issue [#93](https://github.com/fairagro/m4.2_sql_to_arc/issues/93)
asks to adopt the same stack as the fleet follower after the middleware_api
pilot ([#366](https://github.com/fairagro/m4.2_advanced_middleware_api/issues/366)
/ draft PR [#374](https://github.com/fairagro/m4.2_advanced_middleware_api/pull/374)).

**Provisional pin (same as pilot):** `906870bd18fa7fef3c5593f75440291e04ceb43e`.
Re-confirm against the **merged** pilot PR before opening the adopt PR here
(F1: same Devinfra SHA).

## What Changes

- Sync Wave A paths verbatim from the pinned Devinfra SHA: policy,
  `docs/surface-quality-bar.global.md`, Bugbot/Copilot entries,
  `/review-fixer` + `/create-issue` + `/issue-fixer`
  skills/commands/prompts, thin fixer docs, vendor skills
  `{gh,docker,hadolint,uv}`, `scripts/ai/` / `m42-ai`,
  `openspec/principles.global.md`, first-party `.agents/skills/arctrl/`.
- **Thin Auth-B** in the same change: `scripts/bin/gh`,
  `scripts/dev-tokens.sh`, `scripts/set-dev-tokens.sh`.
- **P3:** add `.global` verbatim; create local `openspec/principles.md` as a
  product overlay (converter stack / module rules / scaling). Domain specs
  under `openspec/specs/principles/` stay the behavioral contract — do not
  delete them for this change.
- Add local `docs/surface-quality-bar.md` with **sql_to_arc** path rows (not
  API `/v3`/Celery/CouchDB examples).
- Replace local `arctrl` skill with Devinfra’s; keep product-only
  `.agents/skills/config-wrapper/`.
- Thin `AGENTS.md` pointers; minimal lint-exclude updates if needed.
- Smoke `/review-fixer` (and briefly create/issue-fixer) once auth helpers
  land.

### Non-goals

- Full Wave B (git wrapper, quality/Dev Container skeleton) or Wave C (CI
  `uses:`).
- Root uv workspace membership for `m42-ai` (use
  `uv run --project scripts/ai …`).
- Forking product examples into synced policy / `.global.md`.
- Changing converter runtime behaviour or domain OpenSpec requirements
  (`sql-to-arc-conversion`, `arc-building`, …).
- Blocking on Devinfra sync automation (#13).

## Capabilities

### New Capabilities

- _none — `skip_specs: true`._ Shared agent/tooling behaviour is owned by
  Devinfra; this change does not alter product domain requirements under
  `openspec/specs/`.

### Modified Capabilities

- _none._

## Impact

- **Synced:** `docs/` (policy, surface-bar `.global`, fixer docs),
  `.cursor/`, `.github/` (copilot + fixer prompts), `.agents/skills/`
  (fixer + vendor + `arctrl`), `scripts/ai/`,
  `openspec/principles.global.md`, thin Auth-B scripts.
- **Local:** `openspec/principles.md`, `docs/surface-quality-bar.md`,
  `AGENTS.md`; keep `config-wrapper` skill.
- **Unchanged:** `middleware/**`, domain specs/designs, OpenSpec `opsx-*`
  commands/skills already present.
- **Fleet:** decision matrix on #93 mirrors #366; pin SHA from pilot.
