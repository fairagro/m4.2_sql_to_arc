## Context

See `proposal.md`. Locked explore **A** for issue #36: OntologyAnnotations continue to come only from view triples;
derive `OntologySourceReference.Name` / `OA.tsr` from the term-accession URI; put `xxx_version` on the OSR.

## Goals / Non-Goals

**Goals**

- Non-empty `ArcInvestigation.OntologySourceReferences` when the DB provides ontology version (and a derivable source
  name from URI).
- `OntologyAnnotation.tsr` matches the corresponding OSR `Name`.
- TermSourceREF on annotations is preserved through `ToROCrateJsonString` when set.
- Fix annotation-table builder misuse of positional `OntologyAnnotation(term, uri, version)` (version was landing in
  `tsr`).

**Non-Goals**

- DB schema change for an explicit source-name column.
- Fabricating terms/URIs when views leave them empty.

## Decisions

1. **URI-derived source short name** — reasoning: views have no TermSourceREF field; ARCtrl needs `OSR.Name` ≡ `OA.tsr`.
   Prefer OBO-style parse (`…/ENVO_00002001` → `ENVO`). Document fallback when URI is missing or unparseable: leave
   `tsr=""`, do not invent a fake source name, and skip OSR registration for that annotation (version alone is not
   enough without a name key).

2. **One OSR per `(source_name, version)`** — reasoning: same ontology can appear under different access versions;
   collapsing only by name would drop provenance. Identical pairs are registered once per investigation.

3. **Register OSRs on the investigation after/during build** — reasoning: assays/contacts/publications/annotation tables
   all hang off one `ArcInvestigation`; collect unique OSRs while building OAs (shared helper/registry) then ensure they
   are on `investigation.OntologySourceReferences` before serialize.

4. **Pass real `xxx_version` into `_make_oa`** — reasoning: mapper currently passes `None` for assay/publication
   versions; wire the model fields through. Contact roles already have `version` in JSON.

5. **Replace KD5** — reasoning: “no OSR” is obsolete; document URI derivation + version-on-OSR instead.
   **Sync-on-archive text for `openspec/specs/arc-building/design.md` KD5 + mapping line:**

   > 5. **OntologySourceReference from URI + version** — `OntologyAnnotation` is built only from view triples
   >    (`term`→`name`, `uri`→`tan`). `TermSourceREF` (`tsr`) is the ontology short name derived from the term-accession
   >    URI (OBO/purl `PREFIX_digits`). `xxx_version` is stored on a matching `OntologySourceReference` (unique per
   >    `(name, version)`) on the investigation, not on the annotation. Unparseable/missing URI → empty `tsr`, no OSR.
   >    Note: arctrl RO-Crate export may omit the `ontologySourceReferences` array while preserving annotation `tsr`.

   > `xxx_version` → `OntologySourceReference.version` (with URI-derived `Name` / OA `tsr`)

## Risks / Trade-offs

- [Non-OBO URIs] → Mitigate: documented parse rules + empty tsr / no OSR when derivation fails (no invented name).
- [Conflicting file/description for same name+version] → Mitigate: first-wins or URI-as-file only; keep MVP minimal
  (`name`, `version`, optional `file` from ontology IRI if known).
- [Builder positional OA args] → Mitigate: switch to kwargs `name=` / `tan=` / `tsr=` with version only on OSR.
- [arctrl RO-Crate omits OSR array] → `ToROCrateJsonString` (arctrl 3.2.3) preserves annotation `TermSourceREF` but does
  not emit / round-trip `ontologySourceReferences`. Contract is the ARC object model before serialize; document on
  archive when syncing KD5. Revisit if a later arctrl release serializes OSRs into RO-Crate.

## Migration Plan

1. Implement helper + mapper/builder wiring + tests on the issue branch.
2. Archive OpenSpec after apply/PR readiness.

## Open Questions

None — option A locked (Kurzname aus URI).
