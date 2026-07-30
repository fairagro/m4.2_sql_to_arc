## MODIFIED Requirements

### Requirement: Network And API Errors Are Non-Fatal

On `ConnectionError`, `TimeoutError`, or `ApiClientError`, the system MUST
record the investigation as failed on the shared repository scope with a
failure message and the investigation identifier, and continue. It MUST NOT
maintain a parallel local failed-id list for the end-of-run report.

#### Scenario: ApiClientError response

- **GIVEN** the API returns a non-success response
- **WHEN** the upload fails with `ApiClientError`
- **THEN** the investigation is recorded as failed on the repository scope
- **AND** processing continues with the next investigation

#### Scenario: Timeout

- **GIVEN** the API call times out
- **WHEN** `TimeoutError` is raised
- **THEN** the investigation is recorded as failed on the repository scope
- **AND** the run continues

## ADDED Requirements

### Requirement: Successful Upload Records Harvested

After `ApiClient.create_or_update_arc` completes without error, the system
MUST record one harvested dataset on the shared repository scope for that
investigation. Harvested MUST NOT be recorded before the upload outcome is
known.

#### Scenario: Upload succeeds

- **GIVEN** a non-empty ARC JSON string and a successful API response
- **WHEN** the upload step completes
- **THEN** record harvested is invoked once for that investigation
