# Adopt Devinfra Wave A — Tasks

## 1. Pin and sync Wave A paths

- [x] 1.1 Confirm Devinfra SHA against **merged** middleware_api pilot
      (provisional: `906870bd18fa7fef3c5593f75440291e04ceb43e`); document
      final pin in adopt PR description
      — Pilot [#374](https://github.com/fairagro/m4.2_advanced_middleware_api/pull/374)
      still **OPEN**; using same provisional pin. Re-confirm before merge if
      pilot retargets.
- [x] 1.2 Copy verbatim: `docs/ai_review_policy.md`,
      `docs/surface-quality-bar.global.md`,
      `docs/{review,issue}-fixer.md`, `docs/create-issue.md`
- [x] 1.3 Copy verbatim: `.cursor/BUGBOT.md`,
      `.cursor/commands/{review,issue}-fixer.md`,
      `.cursor/commands/create-issue.md`
- [x] 1.4 Copy verbatim: `.github/copilot-instructions.md`,
      `.github/prompts/{review,issue}-fixer.prompt.md`,
      `.github/prompts/create-issue.prompt.md`
- [x] 1.5 Copy verbatim: `.agents/skills/{review-fixer,create-issue,issue-fixer}/`
- [x] 1.6 Replace `.agents/skills/arctrl/` with Devinfra first-party skill
      (diff already reviewed in explore; keep `config-wrapper/`)
- [x] 1.7 Install/copy vendor skills `.agents/skills/{gh,docker,hadolint,uv}/`
- [x] 1.8 Copy verbatim: `scripts/ai/` (incl. tests/lock) and
      `openspec/principles.global.md`

## 2. Thin Auth-B

- [x] 2.1 Copy verbatim: `scripts/bin/gh`, `scripts/dev-tokens.sh`,
      `scripts/set-dev-tokens.sh`
- [x] 2.2 Confirm `scripts/bin/git` and other Wave B paths are untouched

## 3. Local overlay (P3 + surface-bar) and cleanup

- [x] 3.1 Create `openspec/principles.md` as P3 product overlay (extends
      `.global`; converter stack/modules/constraints; no Finder/surface
      section; leave `openspec/specs/principles/` domain spec in place)
- [x] 3.2 Create `docs/surface-quality-bar.md` with sql_to_arc path rows
      (converter modules, view contract doc, `dev_environment/`, relevant
      OpenSpec domains) — not API `/v3`/Celery/CouchDB rows
- [x] 3.3 Update `AGENTS.md` pointers (`.global` + local principles;
      surface-bar global + local; vendor set; shared `arctrl`;
      `config-wrapper`; `m42-ai` / `scripts/ai`; clarify domain
      principles spec vs root overlay)
- [x] 3.4 Extend minimal lint excludes only if needed for new vendor
      skill trees (no quality-skeleton rewrite; `arctrl` is first-party)

## 4. Verify and smoke

- [x] 4.1 `uv run --project scripts/ai m42-ai --help` and
      `uv run --project scripts/ai m42-ai auth-status`
- [x] 4.2 `uv run --project scripts/ai pytest` →
      `PYTHONPATH=scripts/ai/src uv run pytest scripts/ai/tests --override-ini='addopts='`
      (27 passed; root coverage gate does not apply to this package)
- [x] 4.3 Smoke plumbing: `m42-ai review-open --pr 92` (ok). Full interactive
      `/review-fixer` + brief create/issue-fixer on the **adopt PR** after push
      (same as pilot deferral pattern).
- [x] 4.4 Diff synced paths against pinned SHA (overlays excepted) —
      match; only local `scripts/ai/.venv`, `uv.lock`, `__pycache__` (ignored)
