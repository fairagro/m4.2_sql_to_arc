# Database Access — Design

## Class Structure

```text
Database
  ├── engine: AsyncEngine          (SQLAlchemy async engine)
  ├── validator: SchemaValidator   (pre-flight checks)
  ├── stream_investigations()      (server-side cursor, yields InvestigationRow)
  ├── stream_studies()             (bulk fetch by investigation IDs)
  ├── stream_assays()
  ├── stream_contacts()
  ├── stream_publications()
  └── stream_annotation_tables()  (yields raw dicts)

SchemaValidator
  ├── validate_models()            (iterates all registered models)
  ├── _validate_model()            (columns + NULL checks per model)
  ├── _get_db_columns()            (SQLAlchemy inspect)
  ├── _check_column_presence()     (required vs optional field distinction)
  └── _check_null_values()         (SELECT COUNT WHERE col IS NULL)
```

## Key Decisions

1. **Server-side cursor for investigations**
   — `conn.stream(stmt)` with `stream_results=True` keeps the result set
   on the DB server. The engine fetches rows in small batches rather than
   pulling the whole table into Python RAM.

2. **`SELECT *` via `literal_column("*")`**
   — Using `sqlalchemy.literal_column("*")` generates `SELECT *` without
   quoting the view name into `"vInvestigation"."*"`, which breaks some
   dialects. This is intentional, not an oversight.

3. **`WHERE investigation_ref = ANY(:ids)` for related entities**
   — One round-trip per entity type per batch. Avoids the N+1 problem
   (one query per investigation) while keeping memory bounded (no full
   table load).

4. **`spec_required` / `spec_override` field metadata**
   — Standard Pydantic `is_required()` is not sufficient: some fields have
   a default value but must still be present in the view. Custom
   `json_schema_extra` flags let the validator express this distinction
   without modifying the Python type.

5. **Connection string normalisation in `__init__`**
   — Legacy `postgresql://` and similar prefixes are rewritten to async
   driver schemes before the engine is created. This lets operators reuse
   existing connection strings without changing config.

6. **`_validate_and_map` centralises row parsing**
   — All DB-to-model transitions go through a single method; validation
   errors are logged uniformly and the caller decides whether to skip or
   raise.

## Schema Validation Flow

```text
validate_schema()
  └── for each model:
        _get_db_columns()        → inspect view columns
        _check_column_presence() → missing required → raise
                                 → missing optional → warn
        _check_null_values()     → NULLs in required field → raise
                                 → NULLs + spec_override  → warn
```

## Annotation Tables

Annotation rows are streamed as raw `dict` objects keyed by column name.
The dict contains both column metadata (`column_type`, `column_io_type`,
`column_value`, etc.) and cell data (`cell_value`, `cell_annotation_term`,
…) plus routing keys (`target_type`, `target_ref`, `table_name`).
`builder.py` groups and processes them after the stream is consumed.
