# API Upload — Design

## API Contract

The converter calls `ApiClient.harvest_arcs(rdi, arcs, expected_datasets=…)`
from `processor.py`. The client owns create → parallel submit → complete (or
`fail_harvest` on catastrophic errors). Exact HTTP paths, request/response
shapes, and authentication stay inside `middleware.api_client` and are **not
a concern of this component**. Application code MUST NOT call
`create_or_update_arc`.

## Lifecycle in the Converter

```text
process_investigations()
  ├── build workers enqueue BuiltArc (validated JSON) on a queue
  ├── async generator yields ARC dicts into harvest_arcs
  │     (ArcStreamState tracks investigation id + study/assay counts)
  ├── client.harvest_arcs(rdi, stream, expected_datasets=…)
  └── on HarvestResult:
        set_harvest_id; record_failed per item error;
        record_harvested + add_studies/add_assays for the rest
      on catastrophic abort:
        record_failed / repository issue for submitted items;
        no create_or_update_arc fallback
```

## Key Decisions

1. **`harvest_arcs`, not per-investigation create/update**
   — Aligns with the shared Middleware harvester. The client owns parallel
   submit, retries, and per-item vs catastrophic error classification.

2. **JSON string → dict at enqueue / stream boundary**
   — Workers return a JSON string (clean IPC). The main process validates
   and parses before enqueue so invalid JSON never enters the harvest
   stream.

3. **Single `ApiClient` for the entire run**
   — `ApiClient` is used as an async context manager in `main.py`. One
   harvest session covers the RDI run.

4. **OpenTelemetry span around harvest upload**
   — The upload phase is wrapped in a `harvest_upload` span (plus existing
   per-build spans). Finer per-ARC API spans, if any, live inside the client.

5. **Outcome application after `harvest_arcs` returns**
   — Scope updates (harvested / failed / composition / harvest id) are
   applied from `HarvestResult.errors` and stream-state metadata, not
   per-yield success callbacks. Errors without a mappable `arc_id` become
   repository issues; investigations without a matching per-item error are
   recorded as harvested.
