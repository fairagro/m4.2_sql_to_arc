# SQL-to-ARC Conversion Pipeline

Convert all investigations from the source SQL database to ARC RO-Crate
format and publish each to the FAIRagro Middleware API in a single batch run.

## Requirements

- [ ] Read all investigations from the database via the `vInvestigation` view
- [ ] For each investigation, fetch all related studies, assays, contacts,
      publications, and annotation tables in bulk (no N+1 queries)
- [ ] Build one ARC RO-Crate JSON-LD document per investigation
- [ ] Upload each ARC to the Middleware API via `POST /v3/arcs`
- [ ] Record success and failure per investigation by ID
- [ ] Print a JSON-LD provenance report to stdout when the run completes
- [ ] Exit with code 0 if processing succeeded (even with partial failures),
      non-zero on fatal errors (schema mismatch, DB unreachable, etc.)
- [ ] Respect `debug_limit` config to cap the number of investigations
      processed (for testing)
- [ ] Validate that all required database views and columns exist before
      starting the main loop
- [ ] Support `--version` CLI flag; support `--config` to specify config file

## Scope

Covers the end-to-end batch pipeline only. API server, database schema
management, and ARC format details are in their own specs.

## Edge Cases

Validation error on a single row → skip that investigation, increment
`failed_ids`, continue.

Database view missing → fatal error before the loop starts, prints a clear
diagnostic.

API upload fails (network/timeout) → investigation counted as failed, loop
continues.

Investigation has assays but no studies → allowed, logged as warning.

`arctrl` serialization throws → investigation counted as failed, loop
continues.

Worker process timeout (default 30 min) → investigation counted as failed.
