# SQL-to-ARC Conversion Pipeline

## Purpose

Orchestrate the end-to-end batch run: validate the database, process all
investigations, build ARCs, upload them, and report results. This domain
covers only the glue between the other features.

## Requirements

### Requirement: Pre-Loop Schema Validation

The pipeline MUST validate that all required database views and columns
exist before starting the main loop (see `database-access`).

#### Scenario: Schema mismatch at startup

- GIVEN a required view or column is missing
- WHEN the converter starts
- THEN validation fails fast with a clear diagnostic
- AND the main processing loop does not start

### Requirement: Stream And Bulk-Fetch

The pipeline MUST stream investigations one at a time (batched) and fetch
related entities in bulk per batch (see `database-access`).

#### Scenario: Processing a batch

- GIVEN `db_batch_size` investigations are loaded
- WHEN related entities are needed
- THEN they are fetched with one bulk query per entity type for that batch

### Requirement: Isolated Worker Build

For each investigation, the pipeline MUST build the ARC in an isolated
worker process (see `arc-building`).

#### Scenario: Per-investigation build

- GIVEN an `ArcBuildData` bundle for one investigation
- WHEN the build runs
- THEN it executes in a worker process
- AND returns a JSON-LD string to the main process

### Requirement: Upload Built ARCs

The pipeline MUST upload successfully built ARCs to the Middleware API
through the harvest-session upload path defined in `api-upload` (one harvest
per RDI run via `harvest_arcs`, not per-investigation `create_or_update_arc`).

#### Scenario: Successful builds enter one harvest

- **GIVEN** one or more workers returned non-empty ARC JSON strings
- **WHEN** the upload phase runs
- **THEN** those ARCs are submitted within a single harvest session for the configured RDI
- **AND** `create_or_update_arc` is not used

### Requirement: Provenance Report

The pipeline MUST record success and failure per investigation by ID and
print a JSON provenance report to stdout when the run completes.

#### Scenario: Run completes with mixed results

- GIVEN some investigations succeeded and some failed
- WHEN the run finishes
- THEN a JSON report listing success/failure by ID is printed to stdout

### Requirement: Exit Codes

The pipeline MUST exit with code 0 if processing succeeded (even with
partial failures). It MUST exit non-zero on fatal errors (schema mismatch,
DB unreachable, etc.).

#### Scenario: Partial failures only

- GIVEN the run completed and some investigations failed
- WHEN the process exits
- THEN the exit code is 0

#### Scenario: Fatal database error

- GIVEN the database is unreachable at startup
- WHEN the converter cannot proceed
- THEN the exit code is non-zero

### Requirement: Worker Timeout Continues Loop

If a worker process times out (default 30 min), the investigation MUST be
counted as failed and the loop MUST continue.

#### Scenario: Worker exceeds timeout

- GIVEN a build exceeds the configured timeout
- WHEN the timeout fires
- THEN that investigation is marked failed
- AND subsequent investigations continue

### Requirement: Debug Limit Cap

The pipeline MUST respect `debug_limit` config to cap the number of
investigations processed (for testing).

#### Scenario: debug_limit set to 5

- GIVEN `debug_limit` is 5
- WHEN more than 5 investigations are available
- THEN only 5 are processed

### Requirement: CLI Version And Config Flags

The CLI MUST support `--version` and `--config` to specify the config file.

#### Scenario: Version flag

- GIVEN the operator passes `--version`
- WHEN the CLI runs
- THEN the version is printed and processing does not start
