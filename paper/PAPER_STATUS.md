# Scientific Paper: Status & Open Points

**Target journal:** GigaScience – Technical Note

**Draft file:** `paper_sql_to_arc.md`

**Status:** First draft complete — awaiting author review and feedback.

---

## What has been done

- [x] Research: codebase, architecture docs, database views schema, FAIRagro website, ARC/nfdi4plants knowledge base, GigaScience Technical Note guidelines, comparable tools
- [x] Structured abstract (Background / Findings / Conclusions, ≤250 words)
- [x] Introduction: FAIRagro, ARC/ISA model (incl. provenance graph / knowledge graph angle), middleware
- [x] Implementation: view-based adapter pattern, pipeline architecture (async I/O + ProcessPoolExecutor + Semaphore), error handling, observability, deployment
- [x] Related work comparison: ISA API, arc-to-roc, ro-crate-py, OMERO, iRODS — with feature comparison table
- [x] Availability, conclusions, declarations, references

---

## Open points — needs author input

- [ ] **Author details:** full name, institution, email address
- [ ] **DFG grant number** (Funding section)
- [ ] **Use case confirmation:** Is Edaphobase the right primary example? Or should a different database be used?
- [ ] **Co-authors:** Are there additional contributors to be listed?
- [ ] **References:** Please verify all references, especially:
  - The Weil et al. 2023 PLANTdataHUB paper (check DOI and author list)
  - The ISA API reference (Rocca-Serra et al. 2023 — currently just a GitHub link)
  - The OMERO reference (check author list)
- [ ] **RRID:** Assign a Research Resource Identifier for the software
- [ ] **(Optional)** Add a pipeline architecture figure (Figure 1 is referenced in the text but not yet created)

---

## GigaScience Technical Note checklist

- [ ] Abstract ≤ 250 words with Background / Findings / Conclusions structure
- [ ] 3–10 keywords
- [ ] Open-source software with public repository
- [ ] Supporting data deposited in a public repository (e.g., GigaDB) — *check if required for a software-only Technical Note*
- [ ] Double line spacing in final submission
- [ ] SI units used throughout
- [ ] Page numbers in final submission
