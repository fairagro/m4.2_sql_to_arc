# Surface quality bar — path map (product overlay)

Product-local **path→surface** map for Finder/Fixer triage. Use **this table
first** when a path matches; otherwise fall back to
[`docs/surface-quality-bar.global.md`](surface-quality-bar.global.md). Rules
(how the bar affects step 5 / nits / dismiss) stay in
[`docs/ai_review_policy.md`](ai_review_policy.md).

Do not hand-edit the synced `.global.md`. Sync of `.global.md` must not
overwrite this file.

## Model (this repo)

Quality is driven by **who can hurt whom**, not by “is it under `middleware/`”.

1. **User-facing / operator contracts** — config the operator supplies, CLI /
   entrypoints they run, and the harvest/upload contract toward the Middleware
   API. Highest bar: wrong or hostile input must fail safely with **clear
   errors**; no silent corruption; no invalid ARC uploaded as success.
2. **Supporting domain + third-party I/O** — SQL view reads, ARC build/mapping,
   ProcessPool orchestration, httpx/API client. Must **not undermine** (1).
   Toward Postgres and the Middleware API, apply **similar care** (explicit
   failure, no silent data loss) on realistic paths. Everything else on this
   surface: **documented happy path only** — exotic edges → dismiss.
3. **Global rows** (scripts, agent plumbing, docs, vendor skills) — unchanged;
   see `.global.md`.

## Path map

| Surface | Typical paths | Bar (what must work) | Default for exotic edge cases |
| ------- | ------------- | -------------------- | ----------------------------- |
| **User-facing / operator contracts** | `middleware/sql_to_arc/src/middleware/sql_to_arc/{main,config}.py`; operator YAML / env (`Config` / `ConfigWrapper`, `dev_environment/config.*.yaml`); harvest/upload outcomes surfaced to operators (stats, failed IDs) | **Full boundary:** valid and invalid config; clear errors; no silent bad ARC upload; tests for failure modes operators hit | **Fix** when correct and in this PR |
| **Supporting domain + third-party I/O** | `processor.py`, `pipeline.py`, `builder.py`, `mapper.py`, `database.py`, `models.py`; `docs/sql_to_arc_database_views.md` consumers; `middleware.api_client` usage; `dev_environment/{compose,config}.{demo,dev}.yaml`, `demo_api_main.py`; OpenSpec domains `sql-to-arc-conversion`, `arc-building`, `database-access`, `api-upload` | **Uphold** operator contracts (errors, types, view-only SQL). **Third-party care** on Postgres / Middleware API realistic paths. **Otherwise** only the documented happy path | **Dismiss** exotic edges that do not threaten operator contracts or DB/API integrity (practicality Low / None). Still **fix** when a default caller or view/API path is wrong |

When a file sits under both ideas, pick the **stricter** surface (usually
operator-facing if it shapes CLI/config/upload errors).

## Out of scope here

Agent CLI (`scripts/ai/`), synced Devinfra scripts, vendor skills, and pure
docs/OpenSpec cadence stay on the **global** rows — do not restate them unless
this product needs a different bar for a path the global table mis-classifies.
