# API Upload

Publish each finished ARC RO-Crate JSON-LD document to the FAIRagro
Middleware API. The upload is the final step of the per-investigation
lifecycle and is the only I/O operation that reaches outside the local
machine at runtime.

## Requirements

- [ ] For each successfully built ARC, call
      `ApiClient.create_or_update_arc(rdi, arc)` with the RO-Crate dict
- [ ] On `ConnectionError`, `TimeoutError`, or `ApiClientError` → count as
      `failed_datasets`, add `investigation_id` to `failed_ids`, continue
- [ ] Log success or failure per investigation after each call
- [ ] Reuse the same `ApiClient` instance across all uploads within a run

## Configuration

The converter passes an `ApiClientConfig` (from `config.api_client`) to the
`ApiClient` constructor, which includes base URL, timeout, and credentials.
The converter does not interpret these values itself.

## Edge Cases

`ApiClientError` (any non-success response) → mark investigation failed,
continue.

API is unreachable at startup → first upload attempt fails; the converter
does not pre-check connectivity.

`arc_json` is `None` (build returned nothing) → log error, mark failed,
skip upload entirely.
