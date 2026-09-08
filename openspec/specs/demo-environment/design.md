# Demo Environment — Design

## Service Topology

```text
compose.demo.yaml
  ├── postgres          (postgres:15)
  │     └── /docker-entrypoint-initdb.d/01-demo.sql  ← bind-mounted
  │         healthcheck: pg_isready -d rdi
  │
  ├── middleware-api    (python:3.12.14-slim)
  │     ├── installs fastapi + uvicorn + arctrl at startup
  │     ├── mounts demo_api_main.py read-only
  │     ├── mounts demo_output/ read-write
  │     └── healthcheck: python urllib.request → /live
  │
  └── sql_to_arc        (sql_to_arc:latest, built from repo)
        depends_on:
          postgres      (service_healthy)
          middleware-api (service_healthy)
        env: SQL_TO_ARC_CONNECTION_STRING = postgresql+psycopg://…/rdi
        config: /etc/sql_to_arc/config.yaml  ← config.demo.yaml
```

## Key Decisions

1. **DB init via `/docker-entrypoint-initdb.d/`, not a `db-init` sidecar**
   — The postgres image runs SQL files in that directory during its own
   startup, *before* the healthcheck passes. This eliminates the race
   condition where `db-init` exiting (with code 0) caused compose to stop
   postgres before `sql_to_arc` could connect.

2. **`POSTGRES_DB: rdi` on the postgres service**
   — `demo.sql` populates the `rdi` database directly. Setting `POSTGRES_DB`
   makes postgres create it on first start so the init script can import
   immediately without a `CREATE DATABASE` step.

3. **Healthcheck uses Python's stdlib `urllib.request` instead of `curl`**
   — `python:3.12.14-slim` does not include `curl`. Using Python avoids an
   extra `apt-get install` step in the image.

4. **`--exit-code-from sql_to_arc` (no `--abort-on-container-exit`)**
   — Compose waits for `sql_to_arc` to exit, then propagates its exit code.
   Without `--abort-on-container-exit`, long-running services (postgres,
   middleware-api) are not killed prematurely while the converter is running.

5. **Hardcoded `postgres/postgres` credentials**
   — The demo environment has no security requirements and no access to
   sops-encrypted secrets. Hardcoded defaults remove the need for any
   `.env` file.

6. **Path safety in `demo_api_main.py`**
   — ARC identifiers come from user-controlled JSON. The `_derive_safe_arc_id`
   function uses `os.path.realpath + startswith(base + os.sep)` (the
   CodeQL-recommended pattern) before writing any files. Falls back to a
   random hex ID when the identifier is unsafe or non-conforming.

## Mock API (`demo_api_main.py`)

```text
POST /v3/harvests
  → create in-memory harvest (RUNNING), return HarvestResult-shaped JSON

POST /v3/harvests/{id}/arcs
  → require RUNNING harvest
  → _persist_arc_payload()   (shared write helper)
  → return ArcResult-shaped JSON

POST /v3/harvests/{id}/complete
PATCH /v3/harvests/{id}      (status=COMPLETED|FAILED|CANCELLED)
  → set terminal status + completed_at

POST /v3/arcs                (legacy / debug; same write helper)

_persist_arc_payload(rdi, arc):
  → _derive_safe_arc_id()
  → write {arc_id}.payload.json
  → ARC.from_rocrate_json_string() + WriteAsync + _chown_tree

GET /live → { "status": "ok" }
```
