## Why

Workers already return ARC RO-Crate as a JSON string from arctrl (`ToROCrateJsonString`) for cheap IPC. The main process
still `json.loads` that string into a dict before enqueue/`harvest_arcs`, even though `ApiClient.harvest_arcs` accepts
`str` (API #191). That keeps large dict graphs on the harvest queue and re-does work the client performs anyway. Explore
locked **option B**: trust arctrl JSON and pass the string through without a converter parse (issue #27).

## What Changes

- Store/yield the worker JSON **string** on `BuiltArc` into `harvest_arcs` (no `json.loads` / dict materialization in
  the converter upload path).
- Drop the “validate JSON before harvest stream” step that existed only to fail closed before the client; rely on arctrl
  output plus client `_serialize_arc` for string inputs.
- Update `api-upload` design/spec wording from “yield dicts after parse” to “yield JSON strings from the worker”.
- Note related client gap: invalid JSON `str` currently aborts the whole harvest (API #667) — out of scope here; B
  accepts that under arctrl trust.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `api-upload`: Harvest stream payloads are worker JSON strings; converter MUST NOT parse them to dict solely for
  upload.

## Impact

- Code: `BuiltArc`, `_built_arc_from_json` (likely rename/simplify), `stream_arcs_from_queue`, tests typing
  `RoCrateContent` → `str` where appropriate.
- Specs/design under `openspec/specs/api-upload/`.
- Depends on installed `middleware.api_client` with `str` support (already present).
- Does **not** fix API #667; does **not** restore `create_or_update_arc`.

## Non-goals

- Changing arctrl build / IPC string production.
- Client-side raw HTTP body without re-parse (api_client still dict-ifies strings).
- Per-item handling of bad JSON strings inside `api_client` (tracked as API #667).
