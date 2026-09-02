## MODIFIED Requirements

### Requirement: Upload Built ARCs

The pipeline MUST upload successfully built ARCs to the Middleware API
through the harvest-session upload path defined in `api-upload` (one harvest
per RDI run via `harvest_arcs`, not per-investigation `create_or_update_arc`).

#### Scenario: Successful builds enter one harvest

- **GIVEN** one or more workers returned non-empty ARC JSON strings
- **WHEN** the upload phase runs
- **THEN** those ARCs are submitted within a single harvest session for the configured RDI
- **AND** `create_or_update_arc` is not used
