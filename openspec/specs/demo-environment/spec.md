# Demo Environment

## Purpose

Provide a one-command, self-contained local environment that demonstrates
the full SQL-to-ARC pipeline end-to-end without production credentials,
mTLS certificates, or network access to external services.

## Requirements

### Requirement: Single-Command Start

The demo environment SHALL start with a single command:
`docker compose -f compose.demo.yaml up --build` (or the wrapper
`./start-demo.sh --build`).

#### Scenario: Fresh clone demo

- GIVEN the repository and Docker are available
- WHEN the operator runs the demo start command
- THEN postgres, mock API, and converter services come up without manual steps

### Requirement: Demo Database Import

The environment MUST spin up PostgreSQL and import a small demo dataset
(10 investigations) without any manual steps.

#### Scenario: Postgres healthy

- GIVEN `demo.sql` is present and bind-mounted into init
- WHEN postgres becomes healthy
- THEN the `rdi` database contains the demo investigations

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

### Requirement: Converter Against Demo Stack

The environment MUST run the `sql_to_arc` converter against the demo DB and
mock API.

#### Scenario: End-to-end demo run

- GIVEN postgres and middleware-api are healthy
- WHEN `sql_to_arc` runs
- THEN it processes the demo investigations against the mock API

### Requirement: Exit Code Propagation

The converter MUST exit 0 when all 10 investigations are processed.
Compose MUST exit with the converter's exit code (`--exit-code-from
sql_to_arc`).

#### Scenario: Successful full demo

- GIVEN all 10 investigations succeed
- WHEN compose finishes
- THEN the overall exit code is 0

### Requirement: Host-Accessible Output

Written ARC files MUST be accessible on the host via a bind-mounted
`demo_output/` volume.

#### Scenario: Inspect output on host

- GIVEN a completed demo run
- WHEN the operator lists `demo_output/` on the host
- THEN the uploaded ARC artifacts are present

### Requirement: Host File Ownership

File ownership of output files MUST match the host user via
`LOCAL_UID` / `LOCAL_GID` environment variables.

#### Scenario: Non-root host user

- GIVEN `LOCAL_UID` and `LOCAL_GID` match the host user
- WHEN the mock API writes output
- THEN ownership is corrected for host access

### Requirement: No Secrets Or External Network

The demo MUST NOT require secrets, encrypted files, or external network
calls. Production credentials, sops, mTLS, and Edaphobase full-dump
downloads are out of scope (dev environment only).

#### Scenario: Offline demo

- GIVEN no production credentials or sops keys are available
- WHEN the demo is started
- THEN it runs successfully without external network calls

### Requirement: Missing Demo SQL Fails Clearly

If `demo.sql` is missing, postgres init MUST fail and compose MUST exit
non-zero with a clear log message.

#### Scenario: demo.sql absent

- GIVEN `demo.sql` is not available to postgres init
- WHEN compose starts
- THEN postgres init fails
- AND compose exits non-zero with a clear log message

### Requirement: Unsafe ARC Identifier Fallback

If an ARC identifier in the payload is unsafe (path traversal attempt),
the mock API MUST fall back to a random ID, log to console, and MUST NOT
write outside `demo_output/`.

#### Scenario: Path traversal identifier

- GIVEN an upload whose ARC identifier contains `../`
- WHEN the mock API derives the output path
- THEN a random safe ID is used instead
- AND no files are written outside `demo_output/`

### Requirement: Create Output Directory On Demand

If `demo_output/` does not exist, the mock API MUST create it on first
request.

#### Scenario: Missing output directory

- GIVEN `demo_output/` does not exist
- WHEN the first upload arrives
- THEN the directory is created
- AND the upload proceeds
