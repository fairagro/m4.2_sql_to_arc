## Why

The converter still uploads each ARC via the legacy `ApiClient.create_or_update_arc`
endpoint. The Middleware API and sibling harvester now use a harvest-session
workflow (`create_harvest` → submit ARCs → `complete_harvest` / `fail_harvest`),
exposed to clients as `ApiClient.harvest_arcs`. Remaining on the old path leaves
sql_to_arc out of sync with the shared client contract ([issue #34](https://github.com/fairagro/m4.2_sql_to_arc/issues/34))
and prevents the local demo mock from exercising the real upload lifecycle.

## What Changes

- Replace per-investigation `create_or_update_arc` with **`ApiClient.harvest_arcs`**
  (same pattern as `m4.2_middleware_harvester`): stream built ARC JSON into an
  async generator, let the client create/complete/fail the harvest session.
- Wire `RepositoryScope.set_harvest_id` from the returned `HarvestResult`, and
  apply upload outcomes (`record_harvested` / `record_failed` + study/assay
  counts) from the harvest result — not from a per-call success path alone.
- **BREAKING** (API usage): `create_or_update_arc` MUST no longer be called from
  sql_to_arc application code.
- Update the demo mock API to implement the harvest HTTP surface needed by
  `harvest_arcs` (`POST /v3/harvests`, `POST /v3/harvests/{id}/arcs`,
  `POST /v3/harvests/{id}/complete`, `PATCH /v3/harvests/{id}`), reusing the
  existing arctrl write path for ARC payloads.
- Update unit/integration tests and OpenSpec domains accordingly.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `api-upload`: Upload contract changes from `create_or_update_arc` to
  `harvest_arcs`; success/failure accounting follows harvest outcomes.
- `sql-to-arc-conversion`: Run lifecycle owns one harvest session for the RDI
  (stream builds into `harvest_arcs` instead of upload-per-investigation).
- `demo-environment`: Mock Middleware API must support the harvest lifecycle
  so `./start-demo.sh` works without the legacy single-ARC path.

## Impact

- **Code:** `processor.py` (upload orchestration); tests
  (`test_main`, `test_workflow`, related mocks); `dev_environment/demo_api_main.py`
  (+ demo-environment specs/design as needed).
- **Dependency:** Existing `middleware.api_client` harvest APIs (already in
  tree); no new package required if the locked client already exposes
  `harvest_arcs`.
- **Operators / demo:** Local demo must speak harvest routes; production
  Middleware API already does.
- **Non-goals:** Replacing `HarvestReport` / `RepositoryScope` (already adopted);
  implementing full server-side harvest persistence semantics in the mock
  (in-memory happy path is enough); multi-RDI harvests; changing arc-building
  or database-access contracts.
