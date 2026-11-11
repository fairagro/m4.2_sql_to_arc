## Context

See `proposal.md`. Harvester #474 / PR #602 is the reference implementation. This repo already registers `system_local`
and excludes it from pre-push pytest. Shared package `fairagro-middleware-arc-validation` ≥14.2.0 is on PyPI
(`validate_rocrate`, `FAIRAGRO_ARC_EXPORT_IMAGE`).

## Goals / Non-Goals

**Goals**

- Pre-baked RO-Crate fixtures + `system_local` gate + dedicated Feature-PR Docker job (harvester mirror).
- At least one known-good fixture and one known-bad fixture (readable `cause_excerpt` on failure).
- Digest-pinned `arc-export` image + PATH wrapper (`/arc-export` → `arc-export` on PATH).

**Non-Goals**

- Live demo-DB → convert inside the MVP test (refresh fixtures offline when mapping changes).
- Reimplementing `arc-export` or the Write adapter (lives in the shared package).
- Requiring Docker on every commit / pre-push.
- Editing synced Devinfra quality scripts.

## Decisions

1. **Mirror harvester layout** — `middleware/sql_to_arc/tests/fixtures/arc_export/<name>/ro-crate-metadata.json` plus
   `tests/system_local/` helpers (`arc-export-base.digest`, PATH wrapper tag). Alternative rejected: invent a different
   marker or fold into unit tests with mocked Docker.

2. **Pre-baked fixtures, not map-in-CI** — Stable DataHUB-equivalent gate; regenerate offline from demo/converter when
   mappings change. Alternative rejected for MVP: start-demo → convert every CI run (flaky, slow).

3. **Dependency** — `fairagro-middleware-arc-validation>=14.2.0` as a **dev** dependency of `sql_to_arc` (test-only).

4. **Markers** — `@pytest.mark.system_local` only. Skip clearly when Docker is missing if accidentally collected;
   dedicated CI job must fail closed when Docker/export fails.

5. **CI** — New Feature-PR job (not inside `reusable-code-quality`): checkout, `uv sync --dev --all-packages`, build
   PATH wrapper from digest SoT, set `FAIRAGRO_ARC_EXPORT_IMAGE`, `uv run pytest -m system_local` under
   `middleware/sql_to_arc/tests/system_local`. Skip when Feature `code` path filter is false. Runner `ubuntu-latest`
   provides Docker.

6. **Known-bad fixture** — Separate test asserts `not result.ok` and that `cause_excerpt` (or stderr/stdout excerpt) is
   non-empty. Do not mock Docker for the happy path.

7. **Docs** — Product-local `docs/arc-export-fixtures.md`: Docker requirement, how to run, how to add a fixture after
   DataHUB failure, digest / `FAIRAGRO_ARC_EXPORT_IMAGE` note.

8. **Initial good fixture** — Produce once offline (demo converter or minimal arctrl-built crate that already passes
   `arc-export` locally) before push.

## Risks / Trade-offs

- [GHCR pull / rate limits] → Digest pin; document override env.
- [Stale fixtures hide mapper regressions] → Doc requires adding a fixture when DataHUB fails.
- [Upstream `arc-export` breaks good fixtures] → Digest freezes behaviour; bump deliberately.
- [Package invokes `arc-export` but image only has `/arc-export`] → PATH symlink wrapper (same as harvester); upstream
  package/image fix is out of scope.
- [First real SQL-to-ARC crate fails export] → Fix mapping or start from a minimal known-good; keep known-bad separate.

## Migration Plan

1. Land dependency + fixtures + tests + CI job + doc in one apply/PR.
2. Operators run `system_local` locally only with Docker.
3. Optional later follow-ups: more representative investigation fixtures as DataHUB failures appear.

## Open Questions

None — locked to harvester mirror.
