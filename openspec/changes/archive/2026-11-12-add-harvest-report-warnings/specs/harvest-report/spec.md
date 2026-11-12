## ADDED Requirements

### Requirement: Record Shared Warnings For Non-Fatal Harvested Outcomes

When an investigation is successfully harvested and its build produced non-fatal accommodations, the converter MUST call
the shared scope warning API once per distinct warning (with the investigation id as `record_id`). Those calls MUST NOT
change harvested, failed, or skipped counts for that dataset.

#### Scenario: Edaphobase accommodation still harvested

- **GIVEN** an investigation whose ARC built successfully with at least one non-fatal accommodation warning
- **WHEN** that investigation is uploaded successfully
- **THEN** `record_harvested` is called once
- **AND** `record_warning` is called at least once with the investigation id
- **AND** failed and skipped counts are unchanged by those warning calls

#### Scenario: No accommodations

- **GIVEN** an investigation that builds and uploads without accommodation warnings
- **WHEN** the run finishes
- **THEN** `record_warning` is not called for that investigation
- **AND** the shared JSON-LD report omits `fairagro:warnings` for the RDI when no warnings were recorded

### Requirement: Shared Package Exposes Warning API

The converter MUST depend on `fairagro-middleware-shared` **≥14.3.0** so the repository scope provides `record_warning`.

#### Scenario: Shared dependency exposes warnings

- **GIVEN** the converter's declared dependency on `fairagro-middleware-shared`
- **WHEN** the environment resolves packages for a normal install
- **THEN** the resolved shared package version is at least 14.3.0
- **AND** the repository scope provides `record_warning`

## MODIFIED Requirements

### Requirement: Use Shared Harvest Report Counting API

The converter MUST create a mutable shared harvest-run report at conversion start, open exactly one repository scope for
the configured RDI, invoke the shared counting methods on that scope for conversion events (including warnings), call
finish when the run ends, and render with the shared JSON-LD serializer. It MUST NOT maintain parallel counters for
harvested, failed, skipped, warned, expected, study, or assay statistics, and MUST NOT implement its own report domain
model or JSON-LD serializer.

#### Scenario: Event updates go through the scope

- **GIVEN** an open repository scope for the configured RDI
- **WHEN** an investigation is uploaded successfully, fails, is intentionally skipped, or is harvested with warnings
- **THEN** the converter records the event via the shared counting methods on that scope
- **AND** does not copy separate local counters into the report afterward
