# Principles

## Purpose

Foundation contract and project values for the FAIRagro SQL-to-ARC converter.
All other domain specs assume these constraints. The authoritative schema
contract is `docs/sql_to_arc_database_views.md` — feature specs MUST NOT
restate view definitions; they reference that document when citing columns.

## Requirements

### Requirement: View Contract Is Authoritative

The converter MUST treat `docs/sql_to_arc_database_views.md` as the sole
column-level schema contract and MUST query only the views defined there,
never raw tables.

#### Scenario: Feature cites a column

- GIVEN a feature that needs a database column or constraint
- WHEN the requirement is written or implemented
- THEN it references `docs/sql_to_arc_database_views.md` instead of restating
  the view definition

### Requirement: Correctness Over Speed

The system MUST prefer valid ARC output over throughput. If a dataset cannot
be mapped cleanly, the investigation MUST fail with a clear error rather than
produce silent garbage.

#### Scenario: Unmappable investigation

- GIVEN an investigation whose data cannot be mapped cleanly
- WHEN the converter processes it
- THEN the investigation is marked failed with a clear error
- AND no invalid ARC is uploaded for that investigation

### Requirement: Memory-Safe By Design

The system MUST keep peak RAM bounded and predictable for tens of thousands
of investigations on hosts with limited memory.

#### Scenario: Large dataset run

- GIVEN a database with tens of thousands of investigations
- WHEN the converter runs to completion
- THEN investigations are streamed and processed without loading the full
  dataset into memory at once

### Requirement: Failure Isolation

One failing investigation MUST NOT abort the entire run. Stats and error IDs
MUST be collected and reported at the end.

#### Scenario: Single investigation fails

- GIVEN a batch containing one bad investigation among many valid ones
- WHEN the converter processes the batch
- THEN the bad investigation is recorded as failed
- AND remaining investigations continue to be processed
- AND the final report includes the failed ID

### Requirement: Stateless Batch Process

The converter MUST store no state between runs (no cache, no lock files, no
database writes). The only persistent output is what the Middleware API
receives.

#### Scenario: Second consecutive run

- GIVEN a completed converter run
- WHEN a second run starts
- THEN it does not depend on local state from the first run

### Requirement: Security By Default

Inputs from external sources (database, API, config) MUST be treated as
untrusted. The system MUST validate before use, fail closed, and apply least
privilege (OWASP best practices).

#### Scenario: Untrusted input arrives

- GIVEN data from the database, API, or configuration
- WHEN it is consumed
- THEN it is validated before use
- AND invalid or unsafe values fail closed

### Requirement: Typed Python And Uv

All public APIs MUST be fully typed for Python 3.12. Dependency management
MUST use `uv`; production code MUST NOT call `pip` directly.

#### Scenario: Adding a dependency

- GIVEN a new Python dependency is required
- WHEN it is added to the project
- THEN it is declared via `uv` / the workspace lockfile
- AND no direct `pip install` is used in production paths

### Requirement: No Direct Environment Access

Code MUST NOT read `os.environ` directly. Configuration MUST go through
`Config` / `ConfigWrapper`.

#### Scenario: Reading a runtime setting

- GIVEN application code needs a setting
- WHEN the value is obtained
- THEN it comes from the injected `Config` object
- AND `os.environ` is not accessed in application modules

### Requirement: SQL Confined To Database Module

All SQL MUST live inside the `Database` class. Other modules MUST NOT query
the database directly.

#### Scenario: Fetching related entities

- GIVEN the pipeline needs studies for a batch of investigations
- WHEN the data is loaded
- THEN the query is issued only from the `Database` class

### Requirement: JSON-Only Worker IPC

Worker processes MUST communicate via JSON strings only (no shared objects,
no pickling of domain objects across the IPC boundary).

#### Scenario: ARC build completes in a worker

- GIVEN an investigation is built in a worker process
- WHEN the result is returned to the main process
- THEN the payload is a JSON string
- AND no ARC/.NET object is pickled across the boundary

### Requirement: Quality Gates And Tests

Ruff (lint + format), mypy, pylint, bandit, and pytest MUST pass before
merge. Every new feature MUST include matching tests. `# noqa` /
`# type: ignore` suppressions MUST be used only when technically unavoidable.

#### Scenario: New feature lands

- GIVEN a new feature is implemented
- WHEN it is proposed for merge
- THEN matching tests exist
- AND configured quality tools pass without unjustified suppressions

### Requirement: Validation In Pydantic Models

Validation MUST belong in the Pydantic model where possible (`Literal` types
or `@field_validator`). A `ValidationError` triggers the standard
skip-with-warning path in `database.py`. Custom warning code outside Pydantic
MAY be used only when a spec violation should log a warning but NOT skip the
row (rescue scenario).

#### Scenario: Invalid row from a view

- GIVEN a database row that fails Pydantic validation
- WHEN it is parsed
- THEN a `ValidationError` causes the standard skip-with-warning path
- AND the row is not silently accepted

### Requirement: Acyclic Module Dependencies

The module dependency graph MUST be:
`main → processor → builder → mapper`, with `processor` also depending on
`database` and `api_client`, and `config`/`stats` as shared leaves. Circular
imports are forbidden. `mapper` and `builder` MUST NOT import `database` or
`processor`.

#### Scenario: Builder needs investigation data

- GIVEN `builder.py` constructs an ARC
- WHEN it receives inputs
- THEN inputs arrive as pure data bundles
- AND it does not import `database` or `processor`
