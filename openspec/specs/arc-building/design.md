# ARC Building — Design

## Module Responsibilities

```text
mapper.py   — Pure row-to-ARCTRL-object functions (no logic, no branching on
              table structure). One public function per entity type.

builder.py  — Orchestration: assembles the ARC from mapper output, handles
              relational linking, builds ArcTable objects from flat rows.
              Entry point: build_single_arc_task(ArcBuildData) → str
```

## Call Graph

```text
build_single_arc_task(data)
  └── _assemble_arc(data)           → ARC
        ├── map_investigation(row)  → ArcInvestigation
        ├── ARC.from_arc_investigation()
        ├── OntologySourceRegistry()
        ├── _add_studies_to_arc()
        │     └── map_study(row)    → ArcStudy
        ├── _add_assays_to_arc()
        │     ├── map_assay(row, registry) → ArcAssay
        │     └── _link_assay_to_studies()
        ├── _add_contacts_to_arc()
        │     └── map_contact(row, registry) → Person
        ├── _add_publications_to_arc()
        │     └── map_publication(row, registry) → Publication
        ├── _process_annotation_tables()
        │     ├── _build_arc_table()
        │     │     ├── _get_column_key()
        │     │     ├── _build_header() → CompositeHeader
        │     │     └── _build_single_cell() → CompositeCell
        │     └── target.AddTable(table)
        └── registry.apply_to_investigation(arc)
  └── arc.ToROCrateJsonString()     → str  (immediately freed after)
```

## Key Decisions

1. **`mapper.py` has no conditional logic on DB structure** — Each mapper function takes a single typed row and returns
   a single ARCTRL object. All relational wiring (linking assays to studies, routing contacts) is the responsibility of
   `builder.py`. This keeps mappers unit-testable without a full ARC context.

2. **Two-pass grouping for annotation tables** — `vAnnotationTable` delivers one row per cell (see database-access
   design). `builder.py` first groups by `(target_type, target_ref, table_name)` to identify each table, then by column
   key to reconstruct columns before calling `ArcTable.AddColumn()`.

3. **Column key is a 7-tuple derived from metadata columns** —
   `(column_type, column_io_type, column_value, column_annotation_term, column_annotation_uri, column_annotation_version, column_name)`.
   Stable across row iterations; used as a dict key to build per-column cell lists without a second pass.

4. **Worker process: explicit GC after serialization** — `arctrl` objects hold .NET interop memory that the Python GC
   may not collect promptly. `del arc` + `gc.collect()` immediately after `ToROCrateJsonString()` prevents worker
   processes from accumulating memory across many investigations.

5. **OntologySourceReference from URI + version** — `OntologyAnnotation` is built only from view triples (`term`→`name`,
   `uri`→`tan`). `TermSourceREF` (`tsr`) is the ontology short name derived from the term-accession URI (OBO/purl
   `PREFIX_digits`). `xxx_version` is stored on a matching `OntologySourceReference` (unique per `(name, version)`) on
   the investigation, not on the annotation. Unparseable/missing URI → empty `tsr`, no OSR. Note: arctrl RO-Crate export
   may omit the `ontologySourceReferences` array while preserving annotation `tsr`.

## OntologyAnnotation Mapping Convention

```text
DB field    → OntologyAnnotation / OSR
xxx_term    → OntologyAnnotation.name
xxx_uri     → OntologyAnnotation.tan  (TermAccessionNumber);
              also derives OntologyAnnotation.tsr (TermSourceREF) when parseable
xxx_version → OntologySourceReference.version (with URI-derived Name / OA tsr)
```
