## 1. Demo Mock Harvest API

- [ ] 1.1 Refactor `demo_api_main.py` ARC write/chown path into a shared helper usable by harvest and legacy routes
- [ ] 1.2 Add in-memory harvest store and implement `POST /v3/harvests`, `POST /v3/harvests/{id}/arcs`, `POST /v3/harvests/{id}/complete`, and `PATCH /v3/harvests/{id}` with ApiClient-compatible JSON
- [ ] 1.3 Keep `GET /live` and optionally `POST /v3/arcs`; document harvest flow in `openspec/specs/demo-environment/design.md` notes only if touched during apply (delta already covers behavior)

## 2. Converter Upload Via `harvest_arcs`

- [ ] 2.1 Introduce stream-state tracking (investigation id, studies/assays) for successfully built ARC payloads
- [ ] 2.2 Replace `create_or_update_arc` upload path in `processor.py` with an async generator fed into `ApiClient.harvest_arcs` (expected_datasets from scope)
- [ ] 2.3 After `harvest_arcs` returns (or aborts), apply outcomes: `set_harvest_id`, `record_failed` per item error, `record_harvested` for remaining submits, `add_studies` / `add_assays`; handle catastrophic abort without legacy fallback
- [ ] 2.4 Ensure build failures / `None` builds never enter the harvest stream and remain recorded as failed/skipped as today

## 3. Tests

- [ ] 3.1 Update unit tests (`test_main` and related) to mock `harvest_arcs` / `HarvestResult` instead of `create_or_update_arc`
- [ ] 3.2 Update integration workflow tests to assert harvest-based upload and absence of `create_or_update_arc`
- [ ] 3.3 Add focused demo-api tests or a lightweight smoke covering create → arcs → complete response shapes

## 4. Verify

- [ ] 4.1 Run `uv run ruff format` on touched paths and `uv run pytest middleware/sql_to_arc/tests/ -v` (or targeted subsets) until green
- [ ] 4.2 Confirm `create_or_update_arc` has no remaining call sites under `middleware/sql_to_arc/src`
