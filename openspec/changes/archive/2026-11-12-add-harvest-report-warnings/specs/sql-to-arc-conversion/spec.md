## ADDED Requirements

### Requirement: Worker Build Result Includes Warning Payloads

When a worker build succeeds, the process-boundary result MUST include the ARC RO-Crate JSON string and MAY include a
list of JSON-serializable warning payloads (message text, optional stable kind). The converter MUST NOT pickle ARC or
.NET objects across the worker boundary. On definitive harvest success for that investigation, each returned warning
MUST be applied via the shared harvest-report warning API.

#### Scenario: Successful build with warnings

- **GIVEN** a worker that produces ARC JSON and one or more warning payloads
- **WHEN** the main process receives the build result and the ARC uploads successfully
- **THEN** each warning payload is recorded on the repository scope for that investigation
- **AND** the ARC JSON string is still submitted to harvest unchanged in content

#### Scenario: Successful build without warnings

- **GIVEN** a worker that produces ARC JSON and an empty warning list
- **WHEN** the ARC uploads successfully
- **THEN** harvest proceeds as today with no warning API calls for that investigation
