## MODIFIED Requirements

### Requirement: Provenance Report

The pipeline MUST record success and failure per investigation via the shared
harvest-run report counting API (see `harvest-report`) and print the shared
JSON-LD harvest report to stdout when the run completes. It MUST NOT emit the
legacy sql_to_arc-only PROV/`void` JSON-LD shape.

#### Scenario: Run completes with mixed results

- **GIVEN** some investigations succeeded and some failed
- **WHEN** the run finishes
- **THEN** a shared-format JSON-LD harvest report is printed to stdout
- **AND** the repository entry reflects harvested and failed dataset counts
  with failed-record detail for failures

### Requirement: Worker Timeout Continues Loop

If a worker process times out (default 30 min), the investigation MUST be
recorded as failed on the shared repository scope (with a timeout message and
investigation id) and the loop MUST continue.

#### Scenario: Worker exceeds timeout

- **GIVEN** a build exceeds the configured timeout
- **WHEN** the timeout fires
- **THEN** that investigation is recorded as failed on the harvest report scope
- **AND** subsequent investigations continue
