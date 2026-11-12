## Purpose

Ensure SQL-to-ARC RO-Crate outputs can be checked with the same DataHUB-equivalent ARC export gate used in client CI,
using committed fixtures and a locally runnable Docker export step.

## ADDED Requirements

### Requirement: Fixture Gate Via Shared Export Validation

The project MUST provide committed RO-Crate fixtures representing SQL-to-ARC outputs and MUST validate them with a
DataHUB-equivalent ARC export check (ARCtrl scaffold write followed by Docker `arc-export` with the same format set
DataHUB uses). Validation MUST run under the `system_local` test marker so default commit-stage and pre-push runs that
exclude that marker do not require Docker. A dedicated CI path that has Docker MUST execute those tests. Failures MUST
surface a readable cause excerpt for operators.

#### Scenario: Known-good fixture passes in Docker CI

- **GIVEN** a committed known-good RO-Crate fixture produced for SQL-to-ARC
- **AND** Docker is available with the configured `arc-export` image
- **WHEN** the `system_local` fixture gate runs
- **THEN** the export validation reports success

#### Scenario: Known-bad fixture fails with readable cause

- **GIVEN** a committed known-bad RO-Crate fixture
- **AND** Docker is available with the configured `arc-export` image
- **WHEN** the `system_local` fixture gate runs that fixture as a negative case
- **THEN** validation reports failure
- **AND** a non-empty cause excerpt (or equivalent failure log excerpt) is available

#### Scenario: Default pre-push does not require Docker

- **GIVEN** the repository’s default pre-push pytest selection that excludes `system_local`
- **WHEN** a developer pushes without Docker
- **THEN** the ARC export fixture gate is not required to run for that push to succeed

### Requirement: Document Local Validation

The project MUST document how developers install prerequisites, run the `system_local` export fixture gate locally, pin
or override the `arc-export` image, and add a new fixture after a production or DataHUB export failure.

#### Scenario: Operator follows the doc

- **GIVEN** the project documentation for the ARC export fixture gate
- **WHEN** an operator wants to reproduce the CI check locally
- **THEN** the documentation describes the Docker requirement, the pytest marker invocation, and image override
