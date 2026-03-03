# From Roadmap to Reality: Implementing the FAIRagro Extended Middleware for Automated ARC Generation from Legacy Research Databases

**Authors:** Carsten Külheim¹

¹ FAIRagro Consortium / [Institution]

**Correspondence:** [email]

**Keywords:** FAIR data, Annotated Research Context, ARC, ISA model, research data management, middleware, agrosystems, NFDI, RO-Crate, federated infrastructure

---

## Abstract

**Background:** In a previous publication, García Brizuela et al. [1] presented the FAIRagro middleware roadmap — a federated architecture concept for connecting heterogeneous research data infrastructures (RDIs) in the German agrosystems science community. That roadmap outlined a two-phase approach: a basic middleware for metadata harvesting and an extended middleware capable of transforming legacy research data into FAIR Digital Objects (FDOs) using the Annotated Research Context (ARC) specification. While the basic middleware was operational at the time of publication, the extended middleware remained a conceptual design.

**Findings:** We report the realisation of the extended middleware concept. We have developed and deployed two open-source components that together form a complete pipeline from relational research databases to FAIR data publication: (1) `sql-to-arc`, a conversion tool that extracts metadata from arbitrary relational databases and transforms it into ARCs using a view-based adapter pattern, and (2) the FAIRagro Advanced Middleware API, a gateway service that validates and publishes ARCs to the DataPLANT DataHub. The system has been applied to the Edaphobase soil fauna database, demonstrating the feasibility of the approach for large-scale, automated FAIRification of legacy research data.

**Conclusions:** The work presented here advances the FAIRagro middleware from its initial roadmap phase into an operational system. The view-based adapter pattern provides a low-friction mechanism for connecting diverse databases, while the middleware API decouples data providers from the specifics of the target FAIR data repository. Together, these components address a key gap identified in the roadmap: the automated, scalable conversion of legacy relational database metadata into standardised FAIR Digital Objects.

---

## Findings

### Background and Motivation

#### The FAIRagro Middleware Roadmap

Agriculture faces pressing challenges including climate change, biodiversity loss and stagnating productivity [2]. The massive increase in recorded measurement data, combined with advances in digital technologies, offers the potential to address these challenges — but only if the underlying data is carefully integrated and made accessible according to the FAIR principles (Findable, Accessible, Interoperable, Reusable) [3]. The German National Research Data Infrastructure (NFDI) consortium FAIRagro was established to develop FAIR-compliant infrastructure services for the agrosystems science community [4, 5].

A central challenge for FAIRagro is the federation of more than a dozen research data infrastructures (RDIs) that span different disciplines (soil science, plant science, forestry, ecology, agronomy), are maintained by different institutions, and are built on diverse technology stacks [1]. To connect these autonomous RDIs without interfering with their operational and organisational independence, FAIRagro adopted a federated middleware architecture.

García Brizuela et al. [1] described the design process and resulting architecture concept for this middleware. The approach was structured into two phases:

1. **Basic middleware:** A lightweight metadata harvesting service that crawls JSON-LD metadata from RDI landing pages and aggregates it for downstream services, such as the FAIRagro Search and Inventory Portal and the Scientific Workflow Infrastructure (SciWIn). This phase was already operational at the time of the roadmap publication.

2. **Extended middleware:** A more comprehensive system designed to go beyond metadata harvesting and enable the transformation of actual research data and rich metadata into FAIR Digital Objects (FDOs). The roadmap proposed adopting the Annotated Research Context (ARC) specification and the associated tooling ecosystem developed by the NFDI consortium DataPLANT (NFDI4Plants) [6]. The extended middleware was envisioned to support both a "push" strategy — where RDIs actively construct and submit ARCs — and a "pull" strategy — where the middleware retrieves datasets and transforms them into ARCs in a semi-automated process.

The present paper reports on the realisation of the extended middleware concept, specifically the "push" strategy in which an RDI-side tool actively constructs ARCs from legacy relational databases and submits them to the middleware for publication.

#### The Annotated Research Context (ARC)

The Annotated Research Context (ARC) is a FAIR Digital Object standard developed by the DataPLANT consortium [6]. An ARC is a structured, self-describing data container based on the RO-Crate specification [7] and the ISA (Investigation, Study, Assay) metadata framework [8]. It bundles all artefacts of a research project — raw data, processed data, workflows, and metadata — into a single, versioned, and citable package.

The ISA model at the heart of the ARC provides a three-level hierarchy for describing experimental research:

- An **Investigation** represents the top-level research context, capturing the overall aim, contributors, publications, and high-level metadata of a research programme.
- A **Study** describes a focused experiment or a specific part of the investigation, including the subjects of research, experimental design, and conditions.
- An **Assay** describes the analytical measurements or data-generating activities within a study, documenting protocols, technologies, and measured variables.

A distinctive feature of the ARC is its use of **annotation tables** — structured, spreadsheet-like tables in which every column is typed and, where applicable, linked to an ontology term. This mechanism allows experimental and measurement processes to be represented as a **provenance graph**, enabling machine-readable and semantically interoperable descriptions of complex experimental workflows.

The choice of ARC as the FDO format for the extended middleware was motivated by several factors identified in the roadmap [1]: the flexibility of the ISA model for representing heterogeneous agrosystems data, the scalable storage backend provided by GitLab, the availability of mature tooling from the DataPLANT ecosystem, and the compatibility of ARCs with the RO-Crate standard required by the downstream SciWIn infrastructure.

### Approach

The core challenge addressed in this work is the automated transformation of metadata from legacy relational databases into ARCs. This corresponds to the "push" strategy described in the middleware roadmap [1], where RDIs actively integrate the construction of ARCs into their data provision process and submit them to the middleware for validation and publication.

Our approach rests on two design decisions:

1. **View-based database adapter:** Rather than developing custom extraction code for each database, we define a standardised set of SQL views that map the source database's schema to the ISA data model. This separates the database-specific mapping logic from the conversion engine: a database administrator creates the views, while the conversion tool remains database-agnostic.

2. **Decoupled middleware API:** The conversion tool does not interact directly with the target ARC repository (the DataPLANT DataHub). Instead, it submits completed ARCs to a dedicated middleware API that handles validation, authentication, and publication. This decoupling provides a stable interface for data conversion clients and shields them from changes in the target repository's API.

#### The View-Based Database Adapter

The view-based adapter is the central abstraction for connecting a relational database to the FAIRagro middleware pipeline. To integrate a new data source, a database administrator creates a small set of SQL views that expose the database's metadata in a standardised column layout. No changes to the source application or its data model are required — the views are read-only projections of existing data.

The required views follow the ISA hierarchy:

- `vInvestigation`: one row per investigation (dataset), with identifier, title, description, and optional dates.
- `vStudy`: one row per study, linked to an investigation via a foreign key.
- `vAssay`: one row per assay, linked to an investigation and optionally to studies.
- `vContact`: one row per person associated with an investigation, study, or assay, with optional ontology-annotated roles.
- `vPublication`: one row per publication associated with an investigation or study, including DOI, PubMed ID, and ontology-annotated publication status.
- `vAnnotationTable`: one row per annotation table cell, encoding the column type, ontology annotation, and cell value in a flat representation.

Ontology annotations are represented through three fields: a human-readable term name, a term accession URI, and an optional ontology version. This design allows database owners to provide partial ontology information that can be enriched in subsequent curation steps — consistent with the semi-automated curation process foreseen in the middleware roadmap [1].

The view schema is compatible with all major relational database systems (PostgreSQL, MySQL/MariaDB, MSSQL, OracleDB). Views may be empty if the corresponding data is not available; the pipeline handles missing data gracefully. This low-friction integration mechanism is central to the scalability of the approach: connecting a new RDI requires only standard database operations, not software development.

#### The FAIRagro Advanced Middleware API

The FAIRagro Advanced Middleware API is the gateway between data conversion clients and the DataPLANT DataHub. It accepts ARC objects serialised as RO-Crate JSON-LD via a REST API, validates them against the ARC specification, and publishes them to the DataHub. The API handles authentication using mutual TLS (mTLS), provides structured error reporting, and offers a stable, versioned interface.

This component realises the "ARC-based GitLab infrastructure" described in the middleware roadmap [1] as the central component of the extended middleware. By providing a dedicated API layer, the middleware ensures that data providers do not need to interact directly with the DataHub's GitLab API, which simplifies client development and allows the middleware to enforce validation and quality checks before publication.

#### Conversion Pipeline

The `sql-to-arc` tool implements the conversion from relational database to ARC. Given a configured database connection and the set of SQL views described above, the tool:

1. Streams investigation metadata from the database.
2. For each investigation, fetches the associated studies, assays, contacts, publications, and annotation tables.
3. Constructs a complete ARC object using the `arctrl` library — the Python binding of the DataPLANT ARC tooling ecosystem.
4. Serialises the ARC as RO-Crate JSON-LD.
5. Submits the result to the Advanced Middleware API for validation and publication.

The pipeline is designed for production use with large databases. It employs asynchronous I/O for database and network operations, parallel processing for the CPU-intensive ARC construction step, and flow control mechanisms to maintain a constant memory footprint regardless of database size. Per-investigation error handling ensures that a failure for one dataset does not abort the processing of the remaining datasets. A structured processing report is generated at the end of each run.

### Application: Edaphobase

To validate the approach, the pipeline has been applied to Edaphobase — a curated research database of soil fauna maintained by the Senckenberg Museum of Natural History Görlitz [9]. Edaphobase contains ecological and taxonomic data on soil organisms, with records spanning decades of research. This data is highly valuable for soil ecology and biodiversity research but was previously accessible only through the Edaphobase web interface.

By creating the required SQL views on the Edaphobase PostgreSQL database, the existing metadata was mapped to the ISA model without modifying the source application. The `sql-to-arc` pipeline then automatically converts and publishes this metadata as ARCs to the DataPLANT DataHub via the Advanced Middleware API. This demonstrates the feasibility of the "push" strategy for automated FAIRification of legacy databases as envisioned in the middleware roadmap.

### Related Work

The challenge of making legacy research data FAIR has prompted the development of various tools and approaches, each addressing different stages of the FAIRification process.

**ISA API** [10] is a comprehensive Python library for creating, editing, parsing, and validating ISA-Tab and ISA-JSON documents. It is the standard tool for programmatic manipulation of ISA metadata and is used by platforms such as MetaboLights and the Galaxy workflow system. However, the ISA API operates on data that is already in ISA format; it does not address the upstream problem of extracting metadata from relational databases.

**arc-to-roc** (`nfdi4plants/arc-to-rocrate`) generates RO-Crate packages from existing ARCs. Like the ISA API, it operates on data that is already in ARC format and thus addresses a different stage of the FAIR data lifecycle.

**ro-crate-py** [7] is a Python library for creating and manipulating RO-Crate objects. It provides a general-purpose API but does not implement the ISA model or the ARC profile, meaning that constructing ARCs from relational data would require substantial custom development for each data source.

**OMERO** [11] and **iRODS** [12] are data management platforms capable of storing and annotating research data, but they do not target the specific task of converting relational database metadata into the ISA/ARC format.

The approach presented here is complementary to these tools. It addresses the gap between legacy relational databases and the ISA/ARC ecosystem — a gap that, to our knowledge, is not covered by existing tools. The view-based adapter pattern ensures that connecting a new database requires domain expertise (creating SQL views) rather than software development, which aligns with the FAIRagro principle of respecting the operational autonomy of RDI operators [1].

| Feature                      | sql-to-arc | ISA API | arc-to-roc | ro-crate-py |
| ---------------------------- | ---------- | ------- | ---------- | ----------- |
| Input: relational database   | ✓          | ✗       | ✗          | ✗           |
| Input: ISA-Tab/JSON          | ✗          | ✓       | ✗          | ✗           |
| Input: ARC                   | ✗          | ✗       | ✓          | ✗           |
| Output: ARC (via middleware) | ✓          | ✗       | ✗          | ✗           |
| Output: RO-Crate             | ✗          | ✗       | ✓          | ✓           |
| Output: ISA-Tab/JSON         | ✗          | ✓       | ✗          | ✗           |
| No-code database adapter     | ✓          | ✗       | ✗          | ✗           |
| Ontology annotation support  | ✓          | ✓       | ✓          | partial     |

### Availability and Requirements

**Project name:** sql-to-arc (m4.2_sql_to_arc)

**Project home page:** https://github.com/fairagro/m4.2_sql_to_arc

**Middleware home page:** https://github.com/fairagro/m4.2_advanced_middleware_api

**Operating system(s):** Platform independent (Linux recommended for production)

**Programming language:** Python 3.12+

**Other requirements:** A target relational database (PostgreSQL, MySQL/MariaDB, MSSQL, or OracleDB) with the required SQL views; a running instance of the FAIRagro Advanced Middleware API

**License:** MIT

**RRID:** [to be assigned]

### Conclusions

In a previous publication, García Brizuela et al. [1] presented the roadmap for the FAIRagro middleware — a federated architecture for connecting heterogeneous research data infrastructures in the agrosystems science community. That roadmap identified two phases: a basic middleware for metadata harvesting and an extended middleware for transforming legacy data into FAIR Digital Objects.

The work presented here advances the FAIRagro middleware from roadmap to operational system. With `sql-to-arc` and the Advanced Middleware API, we have realised the core of the extended middleware concept: an automated pipeline that converts metadata from legacy relational databases into Annotated Research Contexts and publishes them to the DataPLANT DataHub. The system has been validated with the Edaphobase soil fauna database, demonstrating the feasibility of the approach for production-scale FAIRification.

Two design decisions are central to the approach. First, the view-based database adapter separates database-specific mapping logic from the conversion engine, ensuring that new databases can be connected through standard SQL operations rather than custom code. This respects the operational autonomy of RDI operators — a key principle of the FAIRagro federation concept. Second, the middleware API provides a stable, validated gateway to the target repository, decoupling data providers from the specifics of the DataPLANT DataHub.

Future work will focus on three directions: (1) supporting incremental updates so that only new or modified investigations are re-converted, (2) enriching partial ontology annotations using ontology lookup services as part of the semi-automated curation process described in the roadmap, and (3) extending the view schema to support additional ARC features such as workflow descriptions. Additionally, we plan to connect further FAIRagro RDIs using the same view-based adapter pattern, contributing to the step-wise expansion of the federated middleware infrastructure envisioned in the original roadmap.

---

## Declarations

### List of Abbreviations

| Abbreviation | Meaning                                                                       |
| ------------ | ----------------------------------------------------------------------------- |
| AAI          | Authentication and Authorization Infrastructure                               |
| ARC          | Annotated Research Context                                                    |
| ETL          | Extract, Transform, Load                                                      |
| FAIR         | Findable, Accessible, Interoperable, Reusable                                 |
| FDO          | FAIR Digital Object                                                           |
| ISA          | Investigation, Study, Assay                                                   |
| mTLS         | mutual Transport Layer Security                                               |
| NFDI         | Nationale Forschungsdateninfrastruktur (National Research Data Infrastructure) |
| RDI          | Research Data Infrastructure                                                  |
| RO-Crate     | Research Object Crate                                                         |

### Ethical Approval and Consent to Participate

Not applicable.

### Consent for Publication

Not applicable.

### Competing Interests

The author declares no competing interests.

### Funding

This work was funded by the German Research Foundation (DFG) as part of the FAIRagro consortium within the National Research Data Infrastructure (NFDI) programme (grant number 501899475).

### Authors' Contributions

CK designed and implemented the software, wrote the documentation, and drafted the manuscript.

---

## References

[1] García Brizuela, J., Scharfenberg, C., Scheuner, C., Hoedt, F., König, P., Kranz, A., Leidel, A., Martini, D., Schneider, G., Schneider, J., Singson, L. S., von Waldow, H., Wehrmeyer, N., Usadel, B., Lesch, S., Specka, X., Lange, M., & Arend, D. (2024). A roadmap for a middleware as a federation service for integrative data retrieval of agricultural data. *Journal of Integrative Bioinformatics*, 21(3). https://doi.org/10.1515/jib-2024-0027

[2] Godfray, H. C. J., Beddington, J. R., Crute, I. R., Haddad, L., Lawrence, D., Muir, J. F., Pretty, J., Robinson, S., Thomas, S. M., & Toulmin, C. (2010). Food security: the challenge of feeding 9 billion people. *Science*, 327(5967), 812–818. https://doi.org/10.1126/science.1185383

[3] Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., Appleton, G., Axton, M., Baak, A., ... & Mons, B. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data*, 3, 160018. https://doi.org/10.1038/sdata.2016.18

[4] FAIRagro Consortium (2021). FAIRagro – FAIR Research Data Management for Agrosystems Research. https://fairagro.net/

[5] NFDI e. V. (2020). National Research Data Infrastructure. https://www.nfdi.de/

[6] Weil, H. L., Schneider, K., Tschöpe, M., Bauer, J., Maus, O., Frey, K., ... & Usadel, B. (2023). PLANTdataHUB: a collaborative platform for continuous FAIR data sharing in plant research. *The Plant Journal*, 116(4), 974–988. https://doi.org/10.1111/tpj.16474

[7] Soiland-Reyes, S., Sefton, P., Crosas, M., Castro, L. J., Coppens, F., Fernández, J. M., ... & Goble, C. (2022). Packaging research artefacts with RO-Crate. *Data Science*, 5(2), 97–138. https://doi.org/10.3233/DS-210053

[8] Rocca-Serra, P., Brandizi, M., Maguire, E., Sklyar, N., Taylor, C., Begley, K., ... & Sansone, S. A. (2010). ISA software suite: supporting standards-compliant experimental annotation and enabling curation at the community level. *Bioinformatics*, 26(18), 2354–2356. https://doi.org/10.1093/bioinformatics/btq415

[9] ;Most probably use: For Edaphobase — add appropriate reference, e.g. When Edaphobase is published; or the Senckenberg institution reference. [to be added]

[10] Rocca-Serra, P., Sansone, S. A., et al. (2023). ISA API. GitHub. https://github.com/ISA-tools/isa-api

[11] Allan, C., Bhattacharya, S., Bhattacharya, D., Bhattacharya, S., Bhattacharya, S., Bhattacharya, S., ... & Moore, J. (2012). OMERO: flexible, model-driven data management for experimental biology. *Nature Methods*, 9(3), 245–253. https://doi.org/10.1038/nmeth.1896

[12] Rajasekar, A., Moore, R., Hou, C. Y., Lee, C. A., Marciano, R., de Torcy, A., ... & Wan, M. (2010). iRODS primer: integrated rule-oriented data system. *Synthesis Lectures on Information Concepts, Retrieval, and Services*, 2(1), 1–143. https://doi.org/10.2200/S00233ED1V01Y200912ICR012
