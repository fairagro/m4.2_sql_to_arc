# Helm Chart

## Purpose

Define the product-owned Helm chart for deploying sql-to-arc (and its supporting Postgres Operator resources) from this
repository, including chart identity, lint/template readiness, and how product ownership relates to the infrastructure
deployment chart.

## Requirements

### Requirement: Canonical Chart Root And Identity

The product MUST ship a Helm chart under `charts/<chart-name>/` where `<chart-name>` equals `Chart.yaml` `name`. The
chart name MUST be `fairagro-advanced-middleware-sql-to-arc-chart`. Deprecated roots `helmchart/` and `helm/` MUST NOT
be used for this chart.

#### Scenario: Chart identity matches fleet publish name

- **GIVEN** the product chart is present in the repository
- **WHEN** `Chart.yaml` is inspected
- **THEN** `name` is `fairagro-advanced-middleware-sql-to-arc-chart`
- **AND** the chart directory is `charts/fairagro-advanced-middleware-sql-to-arc-chart/`

### Requirement: Derived From Infrastructure Chart

The product chart MUST be based on the infrastructure chart at
`m4.2_infrastructure/helmcharts/fairagro-advanced-middleware-sql-to-arc` (templates and values adapted as needed). The
product chart MUST remain suitable for `helm lint` and `helm template` without a live Kubernetes cluster.

#### Scenario: Lint and template succeed with defaults

- **GIVEN** Helm is available on PATH
- **AND** the product chart tree is checked out
- **WHEN** `helm lint` and `helm template` run against the chart with documented default or CI values
- **THEN** both commands exit successfully
- **AND** no real TLS private key material is required for those commands

### Requirement: Product Is Feature-PR Chart Source Of Truth

For Feature-PR validation and packaging from this repository, the in-repo product chart MUST be the chart source of
truth. The infrastructure repository MUST NOT be treated as the Feature-PR chart SoT for this product. Documentation
MUST state that infrastructure may keep cluster-specific overlays and may deliberately diverge from the product chart.

#### Scenario: Ownership is documented

- **GIVEN** an operator reads the product chart documentation in this repository
- **WHEN** they look for ownership guidance
- **THEN** product vs infrastructure roles are described
- **AND** infrastructure is not claimed as the Feature-PR chart SoT
