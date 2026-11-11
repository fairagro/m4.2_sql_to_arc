## Why

This product has no in-repo Helm chart, so fleet Feature-PR Helm lint and Helm publish callers cannot be wired.
Deployment IaC already defines a chart in `m4.2_infrastructure` under
`helmcharts/fairagro-advanced-middleware-sql-to-arc`; that tree is the starting point for a **product-owned** chart SoT
in this repository (issue #271). Follow-up Feature-PR lint wiring stays in #272.

## What Changes

- Add a product chart under the canonical fleet root `charts/fairagro-advanced-middleware-sql-to-arc-chart/` (folder
  name = `Chart.yaml` `name`), adapted from the infrastructure chart.
- Rename chart identity to `fairagro-advanced-middleware-sql-to-arc-chart` so it matches this repo’s
  `registry-retry.yml` `chart_name` and the fleet `-chart` naming used by API.
- Document product vs infrastructure ownership (product = lint/package/Feature-PR SoT; infra may keep cluster overlays
  and deliberately diverge).
- Ensure `helm lint` / `helm template` succeed with documented default/CI values (no live cluster, no real TLS secrets
  required for lint).
- Do **not** wire Feature-PR `helm-lint` or Helm release callers in this change (#272).

## Capabilities

### New Capabilities

- `helm-chart`: Product-owned Helm chart layout, identity, lint/template readiness, and ownership vs infrastructure.

### Modified Capabilities

<!-- none -->

## Impact

- New tree: `charts/fairagro-advanced-middleware-sql-to-arc-chart/**` (Chart.yaml, values, templates, .helmignore).
- Docs: short ownership/sync note (e.g. under `charts/…/README.md` and/or product overlay docs).
- Aligns with existing `chart_name` in `.github/workflows/registry-retry.yml`.
- No converter runtime, DB views, or Feature-PR workflow changes in this slice.

## Non-goals

- Feature-PR detect-changes / `reusable-helm-lint` wiring (#272).
- Helm pre-release / final release callers or OCI publish.
- Making `m4.2_infrastructure` stop owning cluster overlays.
- Deprecated roots `helmchart/` or `helm/` (prefer canonical `charts/`).
