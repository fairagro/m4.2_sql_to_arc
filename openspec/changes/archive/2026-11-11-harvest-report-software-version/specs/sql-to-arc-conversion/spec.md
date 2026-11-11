## ADDED Requirements

### Requirement: Log Converter Version At Job Start

Every conversion run (not `--version`) MUST log the installed `sql_to_arc` PEP 440 distribution version once at INFO
near job start, before conversion work begins. The logged value MUST use the same package-metadata source as the
`--version` CLI. Existing `--version` print-and-exit behavior MUST remain unchanged.

#### Scenario: Normal conversion logs version

- **GIVEN** the operator starts a conversion run without `--version`
- **AND** the `sql_to_arc` distribution is installed
- **WHEN** the job starts
- **THEN** an INFO log includes the installed PEP 440 version once before conversion proceeds

#### Scenario: --version unchanged

- **GIVEN** the operator passes `--version`
- **WHEN** the CLI runs
- **THEN** the version is printed to stdout
- **AND** conversion does not start
