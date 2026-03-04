# From Roadmap to Reality: Implementing the FAIRagro Federated RDI Network for Automated ARC Generation from Heterogeneous Research Data Infrastructures

**Authors:** Carsten Külheim¹

¹ FAIRagro Consortium / [Institution]

**Correspondence:** [email]

**Keywords:** FAIR data, Annotated Research Context, ARC, ISA model, research data management, federated RDI network, middleware, agrosystems, NFDI, RO-Crate, federated infrastructure, INSPIRE, CSW

---

## Abstract

**Background:** In a previous publication, García Brizuela et al. [1] presented the roadmap for the FAIRagro Federated RDI Network (formerly referred to as the FAIRagro middleware) — a federated architecture concept for connecting heterogeneous research data infrastructures (RDIs) in the German agrosystems science community. That roadmap outlined a two-phase approach: a basic component for metadata harvesting and an extended component capable of transforming legacy research data into FAIR Digital Objects (FDOs) using the Annotated Research Context (ARC) specification. While the basic component was operational at the time of publication, the extended component remained a conceptual design.

**Findings:** We report the realisation of the FAIRagro Federated RDI Network. We have developed and deployed three open-source components: (1) `sql-to-arc`, a conversion tool that extracts metadata from relational databases and transforms it into ARCs using a view-based adapter pattern; (2) `inspire-to-arc`, a harvesting tool that converts geospatial metadata from INSPIRE-compliant CSW (Catalogue Service for the Web) endpoints into ARCs; and (3) the FAIRagro Advanced Middleware API, a gateway service that validates and publishes ARCs to the DataPLANT DataHub. The system has been applied to two RDIs: the Edaphobase soil fauna database (via `sql-to-arc`) and the BonaRes soil and agricultural research data repository (via `inspire-to-arc`).

**Conclusions:** The work presented here advances the FAIRagro Federated RDI Network from its initial roadmap phase into an operational system. The two conversion clients demonstrate that the network architecture supports heterogeneous data sources — from relational databases to standardised geospatial catalogue services — while the common gateway API decouples data providers from the specifics of the target FAIR data repository. Together, these components address a key gap identified in the roadmap: the automated, scalable conversion of legacy research data metadata into standardised FAIR Digital Objects.

---

## Findings

### Background and Motivation

#### The FAIRagro Federated RDI Network Roadmap

Agriculture faces pressing challenges including climate change, biodiversity loss and stagnating productivity [2]. The massive increase in recorded measurement data, combined with advances in digital technologies, offers the potential to address these challenges — but only if the underlying data is carefully integrated and made accessible according to the FAIR principles (Findable, Accessible, Interoperable, Reusable) [3]. The German National Research Data Infrastructure (NFDI) consortium FAIRagro was established to develop FAIR-compliant infrastructure services for the agrosystems science community [4, 5].

A central challenge for FAIRagro is the federation of more than a dozen research data infrastructures (RDIs) that span different disciplines (soil science, plant science, forestry, ecology, agronomy), are maintained by different institutions, and are built on diverse technology stacks [1]. To connect these autonomous RDIs without interfering with their operational and organisational independence, FAIRagro adopted a federated network architecture.

García Brizuela et al. [1] described the design process and resulting architecture concept for this network. The approach was structured into two phases:

1. **Basic component:** A lightweight metadata harvesting service that crawls JSON-LD metadata from RDI landing pages and aggregates it for downstream services. The primary consumers of this component are the FAIRagro Search Hub, a Dataverse-based discovery portal that provides unified search and faceted browsing across all federated RDIs, and the Scientific Workflow Infrastructure SciWIn [26], a platform for creating, executing, and publishing reproducible computational workflows based on FAIR Digital Objects. In addition, the FAIRagro Use Cases — interdisciplinary research scenarios addressing concrete agrosystems science questions — were defined as consumers of the network during the requirements analysis process [1]. This phase was already operational at the time of the roadmap publication.

2. **Extended component (FAIRagro Federated RDI Network):** A more comprehensive system designed to go beyond metadata harvesting and enable the transformation of actual research data and rich metadata into FAIR Digital Objects (FDOs). The roadmap proposed adopting the Annotated Research Context (ARC) specification and the associated tooling ecosystem developed by the NFDI consortium DataPLANT (NFDI4Plants) [6]. This component was envisioned to support both a "push" strategy — where RDIs actively construct and submit ARCs — and a "pull" strategy — where the network retrieves datasets and transforms them into ARCs in a semi-automated process.

The present paper reports on the realisation of the FAIRagro Federated RDI Network. We describe two conversion clients that implement both strategies: `sql-to-arc` follows the "push" approach, where the RDI actively constructs ARCs from its relational database and submits them to the network gateway; `inspire-to-arc` follows the "pull" approach, where the network harvests metadata from INSPIRE-compliant geospatial catalogue services and transforms it into ARCs.

#### The Annotated Research Context (ARC)

The Annotated Research Context (ARC) is a FAIR Digital Object standard developed by the DataPLANT consortium [6]. An ARC is a structured, self-describing data container based on the RO-Crate specification [7] and the ISA (Investigation, Study, Assay) metadata framework [8]. It bundles all artefacts of a research project — raw data, processed data, workflows, and metadata — into a single, versioned, and citable package.

The ISA model at the heart of the ARC provides a three-level hierarchy for describing experimental research:

- An **Investigation** represents the top-level research context, capturing the overall aim, contributors, publications, and high-level metadata of a research programme.
- A **Study** describes a focused experiment or a specific part of the investigation, including the subjects of research, experimental design, and conditions.
- An **Assay** describes the analytical measurements or data-generating activities within a study, documenting protocols, technologies, and measured variables.

A distinctive feature of the ARC is its use of **annotation tables** — structured, spreadsheet-like tables in which every column is typed and, where applicable, linked to an ontology term. This mechanism allows experimental and measurement processes to be represented as a **provenance graph**, enabling machine-readable and semantically interoperable descriptions of complex experimental workflows.

The choice of ARC as the FDO format for the FAIRagro Federated RDI Network was motivated by several factors identified in the roadmap [1]: the flexibility of the ISA model for representing heterogeneous agrosystems data, the scalable storage backend provided by GitLab, the availability of mature tooling from the DataPLANT ecosystem, and the compatibility of ARCs with the RO-Crate standard required by the downstream SciWIn infrastructure.

### Approach

The core challenge addressed in this work is the automated transformation of metadata from heterogeneous research data infrastructures into ARCs. The roadmap [1] envisioned two complementary strategies: a "push" strategy, where RDIs actively construct ARCs and submit them to the network gateway, and a "pull" strategy, where the network retrieves and converts data from external sources. We have implemented both: `sql-to-arc` realises the push strategy for relational databases, while `inspire-to-arc` realises the pull strategy for INSPIRE-compliant catalogue services.

Our approach rests on two principles:

1. **Source-specific conversion clients:** Each type of data source is served by a dedicated conversion client that handles the extraction and mapping of metadata to the ISA model. We have developed two such clients: `sql-to-arc` for relational databases (using a view-based adapter pattern) and `inspire-to-arc` for INSPIRE-compliant geospatial catalogue services (using the CSW protocol). This separation allows each client to be optimised for its specific data source while sharing the common ARC construction and publication logic.

2. **Decoupled gateway API:** The conversion clients do not interact directly with the target ARC repository (the DataPLANT DataHub). Instead, they submit completed ARCs to a dedicated gateway API that handles validation, authentication, and publication. This decoupling provides a stable interface for all conversion clients and shields them from changes in the target repository's API.

#### The View-Based Database Adapter

The view-based adapter is the central abstraction for connecting a relational database to the FAIRagro Federated RDI Network pipeline. To integrate a new data source, a database administrator creates a small set of SQL views that expose the database's metadata in a standardised column layout. No changes to the source application or its data model are required — the views are read-only projections of existing data.

The required views follow the ISA hierarchy:

- `vInvestigation`: one row per investigation (dataset), with identifier, title, description, and optional dates.
- `vStudy`: one row per study, linked to an investigation via a foreign key.
- `vAssay`: one row per assay, linked to an investigation and optionally to studies.
- `vContact`: one row per person associated with an investigation, study, or assay, with optional ontology-annotated roles.
- `vPublication`: one row per publication associated with an investigation or study, including DOI, PubMed ID, and ontology-annotated publication status.
- `vAnnotationTable`: one row per annotation table cell, encoding the column type, ontology annotation, and cell value in a flat representation.

Ontology annotations are represented through three fields: a human-readable term name, a term accession URI, and an optional ontology version. This design allows database owners to provide partial ontology information that can be enriched in subsequent curation steps — consistent with the semi-automated curation process foreseen in the roadmap [1].

The view schema is compatible with all major relational database systems (PostgreSQL, MySQL/MariaDB, MSSQL, OracleDB). Views may be empty if the corresponding data is not available; the pipeline handles missing data gracefully. This low-friction integration mechanism is central to the scalability of the approach: connecting a new RDI requires only standard database operations, not software development.

#### The FAIRagro Advanced Middleware API

The FAIRagro Advanced Middleware API is the gateway between data conversion clients and the DataPLANT DataHub. It accepts ARC objects serialised as RO-Crate JSON-LD via a REST API, validates them against the ARC specification, and publishes them to the DataHub. The API handles authentication using mutual TLS (mTLS), provides structured error reporting, and offers a stable, versioned interface.

This component realises the "ARC-based GitLab infrastructure" described in the roadmap [1] as the central gateway of the FAIRagro Federated RDI Network. By providing a dedicated API layer, the network ensures that data providers do not need to interact directly with the DataHub's GitLab API, which simplifies client development and allows the network to enforce validation and quality checks before publication.

#### The INSPIRE-to-ARC Converter

While `sql-to-arc` addresses RDIs backed by relational databases, many research data infrastructures in the agrosystems domain — particularly those dealing with geospatial and environmental data — expose their metadata through INSPIRE-compliant catalogue services [11]. INSPIRE (Infrastructure for Spatial Information in the European Community) is the EU directive that establishes a standardised spatial data infrastructure across Europe, and many German RDIs in the agricultural and environmental domain provide CSW (Catalogue Service for the Web) endpoints that serve ISO 19139-encoded metadata.

The `inspire-to-arc` tool harvests metadata from such CSW endpoints and converts it into ARCs. This presents a different mapping challenge than the SQL-based approach: INSPIRE metadata describes *datasets and their provenance* (spatial extent, temporal coverage, data quality, lineage), while the ISA model describes *research processes* (investigations, studies, assays). The converter addresses this conceptual gap by mapping INSPIRE metadata to a protocol-based ARC structure:

- The dataset's overall context (title, abstract, contacts, identifiers) maps to an **Investigation**.
- The data creation workflow — reconstructed from lineage statements, spatial sampling, data acquisition, and processing steps — maps to a **Study** with ordered protocols.
- The measurement outputs and technology descriptions map to an **Assay**.

Like `sql-to-arc`, the converter submits completed ARCs to the Advanced Middleware API. Both tools share common infrastructure components (the `api_client` library for network communication, and `shared` models for configuration).

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

The `inspire-to-arc` tool harvests metadata from the BonaRes CSW endpoint and converts it into ARCs. This demonstrates that the FAIRagro Federated RDI Network is not limited to relational database sources but can accommodate any RDI that exposes metadata through standardised interfaces.

Taken together, these two applications validate the extensibility of the FAIRagro Federated RDI Network: heterogeneous data sources can be connected through dedicated conversion clients that share the common Advanced Middleware API as their publication gateway.

#### Downstream Consumers of the FAIRagro Federated RDI Network

The FAIRagro Federated RDI Network does not operate in isolation but serves as a data integration layer for several downstream FAIRagro services.

The **FAIRagro Search Hub** (formerly Search and Inventory Portal) is a Dataverse-based discovery service that presents the harvested and transformed metadata to researchers through unified search and faceted browsing. The basic component feeds JSON-LD metadata into the Search Hub, while the FAIRagro Federated RDI Network — through the ARC objects published to the DataPLANT DataHub — enriches the available metadata with semantically structured ISA descriptions. The Search Hub thus acts as the primary user-facing entry point for discovering datasets across all federated RDIs.

**SciWIn** [26] (Scientific Workflow Infrastructure) is a platform developed within FAIRagro for managing reproducible computational workflows. SciWIn operates on FAIR Digital Objects — specifically RO-Crates — to represent data and code artefacts along with their provenance information. The ARCs generated by the FAIRagro Federated RDI Network are directly compatible with SciWIn's FDO-based processing model, since ARCs are themselves RO-Crates enriched with ISA metadata. This compatibility was a key consideration in the choice of the ARC specification as the target format [1].

Finally, the **FAIRagro Use Cases** were defined as part of the consortium's requirements analysis process [1]. These use cases represent interdisciplinary research scenarios — spanning soil science, plant phenotyping, landscape ecology, and agricultural systems analysis — that require integrated access to data from multiple FAIRagro RDIs. The use cases served as the primary driver for the network's requirements, particularly the need for cross-RDI metadata exchange and access to semantically enriched datasets. While the use cases are not yet actively consuming data from the FAIRagro Federated RDI Network at the time of writing, the infrastructure has been designed to serve their needs as the FAIRagro federation matures.

### Related Work

The challenge of federating heterogeneous research data infrastructures under a unified interface has been addressed by numerous initiatives, both within the agrosystems domain and in the broader life sciences. In the following, we distinguish between *federation and discovery platforms* that aggregate metadata from multiple sources and *data transformation tools* that convert data into specific formats. The FAIRagro Federated RDI Network combines aspects of both: it federates data from heterogeneous RDIs and transforms it into a standardised FAIR Digital Object format (ARC).

#### Federated Data Infrastructures and Discovery Platforms

Several large-scale initiatives aim to provide unified access to distributed research data, differing in their scope, federation strategy, and the depth of data integration they achieve.

**GARDIAN** [18] (Global Agricultural Research Data Innovation and Acceleration Network) is the data discovery platform of the CGIAR system. It harvests metadata from institutional repositories of CGIAR centres worldwide, harmonises it against a common metadata schema, and provides a unified search interface. GARDIAN focuses on metadata discovery and linking; it does not transform the underlying data into a common format or construct standardised data objects.

**AgReFed** [19] (Agricultural Research Federation) is an Australian initiative that provides FAIR guidelines, assessment tools, and minimum metadata standards for agricultural research data. AgReFed focuses on policy, governance, and FAIR assessment rather than on building infrastructure for automated data transformation. It offers guidance on making datasets FAIR but does not operate a middleware that transforms data between formats.

**GFBio** [20] (German Federation for Biological Data) is a national data infrastructure for biological and environmental research in Germany, now closely associated with the NFDI consortium NFDI4Biodiversity. GFBio provides a submission portal that mediates data archiving across a network of specialised data centres. While GFBio supports the full data lifecycle, its federation model relies on a central submission workflow rather than on automated transformation of legacy database metadata into a common FDO format.

In the broader life sciences, **NCBI Entrez** [21] provides a global query system that searches across more than 20 interconnected biological databases (PubMed, GenBank, Protein, Structure, Gene, and others) through a single interface. Entrez uses precomputed cross-references and the E-utilities API for programmatic access. However, Entrez is a centralised search and retrieval system operated by a single institution (NCBI); it does not address the challenge of federating autonomous, independently operated RDIs or transforming their data into a common format.

**EMBL-EBI** [22] hosts one of the world's most comprehensive collections of freely available molecular data and provides API-driven access through services such as EBI Search. Like NCBI, EMBL-EBI follows a centralised model: data is ingested into institutional databases and made available through institutional APIs and search interfaces.

**ELIXIR** [23] is a distributed European infrastructure for life science data that connects national bioinformatics nodes across 22 member countries. ELIXIR's Interoperability Platform promotes FAIR data standards and curates Recommended Interoperability Resources (RIRs). ELIXIR's federation model is closest to the FAIRagro approach: it connects autonomous nodes while respecting their independence. However, ELIXIR focuses primarily on coordination, standards, and interoperability policies rather than on automated data transformation pipelines.

**BASE** [24] (Bielefeld Academic Search Engine), operated by Bielefeld University Library, is one of the world's largest search engines for academic web resources. BASE harvests OAI-PMH metadata from over 10,000 content providers worldwide and indexes more than 300 million documents. Like GARDIAN, BASE is a metadata discovery platform; it aggregates and indexes existing metadata but does not transform the underlying data.

**OpenAIRE** [25] provides infrastructure for the European Open Science Cloud (EOSC), aggregating metadata from repositories across Europe and offering discovery, monitoring, and reporting services. OpenAIRE defines interoperability guidelines for data providers but, like the other discovery platforms, operates at the metadata aggregation level rather than transforming data into standardised research objects.

A common pattern across these platforms is that federation is typically achieved through *metadata harvesting and indexing* — the platforms discover and aggregate metadata but leave the underlying data in its original format and location. The FAIRagro Federated RDI Network goes further: it not only extracts metadata from heterogeneous sources but transforms it into a standardised FAIR Digital Object (ARC) and publishes it to a common repository, thereby achieving a deeper level of data integration.

#### Data Transformation and FAIRification Tools

At the tool level, several projects address specific stages of the FAIRification process.

**ISA API** [12] is a comprehensive Python library for creating, editing, parsing, and validating ISA-Tab and ISA-JSON documents. It is the standard tool for programmatic manipulation of ISA metadata and is used by platforms such as MetaboLights and the Galaxy workflow system. However, the ISA API operates on data that is already in ISA format; it does not address the upstream problem of extracting metadata from legacy data sources.

**arc-to-roc** (`nfdi4plants/arc-to-rocrate`) generates RO-Crate packages from existing ARCs. Like the ISA API, it operates on data that is already in ARC format and thus addresses a different stage of the FAIR data lifecycle.

**ro-crate-py** [7] is a Python library for creating and manipulating RO-Crate objects. It provides a general-purpose API but does not implement the ISA model or the ARC profile, meaning that constructing ARCs from heterogeneous legacy sources would require substantial custom development for each data source.

#### Positioning of the FAIRagro Federated RDI Network

The approach presented here occupies a distinct position: it combines *federation* (connecting autonomous, heterogeneous RDIs) with *automated data transformation* (converting metadata into a standardised FDO format). While discovery platforms like GARDIAN, BASE, and OpenAIRE aggregate metadata for search and reuse, the FAIRagro Federated RDI Network actively transforms legacy metadata into semantically rich, self-describing ARC objects and publishes them to a common repository. This deeper integration goes beyond what metadata harvesting alone can achieve, while the client–gateway architecture — with source-specific conversion clients and a common gateway API — mirrors the federated, autonomy-preserving design principles seen in ELIXIR.

| Aspect                             | FAIRagro Fed. RDI Network | GARDIAN             | NCBI Entrez     | ELIXIR        | BASE / OpenAIRE   |
| ---------------------------------- | ------------------------- | ------------------- | --------------- | ------------- | ----------------- |
| Domain                             | Agrosystems               | Agriculture (CGIAR) | Life sciences   | Life sciences | Multidisciplinary |
| Federation of autonomous RDIs      | ✓                         | ✓                   | ✗ (centralised) | ✓             | ✓                 |
| Metadata harvesting                | ✓ (basic component)       | ✓                   | ✗               | ✓             | ✓                 |
| Data transformation to common FDO  | ✓ (extended component)    | ✗                   | ✗               | ✗             | ✗                 |
| Standardised output format (ARC)   | ✓                         | ✗                   | ✗               | ✗             | ✗                 |
| Push and pull strategies           | ✓                         | pull only           | n/a             | n/a           | pull only         |
| Source-specific conversion clients | ✓                         | ✗                   | ✗               | ✗             | ✗                 |

### Availability and Requirements

**Project name:** sql-to-arc (m4.2_sql_to_arc)

**Project home page:** <https://github.com/fairagro/m4.2_sql_to_arc>

**Project name:** inspire-to-arc (m4.2_inspire_to_arc)

**Project home page:** <https://github.com/fairagro/m4.2_inspire_to_arc>

**Middleware home page:** <https://github.com/fairagro/m4.2_advanced_middleware_api>

**Operating system(s):** Platform independent (Linux recommended for production)

**Programming language:** Python 3.12+

**Other requirements for sql-to-arc:** A target relational database (PostgreSQL, MySQL/MariaDB, MSSQL, or OracleDB) with the required SQL views; a running instance of the FAIRagro Advanced Middleware API

**Other requirements for inspire-to-arc:** An INSPIRE-compliant CSW endpoint; a running instance of the FAIRagro Advanced Middleware API

**License:** MIT

**RRID:** [to be assigned]

### Conclusions

In a previous publication, García Brizuela et al. [1] presented the roadmap for the FAIRagro Federated RDI Network (then referred to as the FAIRagro middleware) — a federated architecture for connecting heterogeneous research data infrastructures in the agrosystems science community. That roadmap identified two phases: a basic component for metadata harvesting and an extended component for transforming legacy data into FAIR Digital Objects.

The work presented here advances the FAIRagro Federated RDI Network from roadmap to operational system. With `sql-to-arc`, `inspire-to-arc`, and the Advanced Middleware API, we have realised the core of the network concept: automated pipelines that convert metadata from heterogeneous data sources into Annotated Research Contexts and publish them to the DataPLANT DataHub. The system has been validated with two FAIRagro RDIs — Edaphobase (relational database) and BonaRes (INSPIRE/CSW catalogue) — demonstrating the feasibility and extensibility of the approach. The generated ARCs serve downstream FAIRagro services: the Search Hub provides unified discovery across all federated metadata, while SciWIn can consume the ARC objects as FAIR Digital Objects for reproducible computational workflows. At the time of writing, the network connects more than ten FAIRagro RDIs in various stages of integration [27].

The architecture follows a client–gateway pattern: source-specific conversion clients handle the extraction and mapping of metadata from different types of data sources, while the common Advanced Middleware API provides a stable, validated gateway to the target repository. This design allows the FAIRagro Federated RDI Network to accommodate new types of data sources by developing additional conversion clients, without changes to the gateway or the target repository. The view-based adapter pattern of `sql-to-arc` further lowers the barrier for relational databases by requiring only SQL view creation rather than custom code — respecting the operational autonomy of RDI operators, a key principle of the FAIRagro federation concept.

Future work will focus on several directions. On the technical side, we plan to support incremental updates so that only new or modified investigations are re-converted, and to enrich partial ontology annotations using ontology lookup services as part of the semi-automated curation process described in the roadmap. We also plan to connect further FAIRagro RDIs — both via existing clients and new ones — contributing to the step-wise expansion of the FAIRagro Federated RDI Network envisioned in the original roadmap.

A particularly important development for the FAIRagro Federated RDI Network is the ongoing standardisation of metadata descriptions for agrosystems research data. Within FAIRagro, the AgriSchemas initiative is developing a community guideline for using Schema.org [15] and Bioschemas [16] vocabularies in the agrosystems domain [17]. AgriSchemas is not itself an extension of Schema.org but rather a set of recommendations on how to combine existing Schema.org types and Bioschemas profiles to consistently describe agrosystems-specific metadata such as soil properties, crop experiments, and environmental observations. Once AgriSchemas reaches maturity and community adoption, it is expected to become the recommended metadata schema for the FAIRagro community. From the perspective of the network architecture presented here, AgriSchemas-compliant metadata exposed by RDIs would be consumed by a dedicated conversion client following the pull strategy — harvesting structured metadata from RDI landing pages or APIs and transforming it into ARCs for publication via the Advanced Middleware API. This future client would complement the existing `sql-to-arc` and `inspire-to-arc` tools, further broadening the range of data sources that can be integrated into the FAIR data ecosystem.

---

## Declarations

### List of Abbreviations

| Abbreviation | Meaning                                                                        |
| ------------ | ------------------------------------------------------------------------------ |
| AAI          | Authentication and Authorization Infrastructure                                |
| ARC          | Annotated Research Context                                                     |
| CSW          | Catalogue Service for the Web                                                  |
| ETL          | Extract, Transform, Load                                                       |
| FAIR         | Findable, Accessible, Interoperable, Reusable                                  |
| FDO          | FAIR Digital Object                                                            |
| INSPIRE      | Infrastructure for Spatial Information in the European Community               |
| ISA          | Investigation, Study, Assay                                                    |
| mTLS         | mutual Transport Layer Security                                                |
| NFDI         | Nationale Forschungsdateninfrastruktur (National Research Data Infrastructure) |
| RDI          | Research Data Infrastructure                                                   |
| RO-Crate     | Research Object Crate                                                          |
| SciWIn       | Scientific Workflow Infrastructure                                             |

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

[1] García Brizuela, J., Scharfenberg, C., Scheuner, C., Hoedt, F., König, P., Kranz, A., Leidel, A., Martini, D., Schneider, G., Schneider, J., Singson, L. S., von Waldow, H., Wehrmeyer, N., Usadel, B., Lesch, S., Specka, X., Lange, M., & Arend, D. (2024). A roadmap for a middleware as a federation service for integrative data retrieval of agricultural data. *Journal of Integrative Bioinformatics*, 21(3). <https://doi.org/10.1515/jib-2024-0027>

[2] Godfray, H. C. J., Beddington, J. R., Crute, I. R., Haddad, L., Lawrence, D., Muir, J. F., Pretty, J., Robinson, S., Thomas, S. M., & Toulmin, C. (2010). Food security: the challenge of feeding 9 billion people. *Science*, 327(5967), 812–818. <https://doi.org/10.1126/science.1185383>

[3] Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., Appleton, G., Axton, M., Baak, A., ... & Mons, B. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data*, 3, 160018. <https://doi.org/10.1038/sdata.2016.18>

[4] FAIRagro Consortium (2021). FAIRagro – FAIR Research Data Management for Agrosystems Research. <https://fairagro.net/>

[5] NFDI e. V. (2020). National Research Data Infrastructure. <https://www.nfdi.de/>

[6] Weil, H. L., Schneider, K., Tschöpe, M., Bauer, J., Maus, O., Frey, K., ... & Usadel, B. (2023). PLANTdataHUB: a collaborative platform for continuous FAIR data sharing in plant research. *The Plant Journal*, 116(4), 974–988. <https://doi.org/10.1111/tpj.16474>

[7] Soiland-Reyes, S., Sefton, P., Crosas, M., Castro, L. J., Coppens, F., Fernández, J. M., ... & Goble, C. (2022). Packaging research artefacts with RO-Crate. *Data Science*, 5(2), 97–138. <https://doi.org/10.3233/DS-210053>

[8] Rocca-Serra, P., Brandizi, M., Maguire, E., Sklyar, N., Taylor, C., Begley, K., ... & Sansone, S. A. (2010). ISA software suite: supporting standards-compliant experimental annotation and enabling curation at the community level. *Bioinformatics*, 26(18), 2354–2356. <https://doi.org/10.1093/bioinformatics/btq415>

[9] [Edaphobase reference — to be added]

[10] BonaRes Centre for Soil and Agricultural Research (2024). BonaRes Repository. <https://www.bonares.de/>

[11] European Parliament and Council (2007). Directive 2007/2/EC establishing an Infrastructure for Spatial Information in the European Community (INSPIRE). *Official Journal of the European Union*, L 108, 1–14.

[12] Rocca-Serra, P., Sansone, S. A., et al. (2023). ISA API. GitHub. <https://github.com/ISA-tools/isa-api>

[13] Allan, C., Bhattacharya, S., Bhattacharya, D., Bhattacharya, S., Bhattacharya, S., Bhattacharya, S., ... & Moore, J. (2012). OMERO: flexible, model-driven data management for experimental biology. *Nature Methods*, 9(3), 245–253. <https://doi.org/10.1038/nmeth.1896>

[14] Rajasekar, A., Moore, R., Hou, C. Y., Lee, C. A., Marciano, R., de Torcy, A., ... & Wan, M. (2010). iRODS primer: integrated rule-oriented data system. *Synthesis Lectures on Information Concepts, Retrieval, and Services*, 2(1), 1–143. <https://doi.org/10.2200/S00233ED1V01Y200912ICR012>

[15] Schema.org Community (2024). Schema.org. <https://schema.org/>

[16] Gray, A. J. G., Goble, C., & Jiménez, R. C. (2017). Bioschemas: from potato salad to protein annotation. In *Proceedings of the ISWC 2017 Posters & Demonstrations and Industry Tracks*. <https://bioschemas.org/>

[17] Schneider, G., Jung, J., Reinosch, N., & Martini, D. (2024). (Meta) Data Standards for agricultural research data management and approaches towards evaluation. An overview. [Poster]. *FAIRagro*. Zenodo. <https://doi.org/10.5281/zenodo.12794379>

[18] CGIAR Platform for Big Data in Agriculture (2020). GARDIAN: Global Agricultural Research Data Innovation and Acceleration Network. <https://gardian.bigdata.cgiar.org/>

[19] AgReFed (2023). Agricultural Research Federation — FAIR Agricultural Data for Australia. <https://www.agrefed.org.au/>

[20] Diepenbroek, M., Glöckner, F. O., Zielinski, D., Classification, A., König-Ries, B., Frommer, B., ... & 19 partners (2014). Towards an integrated biodiversity and ecological research data management and archiving platform: the German Federation for the Curation of Biological Data (GFBio). *Informatik 2014*, 1711–1721. <https://www.gfbio.org/>

[21] Sayers, E. W., Bolton, E. E., Brister, J. R., Canese, K., Chan, J., Comeau, D. C., ... & Sherry, S. T. (2022). Database resources of the National Center for Biotechnology Information. *Nucleic Acids Research*, 50(D1), D13–D25. <https://doi.org/10.1093/nar/gkab1112>

[22] Burley, S. K., Cochrane, G., Denber, P., Griffin, R., Hendricks, A., Kanz, C., ... & Apweiler, R. (2023). EMBL-EBI in 2022. *Nucleic Acids Research*, 51(D1), D9–D17. <https://doi.org/10.1093/nar/gkac1098>

[23] Lemberger, T. (2015). From bench to website: ELIXIR — a distributed infrastructure for life-science information. *Molecular Systems Biology*, 11(2), 785. <https://doi.org/10.15252/msb.20156028>

[24] Pieper, D. & Summann, F. (2006). Bielefeld Academic Search Engine (BASE): An end-user oriented institutional repository search service. *Library Hi Tech*, 24(4), 614–619. <https://doi.org/10.1108/07378830610715473>

[25] Manghi, P., Atzori, C., Bardi, A., Baglioni, M., Schirrwagen, J., Dimitropoulos, H., ... & La Bruzzo, S. (2022). OpenAIRE Research Graph. *Zenodo*. <https://doi.org/10.5281/zenodo.6616871>

[26] Leidel, A., Krumsieck, J., König, P., von Waldow, H., & Hoedt, F. (2024). Boosting Scientific Reusability: A Concept for a FAIR Scientific Workflow Infrastructure (SciWIn). [Poster]. *Zenodo*. <https://doi.org/10.5281/zenodo.11619214>

[27] García Brizuela, J., Scharfenberg, C., Specka, X., Lange, M., & Arend, D. (2026). FAIRagro Federated RDI Network: Connecting Agrosystem Research Data. [Poster]. *FAIRagro Community Summit 2026*. [in press]
