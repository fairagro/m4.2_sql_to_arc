# ARC Building

## Purpose

Transform pre-fetched database rows into a valid ARC RO-Crate JSON-LD
document for a single investigation. Runs in an isolated worker process;
must be stateless and side-effect-free.

## Requirements

### Requirement: Accept ArcBuildData Bundle

The builder MUST accept a self-contained `ArcBuildData` bundle
(investigation plus related studies, assays, contacts, publications,
annotations).

#### Scenario: Complete bundle provided

- GIVEN a fully populated `ArcBuildData` for one investigation
- WHEN the build starts
- THEN all entities in the bundle are available without further I/O

### Requirement: Map Investigation

The builder MUST map `InvestigationRow` → `ArcInvestigation` and wrap it
in an `ARC`.

#### Scenario: Valid investigation row

- GIVEN a valid `InvestigationRow`
- WHEN mapping runs
- THEN an `ArcInvestigation` is created and wrapped in an `ARC`

### Requirement: Map And Register Studies

The builder MUST map each `StudyRow` → `ArcStudy` and register it in the
ARC.

#### Scenario: Multiple studies

- GIVEN several `StudyRow` entries for the investigation
- WHEN studies are added
- THEN each becomes an `ArcStudy` registered on the ARC

### Requirement: Map Assays And Link Studies

The builder MUST map each `AssayRow` → `ArcAssay`, register it in the ARC,
and link it to studies via `study_ref` (supports a single ID or a JSON
array).

#### Scenario: Assay linked to one study

- GIVEN an assay with a plain-text single study ID in `study_ref`
- WHEN the assay is registered
- THEN it is linked to that study

#### Scenario: Assay linked to multiple studies

- GIVEN `study_ref` is a JSON array string of study IDs
- WHEN the assay is registered
- THEN it is linked to every referenced study

### Requirement: Map Contacts By Target

The builder MUST map each `ContactRow` → `Person` and attach it to
investigation, study, or assay depending on `target_type`.

#### Scenario: Contact targets a study

- GIVEN a contact with `target_type` study and a valid target ref
- WHEN contacts are added
- THEN a `Person` is attached to that study

### Requirement: Map Publications By Target

The builder MUST map each `PublicationRow` → `Publication` and attach it
to investigation or study depending on `target_type`.

#### Scenario: Publication targets investigation

- GIVEN a publication with `target_type` investigation
- WHEN publications are added
- THEN it is attached to the investigation

### Requirement: Build Annotation Tables

The builder MUST build `ArcTable` objects from flat annotation rows and
attach them to the correct study or assay.

#### Scenario: Annotation rows for a study table

- GIVEN flat `vAnnotationTable` rows for one study table
- WHEN tables are built
- THEN an `ArcTable` is attached to that study

### Requirement: Serialize To RO-Crate JSON-LD

The builder MUST serialize the finished ARC to a JSON-LD string via
`arc.ToROCrateJsonString()`.

#### Scenario: Successful serialization

- GIVEN a fully assembled ARC
- WHEN serialization runs
- THEN a JSON-LD string is returned

### Requirement: Explicit Cleanup After Serialize

The builder MUST explicitly free ARC objects and call `gc.collect()`
before returning.

#### Scenario: After ToROCrateJsonString

- GIVEN serialization completed
- WHEN the worker prepares to return
- THEN ARC objects are deleted and `gc.collect()` is called

### Requirement: No Database Or Processor Imports

The builder MUST NEVER import `database`, `processor`, or `config`; inputs
arrive as pure Pydantic data.

#### Scenario: Worker module imports

- GIVEN `builder.py` / `mapper.py` are loaded in a worker
- WHEN import graph is inspected
- THEN they do not import `database`, `processor`, or `config`

### Requirement: Duplicate Assays With Matching Metadata

Duplicate `vAssay` rows with the same `identifier` within one investigation
MUST add the assay once and merge study links from subsequent rows when all
other fields match, logging one aggregated warning per investigation (with
row count).

#### Scenario: Same assay linked to two studies via duplicate rows

- GIVEN two assay rows sharing identifier and metadata but different study links
- WHEN assays are registered
- THEN the assay is added once with merged study links
- AND one aggregated warning is logged

### Requirement: Plain-Text Study Ref Coercion

A plain-text `study_ref` (single study ID, not a JSON array) MUST be coerced
to a one-element array, logging one aggregated warning per investigation
(with assay count).

#### Scenario: Non-JSON study_ref

- GIVEN `study_ref` is a bare study ID string
- WHEN the assay is linked
- THEN it is treated as a one-element list
- AND an aggregated warning is logged

### Requirement: Native JSON Roles Coercion

Native JSON `roles` on `vContact` (parsed list from the DB driver, not a
JSON string) MUST be coerced to a JSON string, logging one aggregated
warning per investigation (with contact count).

#### Scenario: roles arrives as a list

- GIVEN `roles` is a native list from the driver
- WHEN the contact is mapped
- THEN it is coerced to a JSON string
- AND an aggregated warning is logged

### Requirement: Missing Contact First Name

Missing `first_name` on `vContact` MUST use an empty given name at
serialization and log one aggregated warning per investigation (with
contact count).

#### Scenario: Contact without first_name

- GIVEN a contact row with null/missing `first_name`
- WHEN the person is serialized
- THEN an empty given name is used
- AND an aggregated warning is logged

### Requirement: Conflicting Duplicate Assay Metadata

Duplicate `identifier` with conflicting metadata (any field other than
`study_ref` / `investigation_ref`) MUST raise `DuplicateAssayRowError` and
fail the investigation build.

#### Scenario: Conflicting duplicate assays

- GIVEN two assay rows with the same identifier but differing titles
- WHEN assays are registered
- THEN `DuplicateAssayRowError` is raised
- AND the investigation build fails

### Requirement: Assays Without Studies Warning

If an investigation has assays but no studies, the builder MUST log a
warning.

#### Scenario: Orphan assays

- GIVEN assays exist and studies are empty
- WHEN the ARC is built
- THEN a warning is logged
- AND build continues as far as possible

### Requirement: Unknown Column Type Skipped

An unknown annotation column type MUST be skipped with a warning.

#### Scenario: Unsupported column_type

- GIVEN an annotation column with an unknown `column_type`
- WHEN the table is built
- THEN that column is skipped
- AND a warning is logged

### Requirement: Missing Annotation Target Skipped

If an annotation table targets a study/assay identifier that does not
exist in the current investigation's data, the table MUST be skipped with
a warning.

#### Scenario: Dangling target_ref

- GIVEN annotation rows targeting a non-existent study ID
- WHEN tables are attached
- THEN the table is skipped
- AND a warning is logged

### Requirement: Unknown Contact Or Publication Target

A contact or publication with an unknown `target_type` MUST NOT be
attached anywhere; a warning MUST be logged.

#### Scenario: Invalid target_type

- GIVEN a contact with an unrecognized `target_type`
- WHEN contacts are added
- THEN it is not attached
- AND a warning is logged
