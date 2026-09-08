# Project Principles

This repository extends the shared foundation in
[`principles.global.md`](principles.global.md). Read that file first for Values,
Supported development environment, Type Safety, Configuration, Code Quality,
Testing, Security, Spec/Code naming, Python tooling, and Branch strategy.

Do **not** redefine or weaken Supported development environment or Type Safety
here — those sections are owned by `principles.global.md`.

Product stack, module map, and converter constraints live below. Surface-bar
path rows for this product belong in
[`docs/surface-quality-bar.md`](../docs/surface-quality-bar.md) (not here).

Behavioral OpenSpec requirements (RFC 2119) for this foundation stay in
[`openspec/specs/principles/`](specs/principles/) — this file is the
agent-facing overlay, not a replacement for that domain spec.

---

## Technology Stack

The following technologies are foundational to the SQL-to-ARC converter.
Component specs may assume their presence and must not replace them with
alternatives without a project-level decision recorded here.

| Technology | Role |
| ---------- | ---- |
| **Python 3.12** | Converter runtime |
| **PostgreSQL 15** | Source database (SQL views only) |
| **SQLAlchemy (async)** | Database access inside `Database` |
| **Pydantic v2** | Config and row models |
| **arctrl** | ARC object construction / RO-Crate JSON-LD |
| **httpx** | HTTP via `middleware.api_client` |
| **uv** | Package manager (never pip/poetry directly) |
| **Docker** | Dev Container + demo/dev compose |

External packages `middleware.shared` and `middleware.api_client` come from
`m4.2_advanced_middleware_api` via the uv workspace.

---

## Module Dependency Rules

```text
middleware/sql_to_arc/   ← converter (entry, orchestration, mapping, upload)
middleware.shared        ← ConfigWrapper / shared utilities (git workspace)
middleware.api_client    ← Middleware API client (git workspace)
```

- Converter code may depend on `shared` and `api_client`.
- Do not add reverse dependencies from this repo into the API package sources
  beyond the published workspace packages.

---

## Configuration (product)

Shared rules are in `principles.global.md`. In this repo:

- Runtime configuration is read from YAML via `ConfigWrapper`
  (`middleware.shared.config.config_wrapper`).
- **No `os.environ` calls in application code.** Environment variables are
  resolved by `ConfigWrapper` only, with prefix **`SQL_TO_ARC`**.
- Every configurable value must have a Pydantic field with a `description`.
- Defaults belong in `Config`, not in application code.
- See the `config-wrapper` skill for the full pattern.

---

## Converter Constraints

- **Views only** — all SQL lives in the `Database` class and MUST query only
  the views in `docs/sql_to_arc_database_views.md`, never raw tables.
- **Worker IPC** — ProcessPool workers exchange **JSON strings only**; never
  pickle ARC / .NET interop objects across process boundaries.
- **Stateless batch** — no local cache/lock state between runs; durable output
  is what the Middleware API receives (harvest upload).
- **Correctness over throughput** — unmappable investigations fail clearly;
  do not upload invalid ARC.

---

## Testing (product layout)

Shared testing expectations are in `principles.global.md`. Layout here:

- Unit: `middleware/sql_to_arc/tests/unit/`
- Integration: `middleware/sql_to_arc/tests/integration/`
- Run with `uv run pytest middleware/sql_to_arc/tests/ -v` (scoped as needed).

---

## Scaling

- Stream investigations; keep peak RAM bounded for large view result sets.
- Prefer one converter process per container; scale by replicas / batch size
  config rather than in-process shared mutable ARC state.
- After serializing ARC JSON in workers, allow GC (`gc.collect()` where the
  skill documents it) so peak RSS stays predictable.
