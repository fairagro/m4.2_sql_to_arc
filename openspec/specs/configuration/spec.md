# Configuration

## Purpose

Define how the converter reads, validates, and exposes configuration so that
all code has a single, typed source of truth for runtime settings.

## Requirements

### Requirement: YAML Config At Startup

The system SHALL load configuration from a YAML file at startup. The path
MUST be provided via the CLI `-c` / `--config` flag.

#### Scenario: Normal startup

- GIVEN a valid config YAML path passed via `--config`
- WHEN the converter starts
- THEN configuration is loaded and validated before processing begins

### Requirement: Env And Secret Overrides

Any config field SHALL be overridable by an environment variable or Docker
secret using the naming convention `{PREFIX}_{FIELD_PATH}` (prefix
`SQL_TO_ARC` for this component).

#### Scenario: Override connection string

- GIVEN `SQL_TO_ARC_CONNECTION_STRING` is set in the environment
- WHEN configuration is loaded
- THEN the env value overrides the YAML field
- AND Docker secrets under `/run/secrets/sql_to_arc_*` follow the same mapping

### Requirement: Pydantic Validation Before Start

All config values MUST be validated and type-coerced via Pydantic before the
application starts.

#### Scenario: Invalid type in YAML

- GIVEN a config field has an invalid type
- WHEN configuration is loaded
- THEN startup fails with a validation error
- AND processing does not begin

### Requirement: Explicit Dependency Injection

The resulting `Config` object MUST be exposed through explicit dependency
injection. No module MAY read environment variables or config files after
startup.

#### Scenario: Module needs a setting mid-run

- GIVEN processing is underway
- WHEN a module needs a config value
- THEN it uses the injected `Config` instance
- AND does not reload YAML or read env vars

### Requirement: Typed Config Fields Only

All new settings MUST be added as typed, annotated fields in `Config` (or a
sub-model referenced by `Config`). Ad-hoc env reads and global variables are
forbidden.

#### Scenario: Adding a new setting

- GIVEN a new runtime setting is required
- WHEN it is introduced
- THEN it is declared as a typed field on `Config` (or a nested model)
- AND documented in `config.example.yaml`

### Requirement: Secrets Via SecretStr

Secrets (`connection_string`, TLS keys) MUST use `pydantic.SecretStr`.
Access via `.get_secret_value()` MUST occur only at the point of use; values
MUST NOT be passed to `str()` or logged.

#### Scenario: Using the DB connection string

- GIVEN `Config.connection_string` is a `SecretStr`
- WHEN the database engine is created
- THEN `.get_secret_value()` is called at that point only
- AND the secret is not logged or stringified elsewhere

### Requirement: Load Once Per Run

Configuration MUST be loaded once in `main.py` and passed down via function
arguments. It MUST NOT be re-loaded during a run.

#### Scenario: Long batch run

- GIVEN the converter is processing many investigations
- WHEN config values are needed throughout the run
- THEN the same `Config` instance loaded at startup is reused
