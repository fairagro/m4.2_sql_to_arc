# Paper Outline

> **Zweck:** Dieses Dokument bildet die Struktur und Kerninhalte des Papers ab.
> Änderungen hier dienen als Grundlage für die Überarbeitung von `paper_sql_to_arc.md`.

---

## Titel

**From Roadmap to Reality: Implementing the FAIRagro Extended Middleware for Automated ARC Generation from Heterogeneous Research Data Infrastructures**

---

## Abstract

- **Background:**
  - Vorgänger-Paper [1] definierte FAIRagro Middleware-Roadmap
  - Zwei Phasen: Basic Middleware (Metadaten-Harvesting) + Extended Middleware (FDO/ARC-Transformation)
  - Basic Middleware war operativ, Extended Middleware nur Konzept

- **Findings:**
  - Drei Komponenten entwickelt und deployed:
    1. `sql-to-arc` — Konvertierung aus relationalen Datenbanken (view-basierter Adapter, Push-Strategie)
    2. `inspire-to-arc` — Harvesting von INSPIRE/CSW-Endpoints (Pull-Strategie)
    3. Advanced Middleware API — Gateway für Validierung + Publikation zum DataPLANT DataHub
  - Validiert mit zwei RDIs: Edaphobase (sql-to-arc) und BonaRes (inspire-to-arc)

- **Conclusions:**
  - Extended Middleware ist jetzt operativ
  - Architektur unterstützt heterogene Datenquellen (Push + Pull)
  - Gemeinsame Middleware API entkoppelt Daten-Provider vom Ziel-Repository

---

## Findings

### Background and Motivation

#### The FAIRagro Middleware Roadmap
- Agrar-Herausforderungen (Klimawandel, Biodiversität, Produktivität) [2]
- FAIR-Prinzipien [3] als Standard für Datenmanagement
- FAIRagro [4, 5] als NFDI-Konsortium für Agrosystemforschung
- Zentrale Herausforderung: >12 heterogene RDIs vernetzen, ohne deren Autonomie einzuschränken [1]
- Roadmap [1] mit zwei Phasen:
  1. **Basic Middleware**: JSON-LD Metadaten-Harvesting → Search Portal + SciWIn (bereits operativ)
  2. **Extended Middleware**: FDO-Transformation mit ARC/DataPLANT [6], Push- und Pull-Strategie
- **Dieses Paper:** Umsetzung der Extended Middleware
  - `sql-to-arc` = Push (RDI baut ARCs, schickt sie zur Middleware)
  - `inspire-to-arc` = Pull (Middleware harvested CSW-Endpoints)

#### The Annotated Research Context (ARC)
- FDO-Standard von DataPLANT [6]
- Basiert auf RO-Crate [7] und ISA-Framework [8]
- ISA-Hierarchie: Investigation → Study → Assay
- Annotation Tables: typisierte Spalten, Ontologie-Verknüpfung → Provenance-Graph
- Gründe für ARC als FDO-Format (aus Roadmap [1]):
  - ISA-Modell flexibel für heterogene Agrar-Daten
  - GitLab als skalierbares Storage-Backend
  - DataPLANT-Tooling verfügbar
  - RO-Crate-Kompatibilität für SciWIn

### Approach

- **Zwei komplementäre Strategien** aus der Roadmap [1]: Push + Pull
- **Zwei Designprinzipien:**
  1. Quell-spezifische Conversion Clients (sql-to-arc, inspire-to-arc)
  2. Entkoppelte Middleware API als gemeinsames Gateway

#### The View-Based Database Adapter (sql-to-arc)
- DB-Admin erstellt SQL Views, kein Code nötig
- Views folgen der ISA-Hierarchie:
  - `vInvestigation`, `vStudy`, `vAssay`, `vContact`, `vPublication`, `vAnnotationTable`
- Ontologie-Annotation: Term Name + Accession URI + Version (partiell möglich)
- Kompatibel mit PostgreSQL, MySQL/MariaDB, MSSQL, OracleDB
- Leere Views erlaubt → graceful handling

#### The FAIRagro Advanced Middleware API
- Gateway zwischen Conversion Clients und DataPLANT DataHub
- Nimmt RO-Crate JSON-LD entgegen, validiert, publiziert
- Authentifizierung via mTLS
- Realisiert die "ARC-based GitLab infrastructure" aus der Roadmap [1]

#### The INSPIRE-to-ARC Converter (inspire-to-arc)
- Für RDIs mit INSPIRE/CSW-Endpoints (EU-Richtlinie für Geodateninfrastruktur) [11]
- Harvested ISO 19139-Metadaten via CSW-Protokoll
- Mapping-Herausforderung: INSPIRE beschreibt *Datensätze*, ISA beschreibt *Forschungsprozesse*
- Protocol-basiertes Mapping:
  - Datensatz-Kontext → Investigation
  - Daten-Workflow (Lineage, Sampling, Acquisition, Processing) → Study mit Protokollen
  - Messungen/Technologie → Assay
- Teilt gemeinsame Infrastruktur mit sql-to-arc (api_client, shared)

#### Conversion Pipelines
- Gemeinsames Pipeline-Pattern beider Clients:
  1. Extract (SQL Views / CSW Queries)
  2. Map (→ ISA-Modell)
  3. Construct (arctrl-Bibliothek)
  4. Serialise (RO-Crate JSON-LD)
  5. Submit (→ Middleware API)
- Produktionstauglich: Async I/O, Parallelisierung, Flow Control, konstanter Speicherverbrauch
- Per-Dataset Error Handling, strukturierter Abschlussbericht

### Applications

- Validierung mit zwei FAIRagro-RDIs

#### Edaphobase (via sql-to-arc)
- Kuratierte Bodenfauna-Datenbank, Senckenberg Museum Görlitz [9]
- Ökologische/taxonomische Daten über Bodenorganismen, jahrzehntelange Forschung
- PostgreSQL-Datenbank, vorher nur über Web-Interface zugänglich
- SQL Views erstellt → ISA-Mapping ohne Änderung der Quell-Applikation
- Automatische Konvertierung + Publikation als ARCs

#### BonaRes (via inspire-to-arc)
- Boden- und Agrarforschungs-Repository [10]
- Geospatiale Metadaten über INSPIRE-kompatiblen CSW-Endpoint
- Harvesting + Konvertierung demonstriert Erweiterbarkeit über SQL hinaus

- **Gemeinsames Fazit:** Heterogene Quellen über dedizierte Clients angebunden, gemeinsame Middleware API als Gateway

### Related Work

- **ISA API** [12]: ISA-Tab/JSON Manipulation — erfordert bereits ISA-Format als Input
- **arc-to-roc**: ARC → RO-Crate — erfordert bereits ARC als Input
- **ro-crate-py** [7]: Generische RO-Crate-Erstellung — kein ISA/ARC-Profil
- **OMERO** [13] + **iRODS** [14]: Datenmanagement-Plattformen — kein ISA/ARC-Konvertierung
- **Differenzierung:** sql-to-arc/inspire-to-arc füllen die Lücke zwischen heterogenen Legacy-Quellen und dem ISA/ARC-Ökosystem
- Feature-Vergleichstabelle (6 Tools × 9 Features)

### Availability and Requirements

- sql-to-arc: GitHub, Python 3.12+, MIT
- inspire-to-arc: GitHub, Python 3.12+, MIT
- Advanced Middleware API: GitHub
- RRID: noch zuzuweisen

### Conclusions

- **Rückbezug auf Roadmap [1]**: Basic → Extended Middleware
- **Ergebnis**: Operatives System mit sql-to-arc + inspire-to-arc + Middleware API
- **Architektur**: Client–Gateway Pattern
  - Quell-spezifische Clients für Extraktion + Mapping
  - Gemeinsame Middleware API als validiertes Gateway
  - Neue Quellen durch neue Clients erweiterbar
- **sql-to-arc**: View-basierter Adapter, kein Code nötig → respektiert RDI-Autonomie

- **Future Work (technisch):**
  - Inkrementelle Updates (nur neue/geänderte Investigations)
  - Ontologie-Anreicherung via Lookup-Services
  - Weitere RDI-Anbindungen

- **Ausblick: AgriSchemas [15, 16, 17]:**
  - Community-Leitfaden für Schema.org + Bioschemas im Agrar-Kontext
  - Keine eigene Schema.org-Erweiterung, sondern Nutzungsempfehlungen
  - Soll empfohlenes Metadaten-Schema der FAIRagro-Community werden
  - Perspektive für Middleware: Zukünftiger Pull-Client, der AgriSchemas-Metadaten von RDI-Landingpages harvested und in ARCs umwandelt

---

## Declarations

- Abkürzungsverzeichnis (AAI, ARC, CSW, ETL, FAIR, FDO, INSPIRE, ISA, mTLS, NFDI, RDI, RO-Crate)
- Ethics: n/a
- Competing Interests: keine
- Funding: DFG / FAIRagro / NFDI (Grant 501899475)
- Authors' Contributions: CK (Design, Implementierung, Dokumentation, Manuskript)

---

## Referenzen (Kurzübersicht)

| Nr   | Referenz                                | Kontext im Paper                    |
| ---- | --------------------------------------- | ----------------------------------- |
| [1]  | García Brizuela et al. 2024             | Vorgänger-Paper / Roadmap           |
| [2]  | Godfray et al. 2010                     | Agrar-Herausforderungen             |
| [3]  | Wilkinson et al. 2016                   | FAIR-Prinzipien                     |
| [4]  | FAIRagro Consortium 2021                | FAIRagro                            |
| [5]  | NFDI e.V. 2020                          | NFDI                                |
| [6]  | Weil et al. 2023                        | DataPLANT / ARC                     |
| [7]  | Soiland-Reyes et al. 2022              | RO-Crate                            |
| [8]  | Rocca-Serra et al. 2010                 | ISA-Modell                          |
| [9]  | [Edaphobase — noch einzufügen]          | Anwendungsfall sql-to-arc           |
| [10] | BonaRes 2024                            | Anwendungsfall inspire-to-arc       |
| [11] | EU INSPIRE-Richtlinie 2007             | INSPIRE-Kontext                     |
| [12] | Rocca-Serra et al. 2023                 | ISA API                             |
| [13] | Allan et al. 2012                       | OMERO                               |
| [14] | Rajasekar et al. 2010                   | iRODS                               |
| [15] | Schema.org 2024                         | Ausblick / AgriSchemas              |
| [16] | Gray et al. 2017                        | Bioschemas                          |
| [17] | Schneider et al. 2024 (Poster/Zenodo)   | AgriSchemas / FAIRagro Standards     |

---

## Offene Punkte

- [ ] Autor-Details (Institution, E-Mail)
- [ ] Co-Autoren klären
- [ ] Edaphobase-Referenz [9] ergänzen
- [ ] BonaRes-Referenz [10] prüfen/verbessern
- [ ] Zieljournal entscheiden (GigaScience vs. JIB)
- [ ] Titel: Ist "From Roadmap to Reality" passend?
- [ ] RRID zuweisen
- [ ] Optional: Architektur-Diagramm(e)
