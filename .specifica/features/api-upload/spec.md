# API Upload

Publish each finished ARC RO-Crate JSON-LD document to the FAIRagro
Middleware API. The upload is the final step of the per-investigation
lifecycle and is the only I/O operation that reaches outside the local
machine at runtime.

## Requirements

- [ ] Upload each ARC as a JSON body to `POST /v3/arcs?rdi=<rdi>`
- [ ] Include the `rdi` identifier as a query parameter on every request
- [ ] Parse the API response and log success or failure per investigation
- [ ] On `ConnectionError`, `TimeoutError`, or `ApiClientError` → count as
      `failed_datasets`, add `investigation_id` to `failed_ids`, continue
- [ ] Reuse a single `httpx.AsyncClient` across all uploads within a run
      (connection pooling)
- [ ] Support mTLS: load client certificate and key from config and/or
      tmpfs secrets at startup
- [ ] Support configurable base URL, timeout, and retry policy via
      `ApiClientConfig`

## Scope

The `ApiClient` is a shared library (`middleware/api_client`), not owned
by this component. This spec covers the *usage contract* from the converter's
perspective, not the client implementation.

## Edge Cases

API returns non-2xx → treat as `ApiClientError`, mark investigation failed.

API is unreachable at startup → first upload attempt fails; the converter
does not pre-check connectivity (fail per-investigation, not globally).

`arc_json` is `None` (build returned nothing) → log error, mark failed,
skip upload entirely.

Upload timeout (configurable) → mark failed, continue.
