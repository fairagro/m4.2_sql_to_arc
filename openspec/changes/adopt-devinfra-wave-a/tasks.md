# Adopt Devinfra Wave A — Tasks

## 1. Pin and sync Wave A paths

- [ ] 1.1 Confirm Devinfra SHA against **merged** middleware_api pilot
      (provisional: `906870bd18fa7fef3c5593f75440291e04ceb43e`); document
      final pin in adopt PR description
- [ ] 1.2 Copy verbatim: `docs/ai_review_policy.md`,
      `docs/surface-quality-bar.global.md`,
      `docs/{review,create,issue}-fixer.md`
- [ ] 1.3 Copy verbatim: `.cursor/BUGBOT.md`,
      `.cursor/commands/{review,create,issue}-fixer.md`
- [ ] 1.4 Copy verbatim: `.github/copilot-instructions.md`,
      `.github/prompts/{review,create,issue}-fixer.prompt.md`
- [ ] 1.5 Copy verbatim: `.agents/skills/{review-fixer,create-issue,issue-fixer}/`
- [ ] 1.6 Replace `.agents/skills/arctrl/` with Devinfra first-party skill
      (diff already reviewed in explore; keep `config-wrapper/`)
- [ ] 1.7 Install/copy vendor skills `.agents/skills/{gh,docker,hadolint,uv}/`
- [ ] 1.8 Copy verbatim: `scripts/ai/` (incl. tests/lock) and
      `openspec/principles.global.md`

## 2. Thin Auth-B

- [ ] 2.1 Copy verbatim: `scripts/bin/gh`, `scripts/dev-tokens.sh`,
      `scripts/set-dev-tokens.sh`
- [ ] 2.2 Confirm `scripts/bin/git` and other Wave B paths are untouched

## 3. Local overlay (P3 + surface-bar) and cleanup

- [ ] 3.1 Create `openspec/principles.md` as P3 product overlay (extends
      `.global`; converter stack/modules/constraints; no Finder/surface
      section; leave `openspec/specs/principles/` domain spec in place)
- [ ] 3.2 Create `docs/surface-quality-bar.md` with sql_to_arc path rows
      (converter modules, view contract doc, `dev_environment/`, relevant
      OpenSpec domains) — not API `/v3`/Celery/CouchDB rows
- [ ] 3.3 Update `AGENTS.md` pointers (`.global` + local principles;
      surface-bar global + local; vendor set; shared `arctrl`;
      `config-wrapper`; `m42-ai` / `scripts/ai`; clarify domain
      principles spec vs root overlay)
- [ ] 3.4 Extend minimal lint excludes only if needed for new vendor
      skill trees (no quality-skeleton rewrite; `arctrl` is first-party)

## 4. Verify and smoke

- [ ] 4.1 `uv run --project scripts/ai m42-ai --help` and
      `uv run --project scripts/ai m42-ai auth-status`
- [ ] 4.2 `uv run --project scripts/ai pytest`
- [ ] 4.3 Smoke `/review-fixer` on one real PR; briefly
      `/create-issue` / `/issue-fixer`
- [ ] 4.4 Diff synced paths against pinned SHA (overlays excepted)
