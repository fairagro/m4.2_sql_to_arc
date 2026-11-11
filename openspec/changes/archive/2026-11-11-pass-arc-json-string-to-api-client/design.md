## Context

See `proposal.md`. Locked explore option **B** for issue #27: pass arctrl JSON strings into `harvest_arcs` without a
converter-side `json.loads`. API #191 (`str` ARC inputs) is done; API #667 (bad `str` aborting the whole harvest)
remains a separate client bug.

## Goals / Non-Goals

**Goals**

- Remove dict materialization of ARC JSON in the main process for upload.
- Keep `BuiltArc` metadata (investigation id, inv_info, composition) unchanged aside from payload type.
- Keep empty/`None` build exclusion and catastrophic harvest handling as today.

**Non-Goals**

- Fixing API #667 in this repo.
- Skipping client `_serialize_arc` parse.
- Option A (validate-then-keep-string).

## Decisions

1. **Trust arctrl JSON; no converter parse for upload** — reasoning: the only successful `arc_json` source is
   `ARC.ToROCrateJsonString()` in `build_single_arc_task`. Re-parsing in the main process duplicates client work and
   holds large dicts on the queue. Choose B over A (defense-in-depth parse) and over keeping today’s dict payload.

2. **`BuiltArc.arc_payload` becomes `str`** — reasoning: one field for the harvest stream item; avoids
   `RoCrateContent | str` union noise. Size logging can use `len(arc_json.encode("utf-8"))` without parsing.

3. **Invalid JSON string behaviour stays client-defined** — reasoning: under B, a theoretically bad string would hit
   `_serialize_arc` inside `harvest_arcs` and today aborts the session (API #667). Document the dependency; do not add a
   converter workaround that reintroduces the parse.

4. **Still never call `create_or_update_arc`** — unchanged harvest-only upload path.

## Risks / Trade-offs

- [Bad JSON aborts harvest until API #667] → Mitigate: arctrl trust; link #667; do not claim per-item serialize errors
  in this change.
- [Tests assume dict yields] → Mitigate: update unit/integration mocks to expect `str` stream items.

## Migration Plan

1. Implement on issue branch; update tests.
2. Archive OpenSpec after merge readiness.
3. Follow API #667 independently for gentler client serialize errors.

## Open Questions

None — option B locked.
