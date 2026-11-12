# Harvest Report

## Purpose

Define how the SQL-to-ARC converter drives and emits the shared harvest-run report from `fairagro-middleware-shared`,
without restating the shared library contract itself.

## Requirements

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

### Requirement: Record Shared Warnings For Non-Fatal Harvested Outcomes

When an investigation is successfully harvested and its build produced non-fatal accommodations, the converter MUST call
the shared scope warning API once per distinct warning (with the investigation id as `record_id`). Those calls MUST NOT
change harvested, failed, or skipped counts for that dataset.

#### Scenario: Non-fatal accommodation still harvested

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

### Requirement: Single Repository Scope For The Run

The finished harvest-run report MUST contain exactly one repository scope snapshot for the configured RDI.

#### Scenario: Completed conversion run

- **WHEN** the conversion run finishes (with or without per-investigation failures)
- **THEN** the report has exactly one repository entry whose identifier is the configured RDI

### Requirement: Drive Shared Fields From The Live Conversion

For the open repository scope the converter MUST:

- set expected datasets when a total is known before or during the run
- set harvest id when the Middleware API yields one for the run or repository
- call record harvested only after definitive upload success
- call record failed with a message and the investigation identifier on build, upload, timeout, and validation failures
  that abort that dataset
- call record skipped for each intentionally skipped investigation dataset
- call add studies / add assays for composition counts of successfully harvested investigations only

#### Scenario: Successful upload counts as harvested

- **GIVEN** an investigation whose ARC uploaded successfully
- **WHEN** the upload step completes without error
- **THEN** record harvested is called once for that investigation
- **AND** its study and assay counts are added to the scope

#### Scenario: Upload failure is not harvested

- **GIVEN** an investigation whose upload raises a network or API error
- **WHEN** the failure is handled
- **THEN** record failed is called with a message and the investigation id
- **AND** record harvested is not called for that investigation

#### Scenario: Expected count known

- **GIVEN** the converter can determine how many investigations will be considered for this run
- **WHEN** that total is known
- **THEN** expected datasets is set on the repository scope

#### Scenario: Expected count unknown

- **GIVEN** no reliable investigation total is available
- **WHEN** the report is serialized
- **THEN** expected datasets remains unset (omitted on the wire)

### Requirement: Print Shared JSON-LD Report To Stdout

After the run is finished, the converter MUST serialize the report with the shared JSON-LD serializer and print the
resulting string to stdout. Serialization or print failures MUST be logged and MUST NOT change the process exit code for
an otherwise successful processing run.

#### Scenario: Mixed results still emit a report

- **GIVEN** some investigations succeeded and some failed
- **WHEN** the run finishes and the report is finalized
- **THEN** a shared-format JSON-LD document is printed to stdout
- **AND** it includes harvested and failed counts for the RDI entry

#### Scenario: Serializer failure is non-fatal

- **GIVEN** the JSON-LD serializer raises an error
- **WHEN** emission is attempted
- **THEN** the error is logged
- **AND** the process exit code is unchanged relative to processing outcome

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
