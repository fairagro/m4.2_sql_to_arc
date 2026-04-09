# Database Access

Provide a typed, async, memory-safe interface to the Edaphobase SQL views.
All SQL in the project lives here; no other module may query the database
directly.

## Requirements

- [ ] Connect to any SQLAlchemy-supported async dialect via a connection
      string (PostgreSQL, MySQL, MSSQL, Oracle); normalise scheme prefixes
      automatically
- [ ] Validate that all required views exist and have the expected columns
      before the main processing loop starts
- [ ] Warn (not fail) when optional columns are missing; use model defaults
- [ ] Fail fast with `MissingRequiredColumnsError` when required columns
      are absent
- [ ] Fail fast with `RequiredColumnsNullError` when required columns
      contain NULL values (unless `spec_override=True` is set on the field)
- [ ] Stream investigations using a server-side cursor; never load the full
      table into memory
- [ ] Fetch related entities (studies, assays, contacts, publications,
      annotations) in bulk for a list of investigation IDs using a single
      `WHERE investigation_ref = ANY(...)` query per entity type
- [ ] Validate each row against its Pydantic model; skip invalid rows with
      a warning and increment `failed_datasets`
- [ ] Stream annotation table rows as raw dicts (no Pydantic model);
      `mapper.py` handles them later

## Views (Contract)

| View | Pydantic Model | Purpose |
| --- | --- | --- |
| `vInvestigation` | `InvestigationRow` | Top-level metadata |
| `vStudy` | `StudyRow` | Study metadata linked to investigation |
| `vAssay` | `AssayRow` | Assay metadata linked to study |
| `vContact` | `ContactRow` | Person/contact linked to investigation, study, or assay |
| `vPublication` | `PublicationRow` | Publication linked to investigation or study |
| `vAnnotationTable` | dict | Flat annotation table rows with column metadata |

## Edge Cases

View does not exist → `validate_schema()` logs a warning and skips that
view (not fatal for optional views; fatal for required ones).

Row fails Pydantic validation → skip row, log warning with field errors,
increment `failed_ids`.

Connection string uses legacy `postgresql://` prefix → automatically
rewritten to `postgresql+psycopg://`.

Empty investigation list passed to `_stream_by_investigation` → returns
immediately without a query.
