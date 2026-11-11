## MODIFIED Requirements

### Requirement: Upload Via ApiClient

For each conversion run, the system MUST upload successfully built ARCs through
`ApiClient.harvest_arcs(rdi, arcs, expected_datasets=…)` (or an equivalent client API that creates a harvest, submits
each ARC into that harvest, and completes or fails the harvest). The system MUST NOT call
`ApiClient.create_or_update_arc` from application code. Each successfully built ARC MUST be yielded into the harvest
stream as the worker JSON **string** produced by arctrl serialization. The converter MUST NOT `json.loads` that string
solely to materialize a dict for `harvest_arcs`.

#### Scenario: Successful harvest upload

- **GIVEN** one or more non-empty ARC JSON payloads for the run's RDI
- **WHEN** the upload phase runs
- **THEN** `harvest_arcs` is invoked with that RDI and an async stream of ARC JSON strings
- **AND** `create_or_update_arc` is not called

#### Scenario: Stream items are JSON strings

- **GIVEN** a worker returned a non-empty `arc_json` string from arctrl
- **WHEN** that investigation is enqueued for harvest
- **THEN** the harvest stream yields that string (or an equivalent string payload)
- **AND** the converter does not parse it into a dict before yielding

### Requirement: Built ARCs Feed The Harvest Stream

Only successfully built ARC JSON payloads MUST enter the harvest upload stream. Build failures, skipped investigations,
and empty (`None`) build results MUST NOT be submitted into the harvest. The converter MUST NOT reject a non-`None`
worker string solely by parsing it as JSON before enqueue; JSON validity for string inputs is the ApiClient’s
responsibility once the item is yielded.

#### Scenario: Empty build excluded from harvest

- **GIVEN** a worker returned `None` for `arc_json`
- **WHEN** the harvest stream is produced
- **THEN** that investigation is recorded as failed on the repository scope
- **AND** no ARC payload for it is yielded to `harvest_arcs`

#### Scenario: Non-empty worker string enters the stream

- **GIVEN** a worker returned a non-empty `arc_json` string
- **WHEN** the harvest stream is produced
- **THEN** that string is yielded to `harvest_arcs`
- **AND** the converter does not call `json.loads` on it only to gate enqueue
