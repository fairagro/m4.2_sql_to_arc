## 1. Import chart

- [x] 1.1 Copy infrastructure chart files into `charts/fairagro-advanced-middleware-sql-to-arc-chart/` and set
      `Chart.yaml` `name` (and directory) to `fairagro-advanced-middleware-sql-to-arc-chart`; verify
      `test -f charts/fairagro-advanced-middleware-sql-to-arc-chart/Chart.yaml`
- [x] 1.2 Adapt any hard-coded chart name references in templates/helpers if present; verify
      `rg -n 'fairagro-advanced-middleware-sql-to-arc[^-]' charts/fairagro-advanced-middleware-sql-to-arc-chart/Chart.yaml`
      shows the `-chart` name only as intended

## 2. Docs

- [x] 2.1 Add chart README (or short product doc section) describing product vs infrastructure ownership and that
      Feature-PR SoT is the in-repo chart; verify the doc mentions both roles and does not claim infra as Feature-PR SoT

## 3. Verify Helm

- [x] 3.1 Run `helm lint charts/fairagro-advanced-middleware-sql-to-arc-chart` and
      `helm template test charts/fairagro-advanced-middleware-sql-to-arc-chart` and verify both exit 0
- [x] 3.2 Confirm no real TLS private key is required for those commands (empty placeholders / disabled paths only)

## 4. OpenSpec quality

- [x] 4.1 Run `openspec validate add-product-helm-chart` and verify it passes
