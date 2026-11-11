# fairagro-advanced-middleware-sql-to-arc-chart

Product-owned Helm chart for deploying sql-to-arc (Edaphobase SQL → ARC → Middleware API) with a Zalando Postgres
Operator CR and converter Job/CronJob.

## Ownership

| Role                         | Repository / path                                                        | Responsibility                                                                   |
| ---------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| **Product (Feature-PR SoT)** | this chart under `charts/fairagro-advanced-middleware-sql-to-arc-chart/` | Lint, package, and Feature-PR chart source of truth for this product             |
| **Infrastructure**           | `m4.2_infrastructure/helmcharts/fairagro-advanced-middleware-sql-to-arc` | Cluster overlays, Argo/SOPS values, and deployment IaC; may deliberately diverge |

Infrastructure is **not** the Feature-PR chart source of truth. This in-repo chart was adapted from the infrastructure
chart and may drift; re-sync is manual when product and infra choose to align.

## Chart identity

- Directory and `Chart.yaml` `name`: `fairagro-advanced-middleware-sql-to-arc-chart`
- Aligns with `.github/workflows/registry-retry.yml` `chart_name` and fleet `-chart` naming

## Defaults for lint / template

- `tls.enabled` defaults to `false` so `helm lint` / `helm template` need no real client PEMs.
- Enable TLS in cluster overlays and set `tls.clientCert` / `tls.clientKey` (typically via SOPS).
- Converter Job/CronJob are disabled by default; enable in overlay values when scheduling runs.

## Verify locally

```bash
helm lint charts/fairagro-advanced-middleware-sql-to-arc-chart
helm template test charts/fairagro-advanced-middleware-sql-to-arc-chart
```

Feature-PR `helm-lint` wiring is tracked separately (issue #272).
