## Why

DB views expose `(xxx_term, xxx_uri, xxx_version)` ontology triples, but the converter drops `xxx_version` and always
sets `OntologyAnnotation.tsr` to `""`. ARCs serialize with empty `ontologySourceReferences`, so ontology version
provenance is lost (issue #36; current Key Decision 5 in `arc-building/design.md`). Explore locked **option A**: keep
creating annotations only from view data; derive the ISA TermSourceREF / `OntologySourceReference.Name` short name from
the term-accession URI; register OSRs on the investigation and wire `tsr`.

## What Changes

- When a view triple provides enough data (at least a usable URI and preferably a version), derive a short ontology
  source name from the URI (OBO/`purl.obolibrary.org` patterns and documented fallbacks).
- Register distinct `OntologySourceReference` objects on `ArcInvestigation.OntologySourceReferences` keyed by
  `(source_name, version)`.
- Set `OntologyAnnotation.tsr` to that source name for mapper-built and annotation-table OAs; stop stuffing `version`
  into the `tsr` constructor slot in the annotation-table builder.
- Do **not** invent OntologyAnnotations when term/uri are absent from the view (existing empty-OA behaviour stays).
- Update `arc-building` design KD5 and mapping convention; add unit coverage for `_make_oa` / OSR wiring with non-empty
  `tsr`.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `arc-building`: Ontology annotations carry TermSourceREF linked to investigation-level `OntologySourceReference`
  entries populated from view version + URI-derived source name.

## Impact

- Code: `mapper.py` (`_make_oa` + OSR registry helper), `builder.py` (annotation headers/cells + append OSRs on the
  investigation), possibly a small shared helper for URI→source-name.
- Specs/design: `openspec/specs/arc-building/`.
- Tests: mapper/builder unit tests for tsr + non-empty `ontologySourceReferences` in JSON-LD when version data exists.

## Non-goals

- Adding a new DB column for TermSourceREF (option D).
- Using `xxx_term` as `OntologySourceReference.Name` (issue text mistake; term ≠ source).
- Inventing annotations or URIs when the view omits them.
- Fixing unrelated RO-Crate fields.
