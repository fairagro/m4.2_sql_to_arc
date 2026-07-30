## MODIFIED Requirements

### Requirement: Validate Rows With Pydantic

The system MUST validate each row against its Pydantic model. Invalid
investigation rows MUST be skipped with a warning and MUST be recorded as
failed on the shared repository scope (message plus best-effort identifier).
Invalid related-entity rows that are skipped MUST follow the same failure
recording rules where those rows represent abandoned datasets; otherwise they
MUST NOT invent harvested counts.

#### Scenario: Investigation row fails validation

- **GIVEN** an investigation row that fails Pydantic validation
- **WHEN** it is mapped
- **THEN** it is skipped
- **AND** a warning with field errors is logged
- **AND** the shared repository scope records a failed dataset for it
