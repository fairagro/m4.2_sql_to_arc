## MODIFIED Requirements

### Requirement: Mock Middleware API

The environment MUST run a mock Middleware API (`middleware-api`) that
implements the harvest lifecycle used by `ApiClient.harvest_arcs`: create a
harvest, accept ARC RO-Crate submissions under that harvest, and complete or
fail the harvest. Successful ARC submissions MUST write artifacts under the
local `demo_output/` directory (same host-ownership rules as today).

#### Scenario: End-to-end harvest upload

- **GIVEN** the mock API is healthy
- **WHEN** the converter runs `harvest_arcs` against it
- **THEN** a harvest is created
- **AND** submitted ARCs are written under `demo_output/`
- **AND** the harvest can be completed (or failed) through the mock endpoints

## ADDED Requirements

### Requirement: Harvest Endpoints On The Mock

The mock MUST expose at least:

- `POST /v3/harvests` — create a harvest (`RUNNING`)
- `POST /v3/harvests/{harvest_id}/arcs` — submit an ARC into that harvest
- `POST /v3/harvests/{harvest_id}/complete` — mark the harvest `COMPLETED`
- `PATCH /v3/harvests/{harvest_id}` — set terminal status (`FAILED`,
  `CANCELLED`, or `COMPLETED`)

Responses MUST be parseable by `middleware.api_client` harvest/ARC result
models for the happy path. Full production auth, idempotency, and persistence
semantics are out of scope for the mock.

#### Scenario: Create then submit then complete

- **GIVEN** the mock API is running
- **WHEN** a client creates a harvest, posts an ARC to `/v3/harvests/{id}/arcs`, then completes the harvest
- **THEN** each step returns a success response compatible with the ApiClient parsers
- **AND** the ARC files are present under `demo_output/`
