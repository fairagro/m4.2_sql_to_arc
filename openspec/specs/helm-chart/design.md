# Helm Chart — Design

## Key Decisions

1. **Root `charts/` not `helmchart/`/`helm/`** — Current Devinfra canonical root (`docs/ci.md` / `docs/quality.md`) so
   future lint discovery and rename PRs are unnecessary for this product.

2. **Chart name `fairagro-advanced-middleware-sql-to-arc-chart`** — Aligns with this repo’s `registry-retry.yml`
   `chart_name` and the fleet `-chart` naming used by API.

3. **Copy templates/values from infrastructure, then rename** — One-shot import from
   `m4.2_infrastructure/helmcharts/fairagro-advanced-middleware-sql-to-arc` preserves Zalando Postgres + converter
   Job/CronJob semantics. Product README records that infra overlays may deliberately diverge; no automated mirror.

4. **Defaults lint without real TLS** — `tls.enabled` defaults to `false` so `helm lint` / `helm template` need no
   client PEMs; cluster overlays enable TLS with SOPS values.

5. **Feature-PR helm-lint wiring deferred** — Chart SoT lands first; Feature-PR detect-changes / `reusable-helm-lint`
   wiring is issue #272.
