## ADDED Requirements

### Requirement: Ontology Source References From View Triples

When building an ARC, the system MUST create `OntologyAnnotation` objects only from ontology triples present in the
database views (term/uri/version fields, including contact role JSON). It MUST NOT invent annotation terms or URIs when
those fields are absent. When a triple includes a term-accession URI from which an ontology source short name can be
derived and includes an ontology version string, the system MUST register a corresponding `OntologySourceReference` on
the investigation (unique per source name and version) and MUST set the annotation’s TermSourceREF (`tsr`) to that
source name. When the source short name cannot be derived, the system MUST leave `tsr` empty and MUST NOT invent a
source name.

#### Scenario: Versioned URI yields OSR and tsr

- **GIVEN** a view ontology triple with a non-empty term, an OBO-style term-accession URI, and a non-empty version
- **WHEN** the ARC is built
- **THEN** an `OntologySourceReference` with that derived source name and version is present on the investigation
- **AND** the corresponding `OntologyAnnotation.tsr` equals that source name

#### Scenario: Missing term does not invent an annotation

- **GIVEN** an ontology triple with no term name
- **WHEN** mapping runs
- **THEN** the system does not invent a term or URI for that field
- **AND** behaviour matches the existing empty-annotation path

#### Scenario: Unparseable URI does not invent a source name

- **GIVEN** a triple with a URI that does not yield a source short name under the documented derivation rules
- **WHEN** mapping runs
- **THEN** `tsr` is empty
- **AND** no invented `OntologySourceReference` name is registered for that annotation

## MODIFIED Requirements

<!-- Mapping requirements stay; behaviour of ontology fields is extended by the ADDED requirement above. -->
