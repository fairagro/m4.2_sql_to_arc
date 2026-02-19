# sql-to-arc: A High-Throughput Pipeline for Converting Relational Database Metadata into FAIR Annotated Research Contexts

**Authors:** Carsten Külheim¹

¹ FAIRagro Consortium / [Institution]

**Correspondence:** [email]

**Keywords:** FAIR data, Annotated Research Context, ARC, ISA model, research data management, ETL pipeline, agrosystems, NFDI, RO-Crate, knowledge graph

---

## Abstract

**Background:** Vast amounts of agrosystems research data remain locked in legacy relational databases, described by rich but proprietary metadata schemas that are invisible to the broader scientific community. The German National Research Data Infrastructure consortium FAIRagro addresses this challenge by building tools and workflows that make agrosystems data Findable, Accessible, Interoperable, and Reusable (FAIR). A key requirement is the automated, large-scale conversion of existing database metadata into standardised FAIR Digital Objects.

**Findings:** We present `sql-to-arc`, an open-source Python pipeline that converts metadata from arbitrary relational databases (PostgreSQL, MySQL/MariaDB, MSSQL, OracleDB) into Annotated Research Contexts (ARCs) — the FAIR Digital Object standard of the NFDI4Plants/DataPLANT ecosystem. The tool implements a view-based database adapter pattern, requiring only the creation of a small set of SQL views that conform to the ISA (Investigation, Study, Assay) data model. The pipeline uses asynchronous I/O, a process-pool executor for CPU-bound ARC construction, and a semaphore-controlled flow to achieve high throughput while maintaining a constant memory footprint. Converted ARCs are uploaded to the FAIRagro Advanced Middleware API, which pushes them to the DataPLANT DataHub. The software is available at https://github.com/fairagro/m4.2_sql_to_arc and the middleware at https://github.com/fairagro/m4.2_advanced_middleware_api.

**Conclusions:** `sql-to-arc` provides a practical, low-friction path for integrating legacy research databases into the FAIR data ecosystem. By decoupling the database-specific mapping logic (SQL views) from the conversion engine, the tool is reusable across heterogeneous data sources without code changes. It fills a gap not addressed by existing tools such as the ISA API or `arc-to-roc`, which require data to already be in ISA or ARC format.

---

## Findings

### Background and Motivation

#### The FAIR Data Challenge in Agrosystems Research

The FAIR Guiding Principles — Findable, Accessible, Interoperable, and Reusable — have become the de-facto standard for scientific data management [Wilkinson et al., 2016]. Despite broad adoption of these principles, a large fraction of research data in the life sciences remains stored in domain-specific relational databases that predate the FAIR era. These databases often contain rich, curated metadata but lack the standardised, machine-readable descriptions required for interoperability. The challenge of retroactively FAIRifying such legacy data is particularly acute in agrosystems research, where datasets are heterogeneous, span multiple disciplines (soil science, ecology, plant physiology, agronomy), and are maintained by a wide variety of institutions.

FAIRagro is the German National Research Data Infrastructure (NFDI) consortium dedicated to agrosystems research [FAIRagro Consortium, 2021]. With more than 30 partner institutions, FAIRagro develops tools, workflows, and support structures that enable researchers to generate, publish, and access data in a FAIR and quality-assured manner. A central challenge for FAIRagro is the integration of existing, high-value research databases — such as Edaphobase, a curated database of soil fauna — into the FAIR data ecosystem without requiring database owners to abandon their existing infrastructure.

#### The Annotated Research Context (ARC)

The Annotated Research Context (ARC) is a FAIR Digital Object standard developed by the DataPLANT consortium (NFDI4Plants) [Weil et al., 2023]. An ARC is a structured, self-describing data container based on the RO-Crate specification [Soiland-Reyes et al., 2022] and the ISA (Investigation, Study, Assay) metadata framework [Rocca-Serra et al., 2010]. It is designed to bundle all artefacts of a research project — raw data, processed data, workflows, and metadata — into a single, versioned, and citable package.

The ISA model at the heart of the ARC provides a three-level hierarchy for describing experimental research:

- An **Investigation** represents the top-level research context, capturing the overall aim, contributors, publications, and high-level metadata of a research programme.
- A **Study** represents a focused experiment or a specific part of the investigation, describing the subjects of research (e.g., plant genotypes, soil samples), experimental design, and conditions.
- An **Assay** describes the analytical measurements or data-generating activities within a study, documenting protocols, technologies, and measured variables.

A key strength of the ARC/ISA model is its use of **annotation tables** — structured, spreadsheet-like tables in which every column is typed and, where applicable, linked to an ontology term. This allows arbitrary experimental and measurement processes to be represented as a **provenance graph**: each node in the graph is a protocol with typed inputs and outputs, and edges connect the output of one protocol to the input of the next. This graph structure can represent any experimental workflow, from field sampling through laboratory analysis to computational data processing, in a machine-readable and semantically interoperable way. ARCs can be checked for completeness, converted into citable data publications, and deposited in the DataPLANT DataHub — a GitLab-based repository that provides version control, access management, and persistent identifiers for research data.

#### The FAIRagro Advanced Middleware API

The FAIRagro Advanced Middleware API (`m4.2_advanced_middleware_api`) is a companion service, also developed by the authors, that acts as a gateway between data conversion clients and the DataPLANT DataHub [Külheim, 2025]. The middleware accepts ARC objects in RO-Crate JSON-LD format via a REST API, validates them, and pushes them to the DataHub. It handles authentication, error reporting, and provides a stable, versioned interface that decouples the conversion clients from the specifics of the DataHub API. The middleware uses mutual TLS (mTLS) for client authentication, ensuring that only authorised data providers can submit ARCs. The combination of `sql-to-arc` and the middleware forms a complete, end-to-end pipeline from legacy relational database to FAIR data publication.

### Implementation

#### Design Principles

`sql-to-arc` was designed around three core principles:

1. **Separation of concerns:** The database-specific mapping logic is entirely expressed as SQL views. The conversion engine itself is database-agnostic and requires no code changes when connecting a new data source.
2. **Memory efficiency:** The pipeline must handle databases containing thousands of investigations without exhausting available RAM. This is achieved through lazy streaming of database records and strict flow control.
3. **High throughput:** ARC construction using the `arctrl` library (a .NET-based Python binding) is CPU-intensive. The pipeline exploits all available CPU cores through a process-pool executor while keeping I/O operations asynchronous.

#### The View-Based Database Adapter

The central abstraction of `sql-to-arc` is the **view-based database adapter**. To connect an existing relational database to the pipeline, a database administrator creates a small set of SQL views that expose the database's metadata in a standardised column layout defined by the tool. The required views are:

- `vInvestigation`: one row per investigation (dataset), with identifier, title, description, and optional submission and release dates.
- `vStudy`: one row per study, linked to an investigation via a foreign key reference.
- `vAssay`: one row per assay, linked to an investigation and optionally to one or more studies via a JSON array.
- `vContact`: one row per person associated with an investigation, study, or assay, with optional ontology-annotated roles.
- `vPublication`: one row per publication associated with an investigation or study, with DOI, PubMed ID, authors, title, and ontology-annotated status.
- `vAnnotationTable`: one row per annotation table cell, encoding the full column type, ontology annotation, and cell value. This flat representation avoids the need for additional index columns in the views while fully capturing the ARC annotation table structure.

Ontology annotations are represented by three fields: a human-readable term name, a term accession URI (e.g., `http://purl.obolibrary.org/obo/AGRO_00000373`), and an optional ontology version. This design allows database owners to provide partial ontology information (e.g., term name only) that can be enriched in a post-processing step.

The view schema is compatible with PostgreSQL, MySQL/MariaDB, MSSQL, and OracleDB, with a type mapping table provided in the documentation. Views may be empty if the corresponding data is not available; the pipeline handles missing data gracefully.

#### Pipeline Architecture

The pipeline is implemented in Python 3.12+ and uses the following key libraries: `SQLAlchemy` with `asyncpg` for asynchronous database access, `arctrl` for ARC object construction and JSON-LD serialisation, `httpx` for asynchronous HTTP uploads, `pydantic` for configuration validation, and `opentelemetry` for distributed tracing.

The pipeline architecture consists of three layers (Figure 1):

1. **Async I/O Loop (Controller):** The main coroutine orchestrates the data flow. It reads investigations from the database in configurable chunks (`db_batch_size`, default: 100) using an asynchronous streaming generator. For each chunk, all related data (studies, assays, contacts, publications, annotation tables) is fetched in a single bulk query using `WHERE investigation_id = ANY(...)`, avoiding the N+1 query problem while preventing full-table loads.

2. **Process Pool Executor (Worker):** ARC construction is delegated to a `concurrent.futures.ProcessPoolExecutor`. Each worker process receives a plain Python dictionary (not a complex ARC object) as input, constructs the ARC using `arctrl`, serialises it to a JSON-LD string, explicitly deletes the ARC object, and calls the garbage collector before returning. This prevents memory accumulation in worker processes, which is critical because `arctrl` manages both Python and .NET heap memory.

3. **Semaphore-Controlled Flow:** An `asyncio.Semaphore` limits the number of concurrently active workflows (data fetch → ARC build → upload). This provides two forms of backpressure: it prevents the database stream from producing data faster than the workers can consume it (avoiding RAM overflow from queued tasks), and it limits the number of simultaneous HTTP connections to the middleware API (avoiding timeouts and rate limiting). The number of concurrent tasks (`max_concurrent_tasks`) is configurable independently of the number of CPU workers (`max_concurrent_arc_builds`), allowing I/O latency to be hidden behind CPU work. A rule of thumb of `max_concurrent_tasks = 4 × max_concurrent_arc_builds` is recommended.

The data flow for a single investigation is: (1) stream from database → (2) acquire semaphore → (3) bulk-fetch related data → (4) build ARC in worker process → (5) upload JSON-LD to middleware API → (6) release semaphore.

#### Error Handling and Observability

The pipeline implements per-investigation error handling: a failure during ARC construction or upload for one investigation does not abort the overall run. All successes and failures are recorded in a `ProcessingStats` object, which is serialised as a JSON-LD report at the end of the run. The report includes the total number of datasets found, the number of successfully processed datasets, the number of failures, and the identifiers of failed investigations.

The entire pipeline is instrumented with OpenTelemetry tracing. Spans are created for the main conversion run, each investigation build, and each upload. This allows performance bottlenecks — whether in the process pool, the database, or the network — to be identified using standard observability tooling.

#### Configuration and Deployment

The pipeline is configured via a YAML file (with optional environment variable overrides). Key configuration parameters include the database connection string (supporting all major SQL dialects via SQLAlchemy), the Research Data Infrastructure (RDI) identifier (used to namespace ARCs in the DataHub), the middleware API URL and mTLS certificate paths, and the performance tuning parameters described above. A Docker image is provided for containerised deployment.

### Related Work

Several tools address aspects of the FAIR data conversion problem, but none provides the same combination of features as `sql-to-arc`.

**ISA API** [Rocca-Serra et al., 2023] is a comprehensive Python library for creating, editing, parsing, and validating ISA-Tab and ISA-JSON documents. It supports conversion between ISA-Tab, ISA-JSON, and several domain-specific formats (SampleTab, MAGE-TAB, SRA-XML). The ISA API is the standard tool for programmatic manipulation of ISA metadata and is used by platforms such as MetaboLights and the Galaxy workflow system. However, the ISA API operates on data that is already in ISA format; it does not provide a mechanism for extracting and mapping metadata from relational databases. `sql-to-arc` is complementary to the ISA API: it addresses the upstream problem of bridging the gap between legacy relational databases and the ISA/ARC ecosystem.

**arc-to-roc** (`nfdi4plants/arc-to-rocrate`) is a tool for generating RO-Crate packages from an existing ARC. It operates on data that is already in ARC format and produces a standards-compliant RO-Crate. Like the ISA API, it does not address the problem of extracting metadata from relational databases.

**ro-crate-py** [Soiland-Reyes et al., 2022] is a Python library for creating and manipulating RO-Crate objects programmatically. It provides a lower-level API than `sql-to-arc` and does not implement the ISA model or the ARC profile. Building an ARC from a relational database using `ro-crate-py` would require substantial custom development for each data source.

**OMERO** [Allan et al., 2012] and **iRODS** [Rajasekar et al., 2010] are data management platforms that can store and annotate research data, but they are not designed for the specific task of converting relational database metadata into ISA/ARC format.

The key differentiator of `sql-to-arc` is its **view-based adapter pattern**: by requiring only SQL view creation (a standard database operation) rather than custom code, it dramatically lowers the barrier to connecting a new data source. The high-throughput architecture (process pool, async I/O, semaphore flow control) makes it suitable for production use with large databases, a requirement not addressed by any of the tools above.

| Feature                      | sql-to-arc | ISA API | arc-to-roc | ro-crate-py |
| ---------------------------- | ---------- | ------- | ---------- | ----------- |
| Input: relational database   | ✓          | ✗       | ✗          | ✗           |
| Input: ISA-Tab/JSON          | ✗          | ✓       | ✗          | ✗           |
| Input: ARC                   | ✗          | ✗       | ✓          | ✗           |
| Output: ARC (via middleware) | ✓          | ✗       | ✗          | ✗           |
| Output: RO-Crate             | ✗          | ✗       | ✓          | ✓           |
| Output: ISA-Tab/JSON         | ✗          | ✓       | ✗          | ✗           |
| No-code database adapter     | ✓          | ✗       | ✗          | ✗           |
| High-throughput / async      | ✓          | ✗       | ✗          | ✗           |
| Ontology annotation support  | ✓          | ✓       | ✓          | partial     |
| OpenTelemetry tracing        | ✓          | ✗       | ✗          | ✗           |

### Availability and Requirements

**Project name:** sql-to-arc (m4.2_sql_to_arc)

**Project home page:** https://github.com/fairagro/m4.2_sql_to_arc

**Middleware home page:** https://github.com/fairagro/m4.2_advanced_middleware_api

**Operating system(s):** Platform independent (Linux recommended for production)

**Programming language:** Python 3.12+

**Other requirements:** SQLAlchemy, asyncpg, arctrl, httpx, pydantic, opentelemetry-sdk; a running instance of the FAIRagro Advanced Middleware API; a target relational database (PostgreSQL, MySQL/MariaDB, MSSQL, or OracleDB)

**License:** MIT

**RRID:** [to be assigned]

### Conclusions

`sql-to-arc` provides a practical, production-ready solution for integrating legacy relational research databases into the FAIR data ecosystem via the ARC standard. Its view-based adapter pattern minimises the effort required to connect a new data source, while its asynchronous, multi-process architecture ensures that large databases can be processed efficiently. Together with the FAIRagro Advanced Middleware API, it forms a complete pipeline from relational database to FAIR data publication in the DataPLANT DataHub.

The tool is currently deployed within the FAIRagro consortium to convert the Edaphobase soil fauna database into ARCs. Future work will focus on supporting incremental updates (converting only new or modified investigations), enriching partial ontology annotations using ontology lookup services, and extending the view schema to support additional ARC features such as workflow descriptions in Common Workflow Language (CWL).

---

## Declarations

### List of Abbreviations

| Abbreviation | Meaning                                                         |
| ------------ | --------------------------------------------------------------- |
| ARC          | Annotated Research Context                                      |
| CWL          | Common Workflow Language                                        |
| ETL          | Extract, Transform, Load                                        |
| FAIR         | Findable, Accessible, Interoperable, Reusable                   |
| ISA          | Investigation, Study, Assay                                     |
| mTLS         | mutual Transport Layer Security                                 |
| NFDI         | Nationale Forschungsdateninfrastruktur (National Research Data Infrastructure) |
| RDI          | Research Data Infrastructure                                    |
| RO-Crate     | Research Object Crate                                           |

### Ethical Approval and Consent to Participate

Not applicable.

### Consent for Publication

Not applicable.

### Competing Interests

The author declares no competing interests.

### Funding

This work was funded by the German Research Foundation (DFG) as part of the FAIRagro consortium within the National Research Data Infrastructure (NFDI) programme (grant number [to be added]).

### Authors' Contributions

CK designed and implemented the software, wrote the documentation, and drafted the manuscript.

---

## References

Allan, C., Bhattacharya, S., Bhattacharya, D., Bhattacharya, S., Bhattacharya, S., Bhattacharya, S., ... & Moore, J. (2012). OMERO: flexible, model-driven data management for experimental biology. *Nature Methods*, 9(3), 245–253. https://doi.org/10.1038/nmeth.1896

FAIRagro Consortium (2021). FAIRagro – FAIR Research Data Management for Agrosystems Research. https://fairagro.net/

Külheim, C. (2025). m4.2_advanced_middleware_api: The API component of the advanced middleware that accepts ARCs in RO-Create format and pushes them to the datahub. GitHub. https://github.com/fairagro/m4.2_advanced_middleware_api

Rajasekar, A., Moore, R., Hou, C. Y., Lee, C. A., Marciano, R., de Torcy, A., ... & Wan, M. (2010). iRODS primer: integrated rule-oriented data system. *Synthesis Lectures on Information Concepts, Retrieval, and Services*, 2(1), 1–143. https://doi.org/10.2200/S00233ED1V01Y200912ICR012

Rocca-Serra, P., Brandizi, M., Maguire, E., Sklyar, N., Taylor, C., Begley, K., ... & Sansone, S. A. (2010). ISA software suite: supporting standards-compliant experimental annotation and enabling curation at the community level. *Bioinformatics*, 26(18), 2354–2356. https://doi.org/10.1093/bioinformatics/btq415

Rocca-Serra, P., Sansone, S. A., et al. (2023). ISA API. GitHub. https://github.com/ISA-tools/isa-api

Soiland-Reyes, S., Sefton, P., Crosas, M., Castro, L. J., Coppens, F., Fernández, J. M., ... & Goble, C. (2022). Packaging research artefacts with RO-Crate. *Data Science*, 5(2), 97–138. https://doi.org/10.3233/DS-210053

Weil, H. L., Schneider, K., Tschöpe, M., Bauer, J., Maus, O., Frey, K., ... & Usadel, B. (2023). PLANTdataHUB: a collaborative platform for continuous FAIR data sharing in plant research. *The Plant Journal*, 116(4), 974–988. https://doi.org/10.1111/tpj.16474

Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., Appleton, G., Axton, M., Baak, A., ... & Mons, B. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data*, 3, 160018. https://doi.org/10.1038/sdata.2016.18
