# API Upload

## Purpose

Publish each finished ARC RO-Crate JSON-LD document to the FAIRagro
Middleware API. The upload is the final step of the per-investigation
lifecycle and is the only I/O operation that reaches outside the local
machine at runtime.

## Requirements

### Requirement: Upload Via ApiClient

For each successfully built ARC, the system MUST call
`ApiClient.create_or_update_arc(rdi, arc)` with the RO-Crate dict.

#### Scenario: Successful create or update

- GIVEN a non-empty ARC JSON string for an investigation
- WHEN the upload runs
- THEN `create_or_update_arc` is called with the RDI and parsed ARC dict

### Requirement: Network And API Errors Are Non-Fatal

On `ConnectionError`, `TimeoutError`, or `ApiClientError`, the system MUST
count the investigation as `failed_datasets`, add `investigation_id` to
`failed_ids`, and continue.

#### Scenario: ApiClientError response

- GIVEN the API returns a non-success response
- WHEN the upload fails with `ApiClientError`
- THEN the investigation is marked failed
- AND processing continues with the next investigation

#### Scenario: Timeout

- GIVEN the API call times out
- WHEN `TimeoutError` is raised
- THEN the investigation is marked failed
- AND the run continues

### Requirement: Per-Investigation Upload Logging

The system MUST log success or failure per investigation after each call.

#### Scenario: Successful upload

- GIVEN the API accepts the ARC
- WHEN the call completes
- THEN an INFO success log is written for that investigation

### Requirement: Reuse ApiClient Instance

The system MUST reuse the same `ApiClient` instance across all uploads
within a run. Connection details come from `ApiClientConfig`
(`config.api_client`); the converter MUST NOT reinterpret those values.

#### Scenario: Many uploads in one run

- GIVEN dozens of investigations succeed builds
- WHEN each is uploaded
- THEN they share one `ApiClient` instance for the run

### Requirement: No Startup Connectivity Pre-Check

If the API is unreachable at startup, the first upload attempt MUST fail
normally; the converter MUST NOT pre-check connectivity.

#### Scenario: API down at start

- GIVEN the Middleware API is unreachable when the converter starts
- WHEN the first upload is attempted
- THEN that attempt fails and is recorded
- AND no separate pre-flight connectivity check ran

### Requirement: Skip Upload When Build Returned Nothing

If `arc_json` is `None` (build returned nothing), the system MUST log an
error, mark the investigation failed, and skip the upload entirely.

#### Scenario: Empty build result

- GIVEN the worker returned `None` for `arc_json`
- WHEN the upload step is reached
- THEN no API call is made
- AND the investigation is marked failed with an error log
