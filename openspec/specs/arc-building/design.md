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
  ├── map_investigation(row)        → ArcInvestigation
  ├── ARC.from_arc_investigation()
  ├── _add_studies_to_arc()
  │     └── map_study(row)          → ArcStudy
  ├── _add_assays_to_arc()
  │     ├── map_assay(row)          → ArcAssay
  │     └── _link_assay_to_studies()
  ├── _add_contacts_to_arc()
  │     └── map_contact(row)        → Person
  ├── _add_publications_to_arc()
  │     └── map_publication(row)    → Publication
  ├── _process_annotation_tables()
  │     ├── _build_arc_table()
  │     │     ├── _get_column_key()
  │     │     ├── _build_header()   → CompositeHeader
  │     │     └── _build_single_cell() → CompositeCell
  │     └── target.AddTable(table)
  └── arc.ToROCrateJsonString()     → str  (immediately freed after)
```

## Key Decisions

1. **`mapper.py` has no conditional logic on DB structure**
   — Each mapper function takes a single typed row and returns a single
   ARCTRL object. All relational wiring (linking assays to studies, routing
   contacts) is the responsibility of `builder.py`. This keeps mappers
   unit-testable without a full ARC context.

2. **Two-pass grouping for annotation tables**
   — `vAnnotationTable` delivers one row per cell (see database-access design).
   `builder.py` first groups by `(target_type, target_ref, table_name)` to
   identify each table, then by column key to reconstruct columns before
   calling `ArcTable.AddColumn()`.

3. **Column key is a 7-tuple derived from metadata columns**
   — `(column_type, column_io_type, column_value, column_annotation_term,
   column_annotation_uri, column_annotation_version, column_name)`.
   Stable across row iterations; used as a dict key to build per-column
   cell lists without a second pass.

4. **Worker process: explicit GC after serialization**
   — `arctrl` objects hold .NET interop memory that the Python GC may not
   collect promptly. `del arc` + `gc.collect()` immediately after
   `ToROCrateJsonString()` prevents worker processes from accumulating
   memory across many investigations.

5. **No `OntologySourceReference` objects are created**
   — `xxx_version` from the DB views belongs to `OntologySourceReference.version`
   in ARCtrl, not to `OntologyAnnotation`. Populating it correctly requires
   registering one `OntologySourceReference` per ontology source on the
   investigation — complexity not justified by the benefit. `tsr` is always `""`
   and `_version` is silently dropped. ARCs serialize with
   `"ontologySourceReferences": []` — valid JSON-LD, but ontology version
   provenance is lost.

## OntologyAnnotation Mapping Convention

```text
DB field    → OntologyAnnotation argument
xxx_term    → name
xxx_uri     → tan  (TermAccessionNumber)
xxx_version → (ignored, see Key Decision 5)
              tsr  (TermSourceREF) is always ""
```
