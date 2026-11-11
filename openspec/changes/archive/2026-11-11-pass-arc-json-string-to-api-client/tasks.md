## 1. Payload type + build path

- [x] 1.1 Change `BuiltArc.arc_payload` (or rename) to hold the worker JSON `str`; remove dict/`RoCrateContent`
      materialization in `_built_arc_from_json` (simplify or inline); keep size log and None/build-failure handling
- [x] 1.2 Update `stream_arcs_from_queue` return type to yield `str` into `harvest_arcs`

## 2. Tests

- [x] 2.1 Update unit/integration tests and mocks that assume dict harvest stream items to expect JSON strings
- [x] 2.2 Remove or rewrite tests that only asserted converter-side `json.loads` reject paths for upload gating
- [x] 2.3 Run focused `uv run pytest middleware/sql_to_arc/tests/ -v` and fix regressions

## 3. OpenSpec quality

- [x] 3.1 Run `openspec validate pass-arc-json-string-to-api-client` and verify it passes
