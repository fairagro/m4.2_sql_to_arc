## Context

See proposal.md for motivation (legacy `create_or_update_arc` → harvest
session). Current converter flow in `processor.py`: build each ARC in a
process pool, then call `create_or_update_arc` per investigation, with a
stubbed `scope.set_harvest_id` that almost never receives an id. The sibling
[middleware harvester](https://github.com/fairagro/m4.2_middleware_harvester)
already uploads exclusively through `ApiClient.harvest_arcs` and applies
scope outcomes from the returned `HarvestResult.errors`. The locked
`middleware.api_client` already implements `harvest_arcs` (create → parallel
submit → complete, or `fail_harvest` on catastrophic errors). The local demo
mock only implements `POST /v3/arcs` today, so a harvest-based converter
would break `./start-demo.sh` unless the mock is extended.

## Goals / Non-Goals

**Goals:**

- Align sql_to_arc upload with the shared harvest client API used by the
  harvester.
- Keep build concurrency (process pool + task semaphore) while feeding an
  async ARC stream into `harvest_arcs`.
- Make the demo mock speak enough of `/v3/harvests*` for an end-to-end demo.

**Non-Goals:**

- Changing `HarvestReport` / counting vocabulary (already adopted).
- Production-faithful mock (mTLS, CouchDB, idempotency replay, GitLab sync).
- Multi-RDI runs or plugin architecture like the harvester orchestrator.

## Decisions

1. **Use `harvest_arcs`, not hand-rolled create/submit/complete**
   — Chose the high-level client API over Issue #34's three explicit calls
   because the library already owns complete-vs-fail, parallel submit, and
   per-item vs catastrophic error classification. Matches the harvester's
   `upload.py` pattern and avoids duplicating that policy in sql_to_arc.

2. **Async generator of built ARC JSON (and metadata for reporting)**
   — Build remains in the process pool; as each build succeeds, yield the
   RO-Crate payload (dict or JSON string accepted by the client) into the
   stream passed to `harvest_arcs`. Track investigation id / study / assay
   counts alongside yields (harvester-style `ArcStreamState`) so outcomes
   can be applied after the call returns. Chose this over collecting all
   ARCs first so memory stays bounded and upload can overlap remaining
   builds via the client's parallel submit.

3. **Apply scope updates after `harvest_arcs` returns**
   — For each per-item error → `record_failed`; for
   `submitted − len(errors)` → `record_harvested`; then `add_studies` /
   `add_assays` for successfully associated composition. Set
   `scope.set_harvest_id(result.harvest_id)`. On abort with submitted items,
   mark those failed; if nothing was submitted, record a repository-level
   issue when the shared API supports it, otherwise fail the known
   investigations. Chose post-hoc counting over per-yield success because
   `harvest_arcs` owns submission retries and error aggregation.

4. **No fallback to `create_or_update_arc`**
   — If harvest creation or a catastrophic failure occurs, surface it through
   the scope/report path. Falling back would hide API contract drift and
   diverge from the harvester.

5. **Demo mock: in-memory harvest store + shared ARC write helper**
   — Implement create / arcs / complete / PATCH status with an in-process
   dict keyed by `harvest_id`. Reuse today's arctrl write + chown path from a
   shared helper called by `/v3/harvests/{id}/arcs` (and optionally keep
   `/v3/arcs` for manual debugging). Responses must satisfy
   `HarvestResult` / `ArcResult` parsing. Chose a minimal mock over copying
   the real API service into the demo container.

6. **Keep `/v3/arcs` on the mock (optional compatibility)**
   — Not required by the converter after this change, but harmless for
   operators poking the mock. Spec requires harvest endpoints; legacy route
   MAY remain.

## Risks / Trade-offs

- **[Risk] Outcome attribution if ARC id ≠ investigation id**
  → Mitigation: track mapping from yielded payload identifier to
  investigation id in stream state (same idea as harvester source-URL maps).

- **[Risk] Demo response shape drift vs ApiClient models**
  → Mitigation: validate mock JSON against `HarvestResult` /
  `ArcResult` in a small unit or smoke test; keep fields minimal but
  required.

- **[Risk] Overlapping build+upload changes concurrency / backpressure**
  → Mitigation: retain existing build semaphore / process-pool limits; rely
  on api_client's submit concurrency rather than unbounded yields.

- **[Trade-off] Less granular per-upload OTel spans**
  → Acceptable: wrap `harvest_arcs` in one span (plus optional per-build
  spans already present); finer per-ARC API spans live inside the client if
  any.

## Migration Plan

1. Land demo harvest routes so local E2E can be verified in the same PR.
2. Switch processor upload to `harvest_arcs` + outcome wiring; remove
   `create_or_update_arc` call sites and update tests.
3. Run unit + integration tests and `./start-demo.sh` (or compose demo)
   before merge.
4. Rollback: revert the PR; Middleware still accepts legacy `/v3/arcs` if
   needed, but this repo will not call it after merge.
