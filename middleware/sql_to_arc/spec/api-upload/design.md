# API Upload — Design

## API Contract

The converter calls `ApiClient.create_or_update_arc(rdi, arc_dict)` from
`processor.py`. The exact HTTP endpoint, request/response shape, and
authentication are fully encapsulated in the `middleware.api_client` shared
library and are **not a concern of this component**.

## Lifecycle in the Converter

```text
_upload_and_update_stats()
  ├── json.loads(arc_json)         → arc_dict (re-parse for API client)
  ├── ctx.client.create_or_update_arc(rdi, arc_dict)
  └── on success: log INFO
      on error:   stats.failed_datasets += 1
                  stats.failed_ids.append(investigation_id)
```

## Key Decisions

1. **JSON string → dict round-trip**
   — The worker returns a JSON string (to keep IPC clean). The main process
   parses it back to a dict for the API client. The overhead is negligible
   and keeps the worker/main interface unambiguous.

2. **Single `ApiClient` for the entire run**
   — `ApiClient` is used as an async context manager in `main.py`.
   Connection pooling amortises TLS handshake cost across all uploads.

3. **OpenTelemetry span per upload**
   — Each upload is wrapped in a `tracer.start_as_current_span("upload_arc")`
   span with `rdi`, `worker_id`, and `investigation_id` attributes. This
   makes per-investigation latency visible in any OTel-compatible backend.

4. **Error scope: `(ConnectionError, TimeoutError, ApiClientError)`**
   — Only network-level and API-level errors are caught here. Programming
   errors (e.g. bad JSON) propagate upward so they are visible in the run
   report as unexpected failures.
