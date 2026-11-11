## Context

See `proposal.md` — Why. Locked explore option **A**: canonical `charts/` root and chart name
`fairagro-advanced-middleware-sql-to-arc-chart` (align with `registry-retry.yml` and API `-chart` naming). Source tree:
infrastructure `helmcharts/fairagro-advanced-middleware-sql-to-arc` (Postgres Operator CR, dump bootstrap init,
converter Job/CronJob, TLS secret, config ConfigMap).

## Goals / Non-Goals

**Goals**

- Import/adapt the infra chart into `charts/fairagro-advanced-middleware-sql-to-arc-chart/`.
- Rename chart identity to the `-chart` suffix; keep deploy semantics unless lint/template requires a small default
  tweak (e.g. empty TLS placeholders already present).
- Document ownership; prove `helm lint` + `helm template` on defaults.

**Non-Goals**

- Wiring `#272` Feature-PR helm-lint / path filters.
- Helm release/pre-release workflows or OCI push.
- Sync automation that mirrors infra→product on every infra change.

## Decisions

1. **Root `charts/` not `helmchart/`/`helm/`** — reasoning: choose current Devinfra canonical root (`docs/ci.md` /
   `docs/quality.md`) over peer legacy folders so future lint discovery and rename PRs are unnecessary for this product.

2. **Chart name `fairagro-advanced-middleware-sql-to-arc-chart`** — reasoning: choose alignment with this repo’s
   `registry-retry.yml` `chart_name` and API’s `…-api-chart` pattern over keeping infra’s shorter name (which would
   force a later publish/caller rename).

3. **Copy templates/values from infra, then rename** — reasoning: choose a one-shot import over inventing a thinner
   chart; preserves Zalando Postgres + converter Job semantics already battle-tested in deployment IaC. Product README
   records that infra overlays may diverge.

4. **No CI values overlay required for MVP if defaults lint** — reasoning: choose bare `helm lint`/`template` first; add
   `values-ci.yaml` only if defaults fail closed on empty TLS or similar. Prefer empty-string TLS placeholders already
   in infra values over baking secrets.

5. **Defer Feature-PR wiring to #272** — reasoning: issue split already exists; this change only establishes the chart
   SoT so lint callers have a path.

## Risks / Trade-offs

- [Infra chart churn after copy] → Mitigate: document manual re-sync / deliberate divergence; no automated mirror in
  MVP.
- [Lint fails on Operator CRDs / unknown APIs] → Mitigate: use `helm lint`/`template` without cluster; avoid
  `--validate` against a live API server in MVP verification.
- [Name rename breaks infra mental model] → Mitigate: README maps old infra path ↔ new product chart name.

## Migration Plan

1. Land chart + docs on the issue branch; verify lint/template locally.
2. Later (#272): point Feature-PR `helm` filter + `reusable-helm-lint` at `charts/…`.
3. Infra keepers continue cluster overlays independently.

## Open Questions

None — option A locked.
