# From Roadmap to Reality: Implementing the FAIRagro Extended Middleware for Automated ARC Generation from Heterogeneous Research Data Infrastructures

**Authors:** Carsten Külheim¹

¹ FAIRagro Consortium / [Institution]

**Correspondence:** [email]

**Keywords:** FAIR data, Annotated Research Context, ARC, ISA model, research data management, middleware, agrosystems, NFDI, RO-Crate, federated infrastructure, INSPIRE, CSW

---

## Abstract

**Background:** In a previous publication, García Brizuela et al. [1] presented the FAIRagro middleware roadmap — a federated architecture concept for connecting heterogeneous research data infrastructures (RDIs) in the German agrosystems science community. That roadmap outlined a two-phase approach: a basic middleware for metadata harvesting and an extended middleware capable of transforming legacy research data into FAIR Digital Objects (FDOs) using the Annotated Research Context (ARC) specification. While the basic middleware was operational at the time of publication, the extended middleware remained a conceptual design.

**Findings:** We report the realisation of the extended middleware concept. We have developed and deployed three open-source components: (1) `sql-to-arc`, a conversion tool that extracts metadata from relational databases and transforms it into ARCs using a view-based adapter pattern; (2) `inspire-to-arc`, a harvesting tool that converts geospatial metadata from INSPIRE-compliant CSW (Catalogue Service for the Web) endpoints into ARCs; and (3) the FAIRagro Advanced Middleware API, a gateway service that validates and publishes ARCs to the DataPLANT DataHub. The system has been applied to two RDIs: the Edaphobase soil fauna database (via `sql-to-arc`) and the BonaRes soil and agricultural research data repository (via `inspire-to-arc`).

**Conclusions:** The work presented here advances the FAIRagro middleware from its initial roadmap phase into an operational system. The two conversion clients demonstrate that the middleware architecture supports heterogeneous data sources — from relational databases to standardised geospatial catalogue services — while the common middleware API decouples data providers from the specifics of the target FAIR data repository. Together, these components address a key gap identified in the roadmap: the automated, scalable conversion of legacy research data metadata into standardised FAIR Digital Objects.

---

## Findings

### Background and Motivation

#### The FAIRagro Middleware Roadmap

Agriculture faces pressing challenges including climate change, biodiversity loss and stagnating productivity [2]. The massive increase in recorded measurement data, combined with advances in digital technologies, offers the potential to address these challenges — but only if the underlying data is carefully integrated and made accessible according to the FAIR principles (Findable, Accessible, Interoperable, Reusable) [3]. The German National Research Data Infrastructure (NFDI) consortium FAIRagro was established to develop FAIR-compliant infrastructure services for the agrosystems science community [4, 5].

A central challenge for FAIRagro is the federation of more than a dozen research data infrastructures (RDIs) that span different disciplines (soil science, plant science, forestry, ecology, agronomy), are maintained by different institutions, and are built on diverse technology stacks [1]. To connect these autonomous RDIs without interfering with their operational and organisational independence, FAIRagro adopted a federated middleware architecture.

García Brizuela et al. [1] described the design process and resulting architecture concept for this middleware. The approach was structured into two phases:

1. **Basic middleware:** A lightweight metadata harvesting service that crawls JSON-LD metadata from RDI landing pages and aggregates it for downstream services, such as the FAIRagro Search and Inventory Portal and the Scientific Workflow Infrastructure (SciWIn). This phase was already operational at the time of the roadmap publication.

2. **Extended middleware:** A more comprehensive system designed to go beyond metadata harvesting and enable the transformation of actual research data and rich metadata into FAIR Digital Objects (FDOs). The roadmap proposed adopting the Annotated Research Context (ARC) specification and the associated tooling ecosystem developed by the NFDI consortium DataPLANT (NFDI4Plants) [6]. The extended middleware was envisioned to support both a "push" strategy — where RDIs actively construct and submit ARCs — and a "pull" strategy — where the middleware retrieves datasets and transforms them into ARCs in a semi-automated process.

The present paper reports on the realisation of the extended middleware concept. We describe two conversion clients that implement both strategies: `sql-to-arc` follows the "push" approach, where the RDI actively constructs ARCs from its relational database and submits them to the middleware; `inspire-to-arc` follows the "pull" approach, where the middleware harvests metadata from INSPIRE-compliant geospatial catalogue services and transforms it into ARCs.

#### The Annotated Research Context (ARC)

The Annotated Research Context (ARC) is a FAIR Digital Object standard developed by the DataPLANT consortium [6]. An ARC is a structured, self-describing data container based on the RO-Crate specification [7] and the ISA (Investigation, Study, Assay) metadata framework [8]. It bundles all artefacts of a research project — raw data, processed data, workflows, and metadata — into a single, versioned, and citable package.

The ISA model at the heart of the ARC provides a three-level hierarchy for describing experimental research:

- An **Investigation** represents the top-level research context, capturing the overall aim, contributors, publications, and high-level metadata of a research programme.
- A **Study** describes a focused experiment or a specific part of the investigation, including the subjects of research, experimental design, and conditions.
- An **Assay** describes the analytical measurements or data-generating activities within a study, documenting protocols, technologies, and measured variables.

A distinctive feature of the ARC is its use of **annotation tables** — structured, spreadsheet-like tables in which every column is typed and, where applicable, linked to an ontology term. This mechanism allows experimental and measurement processes to be represented as a **provenance graph**, enabling machine-readable and semantically interoperable descriptions of complex experimental workflows.

The choice of ARC as the FDO format for the extended middleware was motivated by several factors identified in the roadmap [1]: the flexibility of the ISA model for representing heterogeneous agrosystems data, the scalable storage backend provided by GitLab, the availability of mature tooling from the DataPLANT ecosystem, and the compatibility of ARCs with the RO-Crate standard required by the downstream SciWIn infrastructure.

### Approach

The core challenge addressed in this work is the automated transformation of metadata from heterogeneous research data infrastructures into ARCs. The middleware roadmap [1] envisioned two complementary strategies: a "push" strategy, where RDIs actively construct ARCs and submit them to the middleware, and a "pull" strategy, where the middleware retrieves and converts data from external sources. We have implemented both: `sql-to-arc` realises the push strategy for relational databases, while `inspire-to-arc` realises the pull strategy for INSPIRE-compliant catalogue services.

Our approach rests on two principles:

1. **Source-specific conversion clients:** Each type of data source is served by a dedicated conversion client that handles the extraction and mapping of metadata to the ISA model. We have developed two such clients: `sql-to-arc` for relational databases (using a view-based adapter pattern) and `inspire-to-arc` for INSPIRE-compliant geospatial catalogue services (using the CSW protocol). This separation allows each client to be optimised for its specific data source while sharing the common ARC construction and publication logic.

2. **Decoupled middleware API:** The conversion clients do not interact directly with the target ARC repository (the DataPLANT DataHub). Instead, they submit completed ARCs to a dedicated middleware API that handles validation, authentication, and publication. This decoupling provides a stable interface for all conversion clients and shields them from changes in the target repository's API.

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

#### The INSPIRE-to-ARC Converter

While `sql-to-arc` addresses RDIs backed by relational databases, many research data infrastructures in the agrosystems domain — particularly those dealing with geospatial and environmental data — expose their metadata through INSPIRE-compliant catalogue services [11]. INSPIRE (Infrastructure for Spatial Information in the European Community) is the EU directive that establishes a standardised spatial data infrastructure across Europe, and many German RDIs in the agricultural and environmental domain provide CSW (Catalogue Service for the Web) endpoints that serve ISO 19139-encoded metadata.

The `inspire-to-arc` tool harvests metadata from such CSW endpoints and converts it into ARCs. This presents a different mapping challenge than the SQL-based approach: INSPIRE metadata describes *datasets and their provenance* (spatial extent, temporal coverage, data quality, lineage), while the ISA model describes *research processes* (investigations, studies, assays). The converter addresses this conceptual gap by mapping INSPIRE metadata to a protocol-based ARC structure:

- The dataset's overall context (title, abstract, contacts, identifiers) maps to an **Investigation**.
- The data creation workflow — reconstructed from lineage statements, spatial sampling, data acquisition, and processing steps — maps to a **Study** with ordered protocols.
- The measurement outputs and technology descriptions map to an **Assay**.

Like `sql-to-arc`, the converter submits completed ARCs to the Advanced Middleware API. Both tools share common infrastructure components (the `api_client` library for middleware communication, and `shared` models for configuration).

#### Conversion Pipelines

Both conversion clients follow the same high-level pipeline pattern:

1. **Extract** metadata from the source (SQL views for `sql-to-arc`; CSW queries for `inspire-to-arc`).
2. **Map** the extracted metadata to the ISA model.
3. **Construct** a complete ARC object using the `arctrl` library — the Python binding of the DataPLANT ARC tooling ecosystem.
4. **Serialise** the ARC as RO-Crate JSON-LD.
5. **Submit** the result to the Advanced Middleware API for validation and publication.

Both pipelines are designed for production use with large numbers of datasets. They employ asynchronous I/O for network operations, parallel processing for the CPU-intensive ARC construction step, and flow control mechanisms to maintain a constant memory footprint. Per-dataset error handling ensures that a failure for one investigation does not abort the processing of the remaining datasets. A structured processing report is generated at the end of each run.

### Applications

To validate the approach, the conversion clients have been applied to two FAIRagro research data infrastructures with fundamentally different characteristics.

#### Edaphobase (via sql-to-arc)

Edaphobase is a curated research database of soil fauna maintained by the Senckenberg Museum of Natural History Görlitz [9]. It contains ecological and taxonomic data on soil organisms, with records spanning decades of research. This data is highly valuable for soil ecology and biodiversity research but was previously accessible only through the Edaphobase web interface and its underlying PostgreSQL database.

By creating the required SQL views on the Edaphobase database, the existing metadata was mapped to the ISA model without modifying the source application. The `sql-to-arc` pipeline then automatically converts and publishes this metadata as ARCs to the DataPLANT DataHub via the Advanced Middleware API.

#### BonaRes (via inspire-to-arc)

The BonaRes repository [10] is a research data infrastructure for soil and agricultural science, providing access to a large collection of datasets with rich geospatial metadata. BonaRes exposes its metadata through an INSPIRE-compliant CSW endpoint, making it accessible via standardised geospatial catalogue protocols.

The `inspire-to-arc` tool harvests metadata from the BonaRes CSW endpoint and converts it into ARCs. This demonstrates that the middleware architecture is not limited to relational database sources but can accommodate any RDI that exposes metadata through standardised interfaces.

Taken together, these two applications validate the extensibility of the extended middleware concept: heterogeneous data sources can be connected through dedicated conversion clients that share the common middleware API as their publication gateway.

### Related Work

The challenge of making legacy research data FAIR has prompted the development of various tools and approaches, each addressing different stages of the FAIRification process.

**ISA API** [12] is a comprehensive Python library for creating, editing, parsing, and validating ISA-Tab and ISA-JSON documents. It is the standard tool for programmatic manipulation of ISA metadata and is used by platforms such as MetaboLights and the Galaxy workflow system. However, the ISA API operates on data that is already in ISA format; it does not address the upstream problem of extracting metadata from relational databases.

**arc-to-roc** (`nfdi4plants/arc-to-rocrate`) generates RO-Crate packages from existing ARCs. Like the ISA API, it operates on data that is already in ARC format and thus addresses a different stage of the FAIR data lifecycle.

**ro-crate-py** [7] is a Python library for creating and manipulating RO-Crate objects. It provides a general-purpose API but does not implement the ISA model or the ARC profile, meaning that constructing ARCs from relational data would require substantial custom development for each data source.

**OMERO** [13] and **iRODS** [14] are data management platforms capable of storing and annotating research data, but they do not target the specific task of converting relational database metadata into the ISA/ARC format.

The approach presented here is complementary to these tools. It addresses the gap between heterogeneous legacy data sources and the ISA/ARC ecosystem — a gap that, to our knowledge, is not covered by existing tools. The view-based adapter pattern of `sql-to-arc` ensures that connecting a new database requires domain expertise (creating SQL views) rather than software development, while `inspire-to-arc` leverages existing standardised interfaces (CSW). Both approaches align with the FAIRagro principle of respecting the operational autonomy of RDI operators [1].

| Feature                        | sql-to-arc | inspire-to-arc | ISA API | arc-to-roc | ro-crate-py |
| ------------------------------ | ---------- | -------------- | ------- | ---------- | ----------- |
| Input: relational database     | ✓          | ✗              | ✗       | ✗          | ✗           |
| Input: INSPIRE/CSW endpoint    | ✗          | ✓              | ✗       | ✗          | ✗           |
| Input: ISA-Tab/JSON            | ✗          | ✗              | ✓       | ✗          | ✗           |
| Input: ARC                     | ✗          | ✗              | ✗       | ✓          | ✗           |
| Output: ARC (via middleware)   | ✓          | ✓              | ✗       | ✗          | ✗           |
| Output: RO-Crate               | ✗          | ✗              | ✗       | ✓          | ✓           |
| Output: ISA-Tab/JSON           | ✗          | ✗              | ✓       | ✗          | ✗           |
| No-code database adapter       | ✓          | n/a            | ✗       | ✗          | ✗           |
| Ontology annotation support    | ✓          | ✓              | ✓       | ✓          | partial     |

### Availability and Requirements

**Project name:** sql-to-arc (m4.2_sql_to_arc)

**Project home page:** https://github.com/fairagro/m4.2_sql_to_arc

**Project name:** inspire-to-arc (m4.2_inspire_to_arc)

**Project home page:** https://github.com/fairagro/m4.2_inspire_to_arc

**Middleware home page:** https://github.com/fairagro/m4.2_advanced_middleware_api

**Operating system(s):** Platform independent (Linux recommended for production)

**Programming language:** Python 3.12+

**Other requirements for sql-to-arc:** A target relational database (PostgreSQL, MySQL/MariaDB, MSSQL, or OracleDB) with the required SQL views; a running instance of the FAIRagro Advanced Middleware API

**Other requirements for inspire-to-arc:** An INSPIRE-compliant CSW endpoint; a running instance of the FAIRagro Advanced Middleware API

**License:** MIT

**RRID:** [to be assigned]

### Conclusions

In a previous publication, García Brizuela et al. [1] presented the roadmap for the FAIRagro middleware — a federated architecture for connecting heterogeneous research data infrastructures in the agrosystems science community. That roadmap identified two phases: a basic middleware for metadata harvesting and an extended middleware for transforming legacy data into FAIR Digital Objects.

The work presented here advances the FAIRagro middleware from roadmap to operational system. With `sql-to-arc`, `inspire-to-arc`, and the Advanced Middleware API, we have realised the core of the extended middleware concept: automated pipelines that convert metadata from heterogeneous data sources into Annotated Research Contexts and publish them to the DataPLANT DataHub. The system has been validated with two FAIRagro RDIs — Edaphobase (relational database) and BonaRes (INSPIRE/CSW catalogue) — demonstrating the feasibility and extensibility of the approach.

The architecture follows a client–gateway pattern: source-specific conversion clients handle the extraction and mapping of metadata from different types of data sources, while the common Advanced Middleware API provides a stable, validated gateway to the target repository. This design allows the middleware to accommodate new types of data sources by developing additional conversion clients, without changes to the gateway or the target repository. The view-based adapter pattern of `sql-to-arc` further lowers the barrier for relational databases by requiring only SQL view creation rather than custom code — respecting the operational autonomy of RDI operators, a key principle of the FAIRagro federation concept.

Future work will focus on three directions: (1) supporting incremental updates so that only new or modified investigations are re-converted, (2) enriching partial ontology annotations using ontology lookup services as part of the semi-automated curation process described in the roadmap, and (3) developing additional conversion clients for further RDI types. Additionally, we plan to connect further FAIRagro RDIs — both via existing clients and new ones — contributing to the step-wise expansion of the federated middleware infrastructure envisioned in the original roadmap.

---

## Declarations

### List of Abbreviations

| Abbreviation | Meaning                                                                       |
| ------------ | ----------------------------------------------------------------------------- |
| AAI          | Authentication and Authorization Infrastructure                               |
| ARC          | Annotated Research Context                                                    |
| CSW          | Catalogue Service for the Web                                                 |
| ETL          | Extract, Transform, Load                                                      |
| FAIR         | Findable, Accessible, Interoperable, Reusable                                 |
| FDO          | FAIR Digital Object                                                           |
| INSPIRE      | Infrastructure for Spatial Information in the European Community               |
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

[9] [Edaphobase reference — to be added]

[10] BonaRes Centre for Soil and Agricultural Research (2024). BonaRes Repository. https://www.bonares.de/

[11] European Parliament and Council (2007). Directive 2007/2/EC establishing an Infrastructure for Spatial Information in the European Community (INSPIRE). *Official Journal of the European Union*, L 108, 1–14.

[12] Rocca-Serra, P., Sansone, S. A., et al. (2023). ISA API. GitHub. https://github.com/ISA-tools/isa-api

[13] Allan, C., Bhattacharya, S., Bhattacharya, D., Bhattacharya, S., Bhattacharya, S., Bhattacharya, S., ... & Moore, J. (2012). OMERO: flexible, model-driven data management for experimental biology. *Nature Methods*, 9(3), 245–253. https://doi.org/10.1038/nmeth.1896

[14] Rajasekar, A., Moore, R., Hou, C. Y., Lee, C. A., Marciano, R., de Torcy, A., ... & Wan, M. (2010). iRODS primer: integrated rule-oriented data system. *Synthesis Lectures on Information Concepts, Retrieval, and Services*, 2(1), 1–143. https://doi.org/10.2200/S00233ED1V01Y200912ICR012
