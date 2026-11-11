## 1. Helper + mapper

- [ ] 1.1 Add URI→ontology-source short-name derivation (OBO/purl rules + documented unparseable → None) and an
      investigation-scoped OSR registry keyed by `(name, version)`
- [ ] 1.2 Update `_make_oa` to accept/use version, set `tsr` from derived source name, and register OSRs; pass real
      `*_version` from assay/publication/contact role mapping (do not invent terms/URIs)

## 2. Builder annotation tables

- [ ] 2.1 Stop putting `version` into `OntologyAnnotation` `tsr`; use kwargs and the same OSR/`tsr` helper for column
      and cell annotations; ensure OSRs are attached to `ArcInvestigation` before serialize

## 3. Specs docs + tests

- [ ] 3.1 Replace Key Decision 5 / mapping convention in `arc-building` design (via this change’s design; sync on
      archive) to describe URI-derived OSR + version
- [ ] 3.2 Unit tests: `_make_oa` / build path with non-empty `tsr`, non-empty `ontologySourceReferences` when
      version+URI present; no invented annotation when term missing; unparseable URI → empty tsr
- [ ] 3.3 Run focused `uv run pytest middleware/sql_to_arc/tests/ -v` and fix regressions

## 4. OpenSpec quality

- [ ] 4.1 Run `openspec validate add-ontology-source-references` and verify it passes
