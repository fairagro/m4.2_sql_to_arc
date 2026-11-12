## ADDED Requirements

### Requirement: Surface Non-Fatal Accommodations As Structured Warnings

When the builder applies a non-fatal Edaphobase (or similar) accommodation and still produces a complete ARC for the
investigation, it MUST record a structured warning payload for that event (stable kind + human-readable message) in
addition to any log line. Conflicting duplicate metadata that aborts the build remains a hard failure and MUST NOT be
emitted as a warning.

#### Scenario: Plain study_ref coerced

- **GIVEN** assay rows whose `study_ref` is a plain study id (not a JSON array) and metadata otherwise valid
- **WHEN** the investigation ARC is built successfully
- **THEN** the build result includes at least one structured warning describing the plain `study_ref` accommodation
- **AND** the ARC JSON is still produced

#### Scenario: Duplicate assay rows merged

- **GIVEN** duplicate `vAssay` rows for the same identifier that differ only in study linkage
- **WHEN** the investigation ARC is built successfully
- **THEN** the build result includes a structured warning for the duplicate-row merge
- **AND** the ARC JSON is still produced

#### Scenario: Conflicting duplicates still fail

- **GIVEN** duplicate assay or study rows with conflicting non-link metadata
- **WHEN** the build runs
- **THEN** the build fails with the existing duplicate-row error
- **AND** no successful ARC JSON is returned for that investigation
