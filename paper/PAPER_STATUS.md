# Scientific Paper: Status & Open Points

**Target journal:** GigaScience – Technical Note (or Journal of Integrative Bioinformatics)

**Draft file:** `paper_sql_to_arc.md`

**Status:** Second draft — revised to reference predecessor paper and shift focus from implementation details to conceptual/architectural overview.

---

## What has been done

- [x] Research: codebase, architecture docs, database views schema, FAIRagro website, ARC/nfdi4plants knowledge base, GigaScience Technical Note guidelines, comparable tools
- [x] Read and analysed predecessor paper: García Brizuela et al. (2024), "A roadmap for a middleware as a federation service for integrative data retrieval of agricultural data", *Journal of Integrative Bioinformatics*, 21(3). https://doi.org/10.1515/jib-2024-0027
- [x] **Major revision:** Reframed paper as a follow-up to the roadmap paper — describing the realisation of the "extended middleware" concept
- [x] **Focus shift:** Moved away from implementation details (async I/O, ProcessPoolExecutor, Semaphore, memory management) towards conceptual/architectural overview
- [x] **Narrative arc:** Roadmap → Design decisions (view-based adapter, middleware API) → Application (Edaphobase) → Related work → Conclusions
- [x] Referenced predecessor paper throughout as [1]
- [x] Added DFG grant number (501899475) from predecessor paper
- [x] Introduced FDO (FAIR Digital Object) terminology consistent with predecessor paper
- [x] Implementation details retained only at a high level (pipeline steps, production-readiness)
- [x] Structured abstract (Background / Findings / Conclusions)
- [x] Related work comparison with feature table
- [x] Availability, conclusions, declarations, references

---

## Changes in second draft

1. **New title:** "From Roadmap to Reality: Implementing the FAIRagro Extended Middleware for Automated ARC Generation from Legacy Research Databases"
2. **New framing:** The paper now explicitly positions itself as a follow-up to García Brizuela et al. (2024), describing the progress from conceptual roadmap to operational system
3. **Reduced implementation details:** Removed detailed descriptions of async I/O patterns, semaphore flow control, garbage collection strategies, OpenTelemetry instrumentation, configuration parameters. Retained high-level pipeline description.
4. **New section "Approach":** Replaces the old "Implementation" section with a more conceptual description of the design decisions and components
5. **New section "Application: Edaphobase":** Describes the validation of the approach with a concrete use case
6. **Added abbreviations:** FDO, AAI (consistent with predecessor paper)
7. **Updated references:** Added predecessor paper [1], food security reference [2], NFDI reference [5]; removed Külheim (2025) self-reference for middleware (now described inline)

---

## Open points — needs author input

- [ ] **Author details:** full name, institution, email address
- [ ] **Co-authors:** Are there additional contributors to be listed? Consider co-authors from the predecessor paper who contributed to the middleware concept (e.g. Daniel Arend, Matthias Lange, Xenia Specka)
- [ ] **Target journal:** Is GigaScience still the target, or should this be submitted to the Journal of Integrative Bioinformatics (same journal as the predecessor paper)?
- [ ] **Title:** The new title emphasises the roadmap-to-reality narrative. Alternative: keep it more neutral?
- [ ] **Edaphobase reference:** Need a proper citation for the Edaphobase database (currently placeholder [9])
- [ ] **Use case detail:** Should the Edaphobase section include more concrete results (number of investigations converted, example ARC structures)?
- [ ] **References:** Please verify all references, especially:
  - The Weil et al. 2023 PLANTdataHUB paper (check DOI and author list)
  - The ISA API reference (Rocca-Serra et al. 2023 — currently just a GitHub link)
  - The OMERO reference (check author list)
- [ ] **RRID:** Assign a Research Resource Identifier for the software
- [ ] **(Optional)** Add figures: architecture diagram showing the pipeline flow, and/or a diagram showing the relationship between basic and extended middleware

---

## GigaScience Technical Note checklist

- [ ] Abstract ≤ 250 words with Background / Findings / Conclusions structure
- [ ] 3–10 keywords
- [ ] Open-source software with public repository
- [ ] Supporting data deposited in a public repository (e.g., GigaDB) — *check if required for a software-only Technical Note*
- [ ] Double line spacing in final submission
- [ ] SI units used throughout
- [ ] Page numbers in final submission
