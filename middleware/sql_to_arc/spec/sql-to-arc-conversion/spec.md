# SQL-to-ARC Conversion Pipeline

Orchestrate the end-to-end batch run: validate the database, process all
investigations, build ARCs, upload them, and report results. This spec
covers only the glue between the other features; the details live there.

## Requirements

- [ ] Validate that all required database views and columns exist before
      starting the main loop — see [database-access/spec.md](../database-access/spec.md)
- [ ] Stream investigations one at a time and fetch related entities in
      bulk per batch — see [database-access/spec.md](../database-access/spec.md)
- [ ] For each investigation: build the ARC in an isolated worker process —
      see [arc-building/spec.md](../arc-building/spec.md)
- [ ] Upload each successfully built ARC to the Middleware API —
      see [api-upload/spec.md](../api-upload/spec.md)
- [ ] Record success and failure per investigation by ID; print a JSON
      provenance report to stdout when the run completes
- [ ] Exit with code 0 if processing succeeded (even with partial failures);
      non-zero on fatal errors (schema mismatch, DB unreachable, etc.)
- [ ] Worker process timeout (default 30 min) → investigation counted as
      failed, loop continues
- [ ] Respect `debug_limit` config to cap the number of investigations
      processed (for testing)
- [ ] Support `--version` CLI flag; support `--config` to specify config file

## Scope

Covers orchestration only: entry point, process lifecycle, stats
aggregation, exit codes, and CLI flags. Per-feature behaviour (DB queries,
ARC construction, API calls) is out of scope here.
