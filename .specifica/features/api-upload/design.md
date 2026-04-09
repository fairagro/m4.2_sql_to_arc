# API Upload — Design

## Endpoint Contract

```text
POST {api_url}/v3/arcs?rdi={rdi}
Content-Type: application/json

{
  "arc": { ... }   ← ARC RO-Crate JSON-LD document
}
```

Expected response (2xx):

```json
{
  "arc_id": "...",
  "status": "created",
  "metadata": { "rdi": "...", "status": "ACTIVE", ... }
}
```

## Lifecycle in the Converter

```text
_upload_and_update_stats()
  ├── json.loads(arc_json)         → arc_dict (re-parse for API client)
  ├── ctx.client.create_or_update_arc(rdi, arc_dict)
  │     └── POST /v3/arcs?rdi=...
  └── on success: log INFO
      on error:   stats.failed_datasets += 1
                  stats.failed_ids.append(investigation_id)
```

## Key Decisions

1. **JSON string → dict → JSON string round-trip**
   — The worker returns a JSON string (to keep IPC clean). The main process
   parses it back to a dict for the API client, which re-serializes it.
   The overhead is negligible (strings are small) and keeps the worker/main
   interface unambiguous.

2. **Single `AsyncClient` for the entire run**
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

5. **mTLS at the transport layer**
   — Client key/cert are provided to `httpx` at client construction time.
   The key is read from a `tmpfs` path (`/run/secrets/client.key`) at
   container startup; it never touches disk at rest.
