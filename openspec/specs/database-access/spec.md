# Database Access

## Purpose

Provide a typed, async, memory-safe interface to the SQL views. All SQL in
the project lives here; no other module may query the database directly.

## Requirements

### Requirement: Multi-Dialect Async Connection

The system SHALL connect to any SQLAlchemy-supported async dialect via a
connection string (PostgreSQL, MySQL, MSSQL, Oracle) and MUST normalise
scheme prefixes automatically.

#### Scenario: Legacy postgresql:// prefix

- GIVEN a connection string starting with `postgresql://`
- WHEN the database engine is created
- THEN it is rewritten to `postgresql+psycopg://`

#### Scenario: Other dialects

- GIVEN prefixes `mysql://`, `mariadb://`, `oracle://`, or `mssql://`
- WHEN normalised
- THEN they become `mysql+aiomysql://`, `mysql+aiomysql://`,
  `oracle+oracledb://`, or `mssql+aioodbc://` respectively

### Requirement: Schema Validation Before Loop

The system MUST validate that all required views exist and have the
expected columns before the main processing loop starts.

#### Scenario: Required view present

- GIVEN all required views and columns exist
- WHEN `validate_schema()` runs
- THEN validation succeeds and processing may start

### Requirement: Optional Columns Warn

The system MUST warn (not fail) when optional columns are missing and use
model defaults.

#### Scenario: Optional column absent

- GIVEN an optional column is missing from a view
- WHEN schema validation runs
- THEN a warning is logged
- AND processing continues with model defaults

### Requirement: Required Columns Must Exist

The system MUST fail fast with `MissingRequiredColumnsError` when required
columns are absent.

#### Scenario: Required column missing

- GIVEN a required column is absent from a view
- WHEN schema validation runs
- THEN `MissingRequiredColumnsError` is raised

### Requirement: Required Columns Must Not Be Null

The system MUST fail fast with `RequiredColumnsNullError` when required
columns contain NULL values, unless `spec_override=True` is set on the
field.

#### Scenario: NULLs in required column

- GIVEN a required column contains NULL values and no `spec_override`
- WHEN schema validation runs
- THEN `RequiredColumnsNullError` is raised

### Requirement: Stream Investigations

The system MUST stream investigations using a server-side cursor and MUST
NEVER load the full table into memory.

#### Scenario: Large investigation table

- GIVEN millions of investigation rows
- WHEN `stream_investigations()` is consumed
- THEN rows are fetched incrementally via a server-side cursor

### Requirement: Bulk Fetch Related Entities

The system MUST fetch related entities (studies, assays, contacts,
publications, annotations) in bulk for a list of investigation IDs using a
single `WHERE investigation_ref = ANY(...)` query per entity type.

#### Scenario: Batch of investigation IDs

- GIVEN a list of investigation IDs from the current batch
- WHEN related entities are streamed
- THEN one query per entity type loads all matching rows

### Requirement: Validate Rows With Pydantic

The system MUST validate each row against its Pydantic model; invalid rows
MUST be skipped with a warning and MUST increment `failed_datasets`.

#### Scenario: Row fails validation

- GIVEN a row that fails Pydantic validation
- WHEN it is mapped
- THEN it is skipped
- AND a warning with field errors is logged
- AND failure stats are incremented

### Requirement: Annotation Cross-Field Constraints

For `vAnnotationTable` rows, the system MUST also validate cross-field
constraints (e.g. `column_io_type` required when `column_type` is `input`
or `output`). Constraint violations MUST log a warning but MUST NOT skip
the row.

#### Scenario: input column missing column_io_type

- GIVEN an annotation row with `column_type` input and missing `column_io_type`
- WHEN the row is validated
- THEN a warning is logged
- AND the row is still processed (rescue path)

### Requirement: View Contract Document

The authoritative column-level specification for all views — including
required/optional fields, data types, and cross-dialect type mappings —
MUST be maintained in `docs/sql_to_arc_database_views.md`. Every view MUST
have a corresponding `BaseRow` subclass in `models.py`; no raw dicts MAY
cross module boundaries.

#### Scenario: Adding a new view column

- GIVEN a new column is added to a view
- WHEN the converter is updated
- THEN `docs/sql_to_arc_database_views.md` and the matching `BaseRow` model
  are updated together

### Requirement: Empty Investigation List Short-Circuit

An empty investigation list passed to `_stream_by_investigation` MUST
return immediately without a query.

#### Scenario: Empty ID list

- GIVEN an empty list of investigation IDs
- WHEN related entities are requested
- THEN no SQL query is executed
- AND an empty stream is returned

### Requirement: Missing View Handling

If a view does not exist, `validate_schema()` MUST log a warning and skip
that view for optional views; missing required views MUST be fatal.

#### Scenario: Optional view missing

- GIVEN an optional view is absent
- WHEN schema validation runs
- THEN a warning is logged and that view is skipped

#### Scenario: Required view missing

- GIVEN a required view is absent
- WHEN schema validation runs
- THEN validation fails fatally
