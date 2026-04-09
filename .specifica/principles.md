# FAIRagro SQL-to-ARC — Principles

## Purpose

Convert metadata from a relational SQL database into the
Annotated Research Context (ARC) format and publish the result to the
FAIRagro Middleware API. The converter runs as a one-shot batch process,
not as a long-running service.

## Values

**Correctness over speed** — valid ARC output matters more than throughput.
If a dataset cannot be mapped cleanly it must fail with a clear error, not
produce silent garbage.

**Memory-safe by design** — the dataset is large (tens of thousands of
investigations). Every architectural decision must keep peak RAM bounded and
predictable. Assume the host has limited memory.

**Failure isolation** — one bad investigation must not abort the entire run.
Stats and error IDs are collected and reported at the end.

**Stateless batch process** — the converter stores no state between runs.
No cache, no lock files, no database writes. The only persistent output is
what the Middleware API receives.

**Security by default** — inputs from external sources (database, API,
config) are treated as untrusted. Follow OWASP best practices: validate
before use, fail closed, apply least privilege.

## Constraints

- Python 3.12. No type-unsafe workarounds; all public APIs are fully typed.
- `uv` for dependency management. Never call `pip` directly in production code.
- `os.environ` must never be accessed directly; use `Config` / `ConfigWrapper`.
- All SQL lives inside the `Database` class. Views are the contract; the
  converter never queries raw tables.
- Worker processes communicate via JSON strings only (no shared objects, no
  pickle of domain objects across the IPC boundary).
- Code quality gates: Ruff (lint + format), mypy, pylint, bandit, pytest —
  all must pass before merge. Every new feature requires matching tests.
- No `noqa`/`type: ignore` suppressions unless technically unavoidable.

## Module Dependency Graph

```text
main → processor → builder → mapper
                 ↘ database
                 ↘ api_client (shared lib)
config ←── all modules (read-only)
stats  ←── processor, database (write)
```

Circular imports are forbidden. `mapper` and `builder` must not import
`database` or `processor`.

## Extension Points

| Need | Where to change |
| --- | --- |
| New DB entity | Add view, model in `models.py`, stream method in `database.py`, mapper in `mapper.py` |
| New config value | Extend `Config` in `config.py` with Pydantic field |
| New mapper function | Add to `mapper.py`, re-export from `builder.py` |
| New ARC structure | Extend `builder.py` helper functions |
