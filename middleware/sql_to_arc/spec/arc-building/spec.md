# ARC Building

Transform pre-fetched database rows into a valid ARC RO-Crate JSON-LD
document for a single investigation. Runs in an isolated worker process;
must be stateless and side-effect-free.

## Requirements

- [ ] Accept a self-contained `ArcBuildData` bundle (investigation +
      related studies, assays, contacts, publications, annotations)
- [ ] Map `InvestigationRow` → `ArcInvestigation` and wrap in `ARC`
- [ ] Map each `StudyRow` → `ArcStudy`; register in the ARC
- [ ] Map each `AssayRow` → `ArcAssay`; register in the ARC; link to
      studies via `study_ref` (supports single ID or JSON array)
- [ ] Map each `ContactRow` → `Person`; attach to investigation, study,
      or assay depending on `target_type`
- [ ] Map each `PublicationRow` → `Publication`; attach to investigation
      or study depending on `target_type`
- [ ] Build `ArcTable` objects from flat annotation rows; attach to the
      correct study or assay
- [ ] Serialize the finished ARC to a JSON-LD string via
      `arc.ToROCrateJsonString()`
- [ ] Explicitly free ARC objects and call `gc.collect()` before returning
- [ ] Never import `database`, `processor`, or `config`; inputs arrive
      as pure Pydantic data

## Edge Cases

`study_ref` is a JSON array string → parse and register the assay with
every referenced study.

Duplicate `vAssay` rows with the same `identifier` within one investigation
(e.g. one row per study link in Edaphobase) → add the assay once; merge
study links from subsequent rows when all other fields match; log one aggregated
warning per investigation (with row count).

Plain-text `study_ref` (single study ID, not a JSON array) → coerce to a
one-element array; log one aggregated warning per investigation (with assay count).

Native JSON `roles` on `vContact` (parsed list from the DB driver, not a JSON
string) → coerce to a JSON string; log one aggregated warning per investigation
(with contact count).

Missing `first_name` on `vContact` (ARCtrl requires a given name string) → use
an empty given name at serialization; log one aggregated warning per
investigation (with contact count).

Duplicate `identifier` with conflicting metadata (any field other than
`study_ref` / `investigation_ref`) → raise `DuplicateAssayRowError`; the
investigation build fails.

Investigation has assays but no studies → log warning.

Unknown column type → skip that column, log warning.

Annotation table targets a study/assay identifier that does not exist in
the current investigation's data → skip the table, log warning.

Contact or publication has an unknown `target_type` → not attached
anywhere; log warning.
