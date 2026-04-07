# Detailed Requirements Comparison — 6 Journals × 24 Criteria

## Legend

| Symbol | Meaning |
| --- | --- |
| **K.O.** | Mandatory — Rejection without review if not met |
| **Required** | Mandatory requirement (Rejection after review possible) |
| **Rec.** | Recommended / Nice-to-have |
| **–** | Not required / not mentioned / irrelevant |

Journal Abbreviations: GS = GigaScience (Tech. Note) · JIB = Journal of Integrative Bioinformatics · ScD = Scientific Data (Article) · DSJ = Data Science Journal · CEA = Computers & Electronics in Agriculture · SwX = SoftwareX

---

## 1. Requirements Matrix

| # | Criterion | GS | JIB | ScD | DSJ | CEA | SwX |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **— Software & Code —** | | | | | | | |
| 1 | Software / Code is the primary contribution | Required | Rec. | – | Rec. | Rec. | **K.O.** |
| 2 | OSI-approved open-source license | **K.O.** | Rec. | Required | Required | – | **K.O.** |
| 3 | Public code repository (e.g., GitHub) | **K.O.** | Rec. | Required | Required | Required | **K.O.** |
| 4 | Code can be executed / tested by reviewers | **K.O.** | – | – | – | – | Required |
| 5 | Test data + sample output for reviewers | **K.O.** | – | Required | – | Required | Required |
| 6 | RRID registration of the software | Rec. | – | – | – | – | – |
| 7 | bio.tools ID | Rec. | Rec. | – | – | – | – |
| **— Data & Reproducibility —** | | | | | | | |
| 8 | Dataset as primary contribution (Deposit) | – | – | **K.O.** | – | – | – |
| 9 | Formal data deposit with DOI (Repository) | Required | – | Required | Required | Required | Required |
| 10 | Data Availability Statement | Required | – | Required | Required | Required | Required |
| 11 | Code Availability Statement | Required | Rec. | Required | Required | Required | Required |
| 12 | Reproducibility Statement (Methods trackable) | **K.O.** | Rec. | Required | Required | Required | Required |
| **— Scientific Content —** | | | | | | | |
| 13 | Novelty / Innovation provable | Required | Required | Required | Required¹ | **K.O.** | Rec. |
| 14 | Comparison with existing tools / Benchmarking | Required | Rec. | – | – | Required | – |
| 15 | Quantitative test results | Required | Rec. | – | Rec. | Required | – |
| 16 | Case study / reproducible application example | Required | Rec. | – | Rec. | Required | Rec. |
| 17 | Related Work / Prior Art | Required | Required | Rec. | Required | Required | Rec. |
| 18 | Domain restriction must be met | Rec.² | Required³ | – | – | **K.O.**⁴ | – |
| **— Formal Requirements —** | | | | | | | |
| 19 | Structured Abstract (Background / Findings / Conclusions) | **K.O.** | – | – | – | – | – |
| 20 | Mandatory Manuscript Template | – | – | – | – | – | **K.O.** |
| 21 | Strict word limit (≤ 3,000 words) | – | – | – | –⁵ | – | **K.O.** |
| 22 | Harvard reference style (Author-Date) | – | – | – | **K.O.** | – | – |
| 23 | Highlights / Bullet-Point-Summary | – | – | – | – | Required | Rec. |
| 24 | CRediT Authorship Statement | Required | – | Required | Rec. | Required | Required |

### Notes

¹ DSJ: Required for Research Papers; less strict for Practice Papers (System Report) — Novelty of the *system* is sufficient.
² GS: Technically open (all domains), but the community is biologically/data science focused; agrosystems-adjacent submissions are accepted.
³ JIB: Focus on Bioinformatics / Life Science Data Integration; submissions without reference to data integration infrastructure are out-of-scope.
⁴ CEA: Strictly limited to agricultural *production*; middleware/RDM infrastructure is considered an "ancillary application" according to their own guide and is referred to sister journals.
⁵ DSJ: Research Paper ≤ 8,000 words; Practice Paper ≤ 3,000 words.

---

## 2. Impact Factor, ISSN & Reach

| Journal | ISSN (online) | JIF (2024) | CiteScore | Indexing | Open Access | APC (approx.) |
| --- | --- | --- | --- | --- | --- | --- |
| **GigaScience** | 2047-217X | 3.9 | 20.0 | SCIE, PubMed, Scopus | Gold OA (Oxford) | ~2,250 USD |
| **JIB** | 1613-4516 | 1.8 | 3.3 | ESCI, Scopus | Gold OA (De Gruyter) | ⚠️ 1,050 EUR |
| **Scientific Data** | 2052-4463 | 6.9 | 8.4 | SCIE, PubMed, Scopus | Hybrid OA (Springer Nature) | ~2,490 USD |
| **Data Science Journal** | 1683-1470 | n/a | 3.4 | Scopus, DOAJ | Gold OA (Ubiquity Press) | £770 |
| **CEA** | 1872-7107 | 8.9 | n/a | SCIE, Scopus | Hybrid OA (Elsevier) | ~3,450 USD |
| **SoftwareX** | 2352-7110 | 2.4 | 4.2 | ESCI, Scopus | Hybrid OA (Elsevier) | ~1,250 USD |

⁶ DSJ: No stable JIF available from Clarivate SCIE; CiteScore 3.4 (Scopus 2024) is the more reliable metric.

### JIF Classification

```text
CEA              (8.9)  ██████████████████     ❌ Not Suitable (Scope)
Scientific Data  (6.9)  ██████████████         ❌ Not Suitable (Scope)
GigaScience      (3.9)  ████████               ✅ Recommended
SoftwareX        (2.4)  █████                  ⚠️ Conditionally Suitable
JIB              (1.8)  ████                   ✅ Suitable
Data Science J.  (n/a)  ███████                ✅ Suitable (CiteScore 3.4)
```

**Conclusion on Impact Factor:** Of the three suitable journals (GigaScience, DSJ, JIB), GigaScience has by far the highest Impact Factor (3.9). The IF of JIB (1.8) and DSJ (CiteScore 3.4) is somewhat lower. CEA and Scientific Data have high JIF values but are not suitable in terms of content — the JIF alone is not a selection criterion.

---

## 3. Evaluation: Suitability for this Paper

### Context: What the Paper Describes

The paper describes the implementation of the FAIRagro Federated RDI Network with three open-source software components:

- `sql-to-arc` (Python, MIT, GitHub, Docker) — Conversion of relational databases → ARC
- `inspire-to-arc` (Python, MIT, GitHub, Docker) — Harvesting from INSPIRE/CSW endpoints → ARC
- FAIRagro Advanced Middleware API — Gateway: Validation & Publication of ARCs

Applied to: Edaphobase (Soil Fauna DB, via `sql-to-arc`) and BonaRes (Soil/Agricultural Research Data, via `inspire-to-arc`).

**Content Present:**

- ✅ Three open-source tools: MIT License, GitHub repos, Docker support
- ✅ Two concrete case studies (Edaphobase, BonaRes)
- ✅ Embedding in NFDI/DataPLANT ecosystem (ARC, ISA model)
- ✅ Predecessor paper in JIB [García Brizuela et al.]
- ✅ Two different integration strategies (Push via SQL adapter / Pull via INSPIRE harvesting)

**Content Still Missing (independent of journal):**

- ⚠️ Quantitative results (Number of generated ARCs, runtime)
- ⚠️ Functional comparison with existing tools (ISA-API, ro-crate-py)
- ⚠️ Formal data deposit / Test data with DOI for reviewers
- ⚠️ RRID and bio.tools IDs

---

### 3.1 GigaScience — Technical Note

#### Overall Evaluation: ✅ Suitable (with additions) · JIF 3.9

| Criterion | Status |
| --- | --- |
| **Impact Factor** | ✅ 3.9 (JIF) — highest value among suitable journals |
| Software as primary contribution | ✅ present (three tools + Middleware API) |
| MIT License (OSI) | ✅ present |
| GitHub Repositories | ✅ present |
| Docker / containerized deployment | ✅ present (explicitly preferred by GigaScience) |
| Code executable by reviewers | ⚠️ Docker setup with minimal test data still missing |
| Test data + sample output | ⚠️ must be provided via GigaDB |
| Comparison with existing tools | ⚠️ Related Work present, but no functional benchmark |
| Quantitative test results | ⚠️ missing (number of ARCs, runtime) |
| Case studies | ✅ present (Edaphobase, BonaRes) |
| Domain / Community | ✅ ISA/ARC known in the GigaScience ecosystem |

**Conclusion:** The paper meets the core of the GigaScience requirements. The missing points (Test data, Benchmark, Quantitative results) are scientifically meaningful additions. With a JIF of 3.9, GigaScience offers the highest scientific visibility among all suitable journals and sets the highest, but most justified, requirements.

---

### 3.2 Journal of Integrative Bioinformatics (JIB)

#### Overall Evaluation: ✅ Suitable (lowest barrier) · JIF 1.8

| Criterion | Status |
| --- | --- |
| **Impact Factor** | ⚠️ 1.8 (JIF) — lowest value (with JIF) of all six journals |
| Bioinformatics domain relevance | ✅ ARC and ISA are DataPLANT-/NFDI concepts, known in JIB |
| Predecessor paper in the same journal | ✅ García Brizuela et al. in JIB → natural continuation |
| JIB.tools integration | ✅ automatic; adoption into bio.tools |
| No K.O. criteria | ✅ most flexible format of all six journals |
| Quantitative results | 🟡 recommended, but not mandatory |
| Formal data deposit | 🟡 not explicitly required |
| Benchmarking | 🟡 recommended, not mandatory |

**Conclusion:** JIB is the path of least resistance. The predecessor paper creates a direct thematic bridge; the community knows ARC and DataPLANT. The low JIF (1.8) is the main disadvantage — a publication there has significantly lower reach and scientific perceptibility than GigaScience.

---

### 3.3 Scientific Data (Nature)

#### Overall Evaluation: ❌ Not Suitable · JIF 6.9

| Criterion | Status |
| --- | --- |
| **Impact Factor** | ✅ 6.9 (JIF) — high; but scope does not fit |
| Primary contribution = Dataset | ❌ the paper describes software, not a dataset |
| Formal data deposit as core | ❌ ARC outputs are not an independent scientific dataset |
| Reframing required | ❌ the fundamental contribution type would need to be changed |

**Conclusion:** Scientific Data would have the second-highest JIF (6.9), but is not suitable in terms of content. Software infrastructure that generates datasets is not an accepted primary contribution. The high IF is an illusion — a desk-rejection would be very likely.

---

### 3.4 Data Science Journal (CODATA)

#### Overall Evaluation: ✅ Suitable (as Practice Paper) · CiteScore 3.4

| Criterion | Status |
| --- | --- |
| **Impact Factor** | ⚠️ 3.4 (CiteScore) — comparable to JIB |
| FAIR infrastructure as a topic | ✅ fits directly — CODATA is the organization behind FAIR |
| System Report ("Practice Paper") | ✅ explicitly intended for operational system descriptions |
| No benchmarking necessary | ✅ eases submission |
| Harvard reference style | ⚠️ all references would need to be reformatted |
| Word limit Practice Paper (≤3,000 w.) | ⚠️ tight for three components + context |
| APC | ✅ cheapest option (£770) |
| Community Reach | ⚠️ smaller than GigaScience |

**Conclusion:** A valid option if additions (Benchmark, Test data) cannot be fully realized in a timely manner. The Practice Paper track fits well in terms of content. Main disadvantage: Missing JIF / only moderate CiteScore and the Harvard formatting requires additional effort.

---

### 3.5 Computers & Electronics in Agriculture (CEA)

#### Overall Evaluation: ❌ Not Suitable · JIF 8.9

| Criterion | Status |
| --- | --- |
| **Impact Factor** | ✅ 8.9 (JIF) — very high; but scope does not fit |
| Agricultural production problem as core | ❌ the paper does not solve an agricultural production problem |
| "Ancillary application" per guide | ❌ RDM middleware is explicitly excluded |
| Strict domain restriction | ❌ K.O. criterion cannot be met |

**Conclusion:** CEA has an attractive JIF (8.9), but like Scientific Data, it is an illusion: its own guide explicitly excludes RDM middleware as an "ancillary application". Desk-rejection very likely.

---

### 3.6 SoftwareX (Elsevier)

#### Overall Evaluation: ⚠️ Conditionally Suitable · JIF 2.4

| Criterion | Status |
| --- | --- |
| **Impact Factor** | 🟡 2.4 (JIF) — moderate |
| MIT License, GitHub | ✅ present |
| Software as primary contribution | ✅ fits in terms of content |
| 3,000-word limit (strict) | ❌ not sufficient for 3 tools + context + case studies |
| Mandatory template | ⚠️ complete restructuring required |
| No benchmarking necessary | ✅ lowest content barrier |

**Conclusion:** SoftwareX would be suitable in terms of content for a focused single-tool paper. The 3,000-word limit disqualifies the comprehensive paper. The JIF (2.4) lies between JIB and GigaScience — acceptable, but the formatting restriction outweighs it.

---

## 4. Overall Overview: Suitability + Impact Factor

| Journal | Suitability | JIF (approx.) | Justification (Short Form) |
| --- | --- | --- | --- |
| **GigaScience** | ✅ **Recommended** | 3.9 | Best scope fit + highest JIF among suitable journals |
| **JIB** | ✅ Suitable | 1.8 | Lowest barrier; predecessor paper there; low JIF |
| **Scientific Data** | ❌ Not Suitable | 6.9 | High JIF, but scope mismatch (Dataset vs. Software) |
| **Data Science Journal** | ✅ Suitable | n/a (CS 3.4) | Practice Paper fits; cheapest APC |
| **CEA** | ❌ Not Suitable | 8.9 | High JIF, but desk-rejection very likely |
| **SoftwareX** | ⚠️ Conditional | 2.4 | Moderate; only for single-tool paper; word limit K.O. |

---

## 5. Recommendation

### 🥇 Primary Recommendation: GigaScience — Technical Note

#### Justification

1. **Highest JIF (3.9)** among all content-suitable journals — maximum scientific visibility and likelihood of citation.

2. **Best Scope Fit:** GigaScience is the natural home for open-source tools for data analysis and management at scale. `sql-to-arc`, `inspire-to-arc` and the Middleware API fit exactly into this framework.

3. **Ecosystem Alignment:** The ISA model, ARC and RO-Crate are known concepts in the GigaScience environment. DataPLANT-related tools have been published in GigaScience-adjacent venues.

4. **Scientific Integrity:** The requirements (Benchmarking, Quantitative results, executable demo) are not just formal hurdles — they strengthen the paper regardless of the target journal.

5. **No Word Limit** allows for a complete description of all three components and both case studies.

6. **GigaDB** as an integrated archiving platform for code snapshots and test data.

**Open Points (Prerequisites for GigaScience):**

| Task | Description |
| --- | --- |
| Quantitative Results | Number of generated ARCs from Edaphobase and BonaRes, runtime |
| Benchmark | Functional comparison with ISA-API / ro-crate-py |
| Reproducible Demo | Docker Compose + minimal Edaphobase sample dataset for reviewers |
| RRID | Registration of all three tools at SciCrunch.org |
| GigaDB Submission | Code snapshot + ARC sample outputs with DOI |

### 🥈 Alternative: Journal of Integrative Bioinformatics (JIB)

#### Choose If

The open points (Benchmark, Test data) cannot be fully realized in a timely manner and community continuity to the predecessor paper [García Brizuela et al.] is a priority. The significantly lower JIF (1.8 vs. 3.9) should be consciously accepted in this case.
