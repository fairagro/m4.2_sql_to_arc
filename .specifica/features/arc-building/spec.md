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

## Supported Column Types (Annotation Tables)

`input`, `output`, `characteristic`, `factor`, `parameter`, `component`,
`comment`, `performer`, `date`

## Edge Cases

`study_ref` is a JSON array string → parse and register the assay with
every referenced study.

`study_ref` is missing or empty → assay is added to the ARC but linked
to no study (logged as warning).

Unknown column type → skip that column, log warning.

Annotation table targets a study/assay that doesn't exist in this
investigation's data → skip the table silently.

Contacts/publications with an unknown `target_type` → not attached
anywhere (silently dropped by filter).
