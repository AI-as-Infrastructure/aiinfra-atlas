# Faceted Search Capability

## ADDED Requirements

### Requirement: Faceted Search Panel

The system SHALL provide a faceted search panel that renders metadata-driven filter controls based on the active corpus's facet configuration.

#### Scenario: Panel renders when facets are configured
- **GIVEN** the active corpus has a `facets` array in its manifest/corpus_active.json
- **WHEN** the chat interface loads
- **THEN** a faceted search panel is displayed in a dedicated UI area (not inline with the query input)
- **AND** each configured facet renders an appropriate control

#### Scenario: Panel hidden when no facets configured
- **GIVEN** a corpus built with the folder workflow (no facets in manifest)
- **WHEN** the chat interface loads
- **THEN** no faceted search panel is displayed
- **AND** the existing simple filter dropdowns remain functional

### Requirement: Text Facet Controls

The system SHALL render text-type facets as searchable dropdown controls with type-ahead filtering.

#### Scenario: Text facet with type-ahead
- **GIVEN** a text facet for "Sender" with 200+ distinct values
- **WHEN** the user types in the facet input
- **THEN** matching values are filtered and displayed as suggestions
- **AND** selecting a value adds it as an active filter

#### Scenario: Text facet clear
- **GIVEN** a text facet with an active selection
- **WHEN** the user clears the selection
- **THEN** the filter is removed from the active query
- **AND** subsequent searches are unrestricted on that facet

### Requirement: Date Range Facet Controls

The system SHALL render date-type facets as date range inputs (from/to) that generate ChromaDB `$gte`/`$lte` query clauses.

#### Scenario: Date range filtering
- **GIVEN** a date range facet for "Date" with min "1821-01-01" and max "1882-04-19"
- **WHEN** the user sets from="1859-01-01" and to="1859-12-31"
- **THEN** the system generates a ChromaDB where clause with `$gte` and `$lte` operators on the `tei_date` field
- **AND** only chunks with dates in the specified range are returned

#### Scenario: Partial date range
- **GIVEN** a date range facet
- **WHEN** the user sets only a "from" date without a "to" date
- **THEN** the system generates a `$gte` clause only
- **AND** all chunks from that date onward are included

### Requirement: Keyword Facet Controls

The system SHALL render keyword-type facets as multi-select controls that generate ChromaDB `$or` query clauses.

#### Scenario: Multi-select keyword filtering
- **GIVEN** a keyword facet for "Subject" with values like "natural selection", "geology", "botany"
- **WHEN** the user selects multiple keywords
- **THEN** the system generates a ChromaDB where clause matching chunks containing any of the selected keywords
- **AND** results include chunks matching at least one selected keyword

#### Scenario: Keyword facet with no selection
- **GIVEN** a keyword facet with no active selections
- **WHEN** a search is executed
- **THEN** no keyword filter is applied
- **AND** all chunks are eligible regardless of keywords

### Requirement: Combined Facet Filtering

The system SHALL combine active facets using ChromaDB's `$and` operator, so all active filters must match simultaneously.

#### Scenario: Multiple facets active simultaneously
- **GIVEN** the user has set sender="Charles Robert Darwin", date range 1859-1860, and keyword="natural selection"
- **WHEN** a search is executed
- **THEN** the system constructs a ChromaDB `$and` clause combining all active facet filters
- **AND** only chunks matching all criteria are returned

#### Scenario: Facets combined with text query
- **GIVEN** the user has active facet filters and enters a text query
- **WHEN** the search executes
- **THEN** the facet filters constrain the vector similarity search via ChromaDB `where` clause
- **AND** the text query drives the semantic similarity ranking within the filtered set

### Requirement: Facet Configuration in Corpus Active

The `corpus_active.json` file SHALL include facet configuration from the manifest, making facet metadata available to the frontend at runtime.

#### Scenario: Facets propagated to corpus_active.json
- **GIVEN** a manifest with facet configuration
- **WHEN** the system enters deploy mode and creates corpus_active.json
- **THEN** the facets array is included in corpus_active.json
- **AND** the frontend can read facet configuration from the `/api/config` endpoint

#### Scenario: Frontend fetches facet configuration
- **GIVEN** the chat interface initialises
- **WHEN** it requests configuration from `/api/config`
- **THEN** the response includes available facets with their types and values
- **AND** the faceted search panel renders accordingly
