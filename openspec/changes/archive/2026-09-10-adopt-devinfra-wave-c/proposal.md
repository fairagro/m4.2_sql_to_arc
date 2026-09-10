# Adopt Devinfra Wave C — Proposal

## Why

Issue [#95](https://github.com/fairagro/m4.2_sql_to_arc/issues/95): adopt shared
Devinfra **Wave C** (reusable CI + Bake product-app layout) after Wave B
([#100](https://github.com/fairagro/m4.2_sql_to_arc/pull/100)). Harvester pilot
lock-ins ([#169](https://github.com/fairagro/m4.2_middleware_harvester/issues/169)
/ [#181](https://github.com/fairagro/m4.2_middleware_harvester/pull/181)) apply.

**Golden rule:** never hand-edit synced Devinfra trees — make Devinfra generic
first, else `.global`/product-local split, else documented exception.

## What Changes

- Finish Bake product-app: synced `docker/Dockerfile.product-app.base` verbatim;
  thin product-local `docker/Dockerfile.sql_to_arc` last stage; root
  `docker-bake.hcl` with `sql_to_arc-base` + `sql_to_arc`.
- Switch callers to Devinfra `reusable-code-quality` / `reusable-build` /
  `reusable-release` @`main` (code-quality temporarily pinned to
  [#72](https://github.com/fairagro/m4.2_middleware_devinfra/pull/72) SHA for
  `mypy_path` / `pylint_source_roots` overlays).
- Product-local `reusable-check-local.yml` **without** Trivy licence job until
  Devinfra [#74](https://github.com/fairagro/m4.2_middleware_devinfra/issues/74)
  (caller fork, not a synced-tree edit).
- Rename fleet callers: `feature-pull-request.yml`, `pre-release.yml`,
  `release.yml`; drop duplicated local `python-quality.yml`,
  `docker-build.yml`, `docker-release.yml`, `pull-request-tests.yml`.
- No Helm in this repo — skip Helm slice. No secondary binary — skip #71.
- Sync automation (#13): document; continue manual adopt until ready.

### Non-goals

- Editing synced allowlist files locally.
- Waiting for #13 sync automation or #40 markdown-in-reusable-CQ.
- Patching synced `mypy.ini` / `.pylintrc` for product paths.

## Capabilities

### New Capabilities

- _none — `skip_specs: true`._ Tooling/CI adoption only.

### Modified Capabilities

- _none._

## Impact

- **CI:** Devinfra reusables + temporary local check (no licence scan).
- **Images:** Bake-only builds (BREAKING vs monolith `docker build`).
- **Fleet:** same lock-ins as harvester Wave C pilot.
