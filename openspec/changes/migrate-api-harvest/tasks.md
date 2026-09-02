## 1. Demo Mock Harvest API

- [x] 1.1 Refactor `demo_api_main.py` ARC write/chown path into a shared helper usable by harvest and legacy routes
- [x] 1.2 Add in-memory harvest store and implement `POST /v3/harvests`, `POST /v3/harvests/{id}/arcs`, `POST /v3/harvests/{id}/complete`, and `PATCH /v3/harvests/{id}` with ApiClient-compatible JSON
- [x] 1.3 Keep `GET /live` and optionally `POST /v3/arcs`; document harvest flow in `openspec/specs/demo-environment/design.md` notes only if touched during apply (delta already covers behavior)

## 2. Converter Upload Via `harvest_arcs`

- [x] 2.1 Introduce stream-state tracking (investigation id, studies/assays) for successfully built ARC payloads
- [x] 2.2 Replace `create_or_update_arc` upload path in `processor.py` with an async generator fed into `ApiClient.harvest_arcs` (expected_datasets from scope)
- [x] 2.3 After `harvest_arcs` returns (or aborts), apply outcomes: `set_harvest_id`, `record_failed` per item error, `record_harvested` for remaining submits, `add_studies` / `add_assays`; handle catastrophic abort without legacy fallback
- [x] 2.4 Ensure build failures / `None` builds never enter the harvest stream and remain recorded as failed/skipped as today

## 3. Tests

- [x] 3.1 Update unit tests (`test_main` and related) to mock `harvest_arcs` / `HarvestResult` instead of `create_or_update_arc`
- [x] 3.2 Update integration workflow tests to assert harvest-based upload and absence of `create_or_update_arc`
- [x] 3.3 Add focused demo-api tests or a lightweight smoke covering create → arcs → complete response shapes

## 4. Verify

- [x] 4.1 Run `uv run ruff format` on touched paths and `uv run pytest middleware/sql_to_arc/tests/ -v` (or targeted subsets) until green
- [x] 4.2 Confirm `create_or_update_arc` has no remaining call sites under `middleware/sql_to_arc/src`
