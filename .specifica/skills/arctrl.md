# ARCtrl — Usage Skill

Reference for using the `arctrl` Python library (v3.x) in this project.
ARCtrl is a Fable-transpiled F# library — the Python surface is idiomatic
but some internals are Fable runtime types.

---

## Package & Imports

```python
from arctrl import (
    ARC,
    ArcAssay,
    ArcInvestigation,
    ArcStudy,
    ArcTable,
    CompositeCell,
    CompositeHeader,
    IOType,
    OntologyAnnotation,
    Person,
    Publication,
)

# Async write helper (Fable internal — untyped, needs type: ignore)
from arctrl.py.fable_modules.fable_library.async_ import start_as_task  # type: ignore[import-untyped]
```

---

## Core Objects

### OntologyAnnotation

```python
# Empty / unknown
oa = OntologyAnnotation()

# With values: name=term, tan=URI (TermAccessionNumber), tsr=TermSourceREF
oa = OntologyAnnotation(name="soil texture", tan="http://purl.obolibrary.org/obo/ENVO_00002001", tsr="")
# tsr is usually left empty when only a URI is available
```

### ArcInvestigation

```python
inv = ArcInvestigation.create(
    identifier="inv001",            # required, must be non-empty
    title="My Investigation",
    description="...",
    submission_date="2024-01-15",   # ISO string or None
    public_release_date="2025-01-01",
)
```

### ArcStudy

```python
study = ArcStudy.create(
    identifier="study001",
    title="My Study",
    description="...",
    submission_date=None,
    public_release_date=None,
)
```

### ArcAssay

```python
assay = ArcAssay.create(
    identifier="assay001",
    measurement_type=OntologyAnnotation("soil metagenome", "http://...", ""),
    technology_type=OntologyAnnotation("nucleotide sequencing", "http://...", ""),
    technology_platform=OntologyAnnotation("Illumina", None, None),  # platform is text; OA is allowed
    # technology_platform=None is fine if unknown
)
```

### Person

```python
person = Person(
    last_name="Doe",
    first_name="John",
    mid_initials="A",
    email="j.doe@example.com",
    phone="+49 123 456789",
    fax=None,
    address="Somewhere",
    affiliation="UFZ",
    roles=[OntologyAnnotation("author", "http://...", "")],
)
```

### Publication

```python
pub = Publication(
    doi="10.1234/example",
    pub_med_id="12345678",
    authors="Doe J, Smith A",
    title="Paper title",
    status=OntologyAnnotation("published", "http://...", ""),
)
```

---

## Building an ARC

```python
# 1. Wrap investigation
arc = ARC.from_arc_investigation(inv)

# 2. Add studies (registers them in the investigation)
arc.AddRegisteredStudy(study)

# 3. Add assays
arc.AddAssay(assay)

# 4. Link assay → study
study.RegisterAssay(assay.Identifier)   # pass the string identifier

# 5. Attach contacts
arc.Contacts.append(person)             # investigation-level
study.Contacts.append(person)           # study-level
assay.Performers.append(person)         # assay-level

# 6. Attach publications
arc.Publications.append(pub)            # investigation-level
study.Publications.append(pub)          # study-level

# 7. Serialize to RO-Crate JSON-LD string
json_str: str = arc.ToROCrateJsonString()
```

---

## ArcTable (Annotation Tables)

Tables attach to a study or assay.

```python
# Create table
table = ArcTable.init("my-table-name")

# Build a header
header_input  = CompositeHeader.input(IOType.of_string("source_name"))
header_output = CompositeHeader.output(IOType.of_string("sample_name"))
header_char   = CompositeHeader.characteristic(OntologyAnnotation("pH", "", ""))
header_factor = CompositeHeader.factor(OntologyAnnotation("temperature", "", ""))
header_param  = CompositeHeader.parameter(OntologyAnnotation("extraction", "", ""))
header_comp   = CompositeHeader.component(OntologyAnnotation("reagent", "", ""))
header_cmt    = CompositeHeader.comment("My comment label")
header_perf   = CompositeHeader.performer    # property, not callable
header_date   = CompositeHeader.date         # property, not callable
# Fallback for unknown/simple header names:
header_any    = CompositeHeader.OfHeaderString("SomeColumnName")

# IOType known strings (IOType.of_string):
# "source_name", "sample_name", "raw_data_file", "derived_data_file",
# "image_file", "material"

# Build cells (one per row, same order as rows in the table)
cell_text      = CompositeCell.free_text("some value")
cell_term      = CompositeCell.term(OntologyAnnotation("sandy loam", "http://...", ""))
cell_unitized  = CompositeCell.unitized("6.8", OntologyAnnotation("pH", "http://...", ""))
cell_empty     = CompositeCell.free_text("")

# Add column (header + matching cell list)
table.AddColumn(header_char, [cell_term, cell_term, cell_empty])

# Attach table to study or assay
study.AddTable(table)
assay.AddTable(table)
```

### CompositeHeader.IsTermColumn

```python
# Check before building a cell: if True, wrap plain values in OntologyAnnotation
if header.IsTermColumn:
    cell = CompositeCell.term(OntologyAnnotation(str(value), "", ""))
else:
    cell = CompositeCell.free_text(str(value))
```

---

## Reading Back / Deserializing

```python
# From RO-Crate JSON-LD string
arc = ARC.from_rocrate_json_string(json_str)

# Async write to directory (creates ISA file structure on disk)
# Must be awaited via start_as_task (Fable async bridge)
await start_as_task(arc.WriteAsync("/path/to/output/dir"))
```

---

## Identifiers

- `assay.Identifier` — string property, read-only after creation
- `study.Identifier`
- `arc.Identifier`

---

## Known Pitfalls

**`start_as_task` is untyped** — always add `# type: ignore[import-untyped]`
on the import. It is an internal Fable module and has no stubs.

**`CompositeHeader.performer` and `.date` are properties, not constructors**
— call them without `()`:

```python
# CORRECT
header = CompositeHeader.performer
# WRONG
header = CompositeHeader.performer()   # TypeError
```

**`OntologyAnnotation()` without args is valid** — use it for empty/unknown
ontology terms rather than `None` to avoid null-ref errors in the F# layer.

**ARC objects carry .NET interop state** — do not pickle them or transfer
them across multiprocessing boundaries. Always serialize to JSON string first.

**`ToROCrateJsonString()` + `gc.collect()`** — after serializing in a worker
process, explicitly `del arc` and call `gc.collect()` to release .NET bridge
memory promptly.

**`ArcAssay.create(technology_platform=None)`** — passing `None` is safe and
means "unknown platform". Passing an empty `OntologyAnnotation()` is also
accepted.

---

## RO-Crate JSON-LD Output Shape

```json
{
  "@context": { ... },
  "@graph": [
    { "@id": "inv001", "@type": "Dataset", "identifier": "inv001", ... },
    { "@id": "study001", "@type": "Dataset", ... },
    { "@id": "assay001", "@type": "Dataset", ... },
    { "@id": "#Doe_John", "@type": "Person", "familyName": "Doe", ... },
    ...
  ]
}
```

Useful for test assertions:

```python
graph = json.loads(arc.ToROCrateJsonString()).get("@graph", [])
inv_node = next(item for item in graph if item.get("identifier") == "inv001")
person   = next(item for item in graph if item.get("familyName") == "Doe")
```
