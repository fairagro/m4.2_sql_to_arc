---
name: arctrl
description: >
  Reference for using the arctrl Python library (v3.x) to build ARC (Annotated
  Research Context) objects and serialize them to RO-Crate JSON-LD. Use when
  working with ArcInvestigation, ArcStudy, ArcAssay, ArcTable, CompositeHeader,
  CompositeCell, OntologyAnnotation, OntologySourceReference, Person, or
  Publication objects, or when calling ToROCrateJsonString / WriteAsync.
compatibility: Python 3.12+, arctrl (Fable-transpiled F# library)
---

# ARCtrl — Usage Reference

ARCtrl is a Fable-transpiled F# library — the Python surface is idiomatic
but some internals are Fable runtime types.

---

## Package & Imports

arctrl ships no type stubs and no `py.typed` marker. Mypy will report
`[import-untyped]` for every `arctrl.*` import unless you suppress it.

**Preferred: project-level override in `pyproject.toml`** (no per-import
comments needed, covers all submodules):

```toml
[[tool.mypy.overrides]]
module = ["arctrl", "arctrl.*"]
ignore_missing_imports = true
```

The `arctrl.*` glob is required because the Fable-transpiled internals are
exposed under `arctrl.py.*` subpackages (e.g.
`arctrl.py.Core.Table.composite_cell`), which are a different dotted path
from the bare `arctrl` package.

**Alternative: per-import suppression** (only needed when the project-level
override is not in place):

```python
from arctrl.py.Core.Table.composite_cell import Data  # type: ignore[import-untyped]
```

---

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
    start_as_task,  # re-exported from fable_library (arctrl ≥3.2)
)
```

---

## Core Objects

### OntologyAnnotation

```python
# Empty / unknown
oa = OntologyAnnotation()

# With values — all parameters optional:
oa = OntologyAnnotation(
    name="soil texture",  # human-readable term
    tan="http://purl.obolibrary.org/obo/ENVO_00002001",  # TermAccessionNumber (URI)
    tsr="ENVO",  # TermSourceREF: short name of the ontology source
)
# tsr is a back-reference to an OntologySourceReference registered on the
# investigation (by its .Name). If no OntologySourceReference is registered,
# tsr can be left empty or omitted.
```

### OntologySourceReference

Registered on `ArcInvestigation.OntologySourceReferences`. Describes an
ontology source and holds its version.

```python
from arctrl import OntologySourceReference

osr = OntologySourceReference(
    name="ENVO",  # short name — must match OntologyAnnotation.tsr
    description="Environment Ontology",
    file="http://purl.obolibrary.org/obo/envo.owl",
    version="2024-01-01",  # ontology version / access date
)
investigation.OntologySourceReferences.append(osr)
```

**Relationship:** `OntologyAnnotation.tsr` is a string key that references
`OntologySourceReference.name`. ARCtrl does not enforce referential integrity
at runtime, but the RO-Crate serialization will include both objects.

### ArcInvestigation

```python
inv = ArcInvestigation.create(
    identifier="inv001",  # required, must be non-empty
    title="My Investigation",
    description="...",
    submission_date="2024-01-15",  # ISO string or None
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
    technology_platform=OntologyAnnotation("Illumina", None, None),
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
study.RegisterAssay(assay.Identifier)  # pass the string identifier

# 5. Attach contacts
arc.Contacts.append(person)  # investigation-level
study.Contacts.append(person)  # study-level
assay.Performers.append(person)  # assay-level

# 6. Attach publications
arc.Publications.append(pub)  # investigation-level
study.Publications.append(pub)  # study-level

# 7. Serialize to RO-Crate JSON-LD string
json_str: str = arc.ToROCrateJsonString()
```

---

## ArcTable (Annotation Tables)

```python
# arctrl ≥3.2: CompositeHeader / IOType / CompositeCell are TypeAliases on
# `from arctrl import …`. Use a case class for factories:
from arctrl.py.Core.Table.composite_header import CompositeHeader_Output as CompositeHeader
from arctrl.py.Core.Table.composite_header import IOType_Data as IOType
from arctrl.py.Core.Table.composite_cell import CompositeCell_FreeText as CompositeCell

# Create table
table = ArcTable.init("my-table-name")

# Build headers
header_input = CompositeHeader.input(IOType.of_string("Source Name"))
header_output = CompositeHeader.output(IOType.of_string("Sample Name"))
header_char = CompositeHeader.characteristic(OntologyAnnotation("pH", "", ""))
header_factor = CompositeHeader.factor(OntologyAnnotation("temperature", "", ""))
header_param = CompositeHeader.parameter(OntologyAnnotation("extraction", "", ""))
header_comp = CompositeHeader.component(OntologyAnnotation("reagent", "", ""))
header_cmt = CompositeHeader.comment("My comment label")
header_perf = CompositeHeader.performer()  # factory — call it
header_date = CompositeHeader.date()  # factory — call it
# Fallback for unknown/simple header names:
header_any = CompositeHeader.OfHeaderString("SomeColumnName")

# IOType canonical strings recognised by IOType.of_string() (maps to named tags 0-3):
# "Source Name" / "Source"  → tag 0 (Source)
# "Sample Name" / "Sample"  → tag 1 (Sample)
# "Data" / "RawDataFile" / "Raw Data File" / "DerivedDataFile" /
# "Derived Data File" / "ImageFile" / "Image File"  → tag 2 (Data)
# "Material"                → tag 3 (Material)
# Any other string          → tag 4 (FreeType — avoid for ISA compliance)

# Build cells
cell_text = CompositeCell.free_text("some value")
cell_term = CompositeCell.term(OntologyAnnotation("sandy loam", "http://...", ""))
cell_unitized = CompositeCell.unitized("6.8", OntologyAnnotation("pH", "http://...", ""))
cell_empty = CompositeCell.free_text("")

# Add column (header + matching cell list)
table.AddColumn(header_char, [cell_term, cell_term, cell_empty])

# Check whether a header expects a term cell
if header.IsTermColumn:
    cell = CompositeCell.term(OntologyAnnotation(str(value), "", ""))
else:
    cell = CompositeCell.free_text(str(value))

# Attach table to study or assay
study.AddTable(table)
assay.AddTable(table)
```

---

## Reading Back / Deserializing

```python
# From RO-Crate JSON-LD string
arc = ARC.from_rocrate_json_string(json_str)

# Async write to directory (creates ISA file structure on disk)
await start_as_task(arc.WriteAsync("/path/to/output/dir"))
```

---

## Identifiers

- `assay.Identifier` — string property, read-only after creation
- `study.Identifier`
- `arc.Identifier`

---

## Known Pitfalls

**`start_as_task`** — import from `arctrl` (re-exported since 3.2). The old
path `arctrl.py.fable_modules.fable_library.async_` no longer exists.

**`CompositeHeader` / `IOType` / `CompositeCell` TypeAliases (arctrl ≥3.2)** —
`from arctrl import CompositeHeader` is annotation-only. Factory methods
(`.input`, `.output`, `.of_string`, `.free_text`, …) live on case classes such
as `CompositeHeader_Output`, `IOType_Data`, `CompositeCell_FreeText`. Alias one
of those at import time for runtime use.

**`CompositeHeader.performer` and `.date` are factories** — call them with `()`:

```python
header = CompositeHeader.performer()
header = CompositeHeader.date()
```

**`OntologyAnnotation()` without args is valid** — use for empty/unknown terms
instead of `None` to avoid null-ref errors in the F# layer.

**ARC objects carry .NET interop state** — do not pickle or transfer across
multiprocessing boundaries. Serialize to JSON string first.

**`ToROCrateJsonString()` + `gc.collect()`** — after serializing in a worker
process, explicitly `del arc` and call `gc.collect()` to release .NET bridge
memory promptly.

**`ArcAssay.create(technology_platform=None)`** — `None` is safe. An empty
`OntologyAnnotation()` is also accepted.

---

## RO-Crate JSON-LD Output Shape

```json
{
  "@context": { "...": "..." },
  "@graph": [
    { "@id": "inv001", "@type": "Dataset", "identifier": "inv001" },
    { "@id": "study001", "@type": "Dataset" },
    { "@id": "assay001", "@type": "Dataset" },
    { "@id": "#Doe_John", "@type": "Person", "familyName": "Doe" }
  ]
}
```

Test assertion pattern:

```python
graph = json.loads(arc.ToROCrateJsonString()).get("@graph", [])
inv_node = next(item for item in graph if item.get("identifier") == "inv001")
person = next(item for item in graph if item.get("familyName") == "Doe")
```
