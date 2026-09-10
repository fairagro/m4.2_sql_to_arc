# Adopt Devinfra Wave C — Design

## Context

Issue [#95](https://github.com/fairagro/m4.2_sql_to_arc/issues/95); explore
lock-ins (2026-09-10): full MVP in one PR; Bake first then `uses:`; pin
`@main` except CQ → [#72](https://github.com/fairagro/m4.2_middleware_devinfra/pull/72)
SHA until merged; product-local check without licence scan until [#74](https://github.com/fairagro/m4.2_middleware_devinfra/issues/74);
no Helm; golden rule on synced paths.

## Goals / Non-Goals

**Goals:** CI matches fleet Devinfra reusables; Bake product-app layout;
CST/pre-push still green.

**Non-Goals:** Sync automation (#13); Helm; secondary PyInstaller binary;
hand-editing synced trees.

## Decisions

### D1 — Bake then callers

1. Thin last-stage Dockerfile + `docker-bake.hcl` (`sql_to_arc-base` →
   `export-binaries`, `sql_to_arc` last stage with `contexts.export_bins`).
2. Microsoft ODBC apk stays **product-local last stage** (not in synced base).
3. `BUILDER_APK_PACKAGES=unixodbc-dev` for compile-time ODBC headers.
4. Smoke `docker buildx bake sql_to_arc --load` with `versions.env` args.

### D2 — Workflow callers

| Caller | Uses |
| ------ | ---- |
| `feature-pull-request.yml` | CQ @#72 SHA; build @main; check-local |
| `pre-release.yml` / `release.yml` | same + release @main |
| `reusable-check-local.yml` | Temporary copy of Devinfra check **minus** licence-check |

Overlays: `python_package_root: middleware`,
`mypy_path: stubs:middleware/sql_to_arc/src`,
`components: '["sql_to_arc"]'`,
`image_base_name: fairagro-advanced-middleware`.

### D3 — Delete local duplicates

Remove `python-quality.yml`, `docker-build.yml`, `docker-release.yml`,
`pull-request-tests.yml` after callers land. Keep `codeql.yml`, `renovate.yml`.

### D4 — `skip_specs: true`

CI/tooling only.

## Risks

- CQ pin drifts until #72 merges → flip to `@main`.
- Licence workaround must be deleted when #74 lands.
- Bake ARG omission fails builds — always inject from `versions.env`.

## Migration

1. Branch `issue-95-adopt-devinfra-wave-c` from `main` (Wave B present).
2. Bake + workflows + drop duplicates.
3. Local bake smoke; draft PR `Fixes #95`.
