# API Upload

## Purpose

Publish finished ARC RO-Crate JSON-LD documents to the FAIRagro
Middleware API. Upload is the final I/O step of a conversion run and is
the only operation that reaches outside the local machine at runtime.

## Requirements

### Requirement: Upload Via ApiClient

For each conversion run, the system MUST upload successfully built ARCs
through `ApiClient.harvest_arcs(rdi, arcs, expected_datasets=…)` (or an
equivalent client API that creates a harvest, submits each ARC into that
harvest, and completes or fails the harvest). The system MUST NOT call
`ApiClient.create_or_update_arc` from application code.

#### Scenario: Successful harvest upload

- **GIVEN** one or more non-empty ARC JSON payloads for the run's RDI
- **WHEN** the upload phase runs
- **THEN** `harvest_arcs` is invoked with that RDI and an async stream of ARC payloads
- **AND** `create_or_update_arc` is not called

### Requirement: Network And API Errors Are Non-Fatal

On per-item harvest submission failures reported by the client, or on
`ConnectionError`, `TimeoutError`, or `ApiClientError` for individual ARC
submissions that the client treats as non-catastrophic, the system MUST
record the affected investigation as failed on the shared repository scope
with a failure message and the investigation identifier, and MUST continue
the run. A catastrophic harvest failure (for example auth failure or
harvest-state error that aborts `harvest_arcs`) MUST be recorded on the
scope (failed datasets and/or repository issue as applicable) without
silently falling back to `create_or_update_arc`.

#### Scenario: Per-item submission failure

- **GIVEN** the harvest client reports a per-item error for one ARC
- **WHEN** upload outcomes are applied
- **THEN** that investigation is recorded as failed on the repository scope
- **AND** other ARCs in the harvest are still processed

#### Scenario: Catastrophic harvest failure

- **GIVEN** `harvest_arcs` raises because the harvest session cannot continue
- **WHEN** the upload phase ends
- **THEN** the failure is recorded on the repository scope
- **AND** the converter does not call `create_or_update_arc` as a fallback

### Requirement: Successful Upload Records Harvested

After a harvest completes (or returns with mixed per-item results), the
system MUST record one harvested dataset on the shared repository scope for
each ARC that was submitted without a corresponding per-item error.
Harvested MUST NOT be recorded for ARCs that failed submission. When the
client returns a harvest identifier, the system MUST set it on the
repository scope.

#### Scenario: Mixed harvest outcomes

- **GIVEN** N ARCs were submitted and the harvest result lists K per-item errors
- **WHEN** upload outcomes are applied
- **THEN** harvested is recorded N−K times
- **AND** failed is recorded once per per-item error
- **AND** the harvest id from the result is set on the repository scope when present

#### Scenario: Unattributed per-item harvest error

- **GIVEN** ARCs were submitted and the harvest result includes a per-item
  error with a missing or unmapped `arc_id`
- **WHEN** upload outcomes are applied
- **THEN** a repository issue is recorded for the unattributed error
- **AND** investigations without a matching per-item error are still recorded as harvested

### Requirement: Built ARCs Feed The Harvest Stream

Only successfully built ARC JSON payloads MUST enter the harvest upload
stream. Build failures, skipped investigations, and empty (`None`) build
results MUST NOT be submitted into the harvest.

#### Scenario: Empty build excluded from harvest

- **GIVEN** a worker returned `None` for `arc_json`
- **WHEN** the harvest stream is produced
- **THEN** that investigation is recorded as failed on the repository scope
- **AND** no ARC payload for it is yielded to `harvest_arcs`

### Requirement: Per-Investigation Upload Logging

The system MUST log per-investigation upload progress when an ARC enters the
harvest stream, and MUST log overall harvest completion (or failure) for the
run. Logging MUST reflect harvest-session outcomes, not a separate
per-investigation upload RPC.

#### Scenario: ARC queued for harvest

- **GIVEN** an investigation built successfully
- **WHEN** its ARC payload is yielded into `harvest_arcs`
- **THEN** an INFO log is written for that investigation

#### Scenario: Harvest finished

- **GIVEN** `harvest_arcs` returns a result
- **WHEN** outcomes have been applied
- **THEN** an INFO log summarizes the harvest id and submitted/error counts

### Requirement: Reuse ApiClient Instance

The system MUST reuse the same `ApiClient` instance across all uploads
within a run. Connection details come from `ApiClientConfig`
(`config.api_client`); the converter MUST NOT reinterpret those values.

#### Scenario: Many uploads in one run

- **GIVEN** dozens of investigations succeed builds
- **WHEN** each is uploaded
- **THEN** they share one `ApiClient` instance for the run

### Requirement: No Startup Connectivity Pre-Check

If the API is unreachable at startup, the first upload attempt MUST fail
normally; the converter MUST NOT pre-check connectivity.

#### Scenario: API down at start

- **GIVEN** the Middleware API is unreachable when the converter starts
- **WHEN** the first upload is attempted
- **THEN** that attempt fails and is recorded
- **AND** no separate pre-flight connectivity check ran

### Requirement: Skip Upload When Build Returned Nothing

If `arc_json` is `None` (build returned nothing), the system MUST log an
error, mark the investigation failed, and skip the upload entirely.

#### Scenario: Empty build result

- **GIVEN** the worker returned `None` for `arc_json`
- **WHEN** the upload step is reached
- **THEN** no API call is made
- **AND** the investigation is marked failed with an error log
