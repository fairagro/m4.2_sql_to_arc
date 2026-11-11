## ADDED Requirements

### Requirement: Report Carries Installed Converter Version

When the converter creates the run `HarvestReport`, it MUST set `software_version` to the installed `sql_to_arc`
distribution version from package metadata (same source as the `--version` CLI). The finished shared JSON-LD report MUST
include that version string on the wire when set. The converter MUST NOT invent a parallel version field or serializer
for this value.

#### Scenario: Conversion run sets software_version

- **GIVEN** the `sql_to_arc` distribution is installed with a PEP 440 version
- **WHEN** the conversion run creates its harvest report
- **THEN** `HarvestReport.software_version` equals that installed distribution version
- **AND** the printed JSON-LD document includes the same version string once

#### Scenario: Same source as --version

- **GIVEN** `importlib.metadata.version("sql_to_arc")` returns a version string
- **WHEN** a normal conversion run builds the harvest report
- **THEN** the report `software_version` matches that string
