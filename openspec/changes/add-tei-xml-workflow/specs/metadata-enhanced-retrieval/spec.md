# Metadata-Enhanced Retrieval Capability

## ADDED Requirements

### Requirement: Advanced ChromaDB Query Construction

The retriever SHALL construct ChromaDB `where` clauses using `$and`, `$or`, `$gte`, and `$lte` operators based on active facet selections.

#### Scenario: Date range query construction
- **GIVEN** the user has set a date range facet with from="1859-01-01" and to="1859-12-31"
- **WHEN** the retriever constructs the ChromaDB query
- **THEN** the `where` clause includes `{"$and": [{"tei_date": {"$gte": "1859-01-01"}}, {"tei_date": {"$lte": "1859-12-31"}}]}`

#### Scenario: Combined facet query construction
- **GIVEN** the user has active text, date range, and keyword facets
- **WHEN** the retriever constructs the ChromaDB query
- **THEN** all facet conditions are combined under a top-level `$and` operator
- **AND** keyword multi-select uses `$or` for values within that facet

#### Scenario: No facets active falls back to simple filtering
- **GIVEN** no facet filters are active
- **WHEN** the retriever constructs the query
- **THEN** the existing simple `filter_1`/`filter_2` equality filtering is used
- **AND** no advanced operators are included

### Requirement: Backward-Compatible Filter Handling

The retriever SHALL maintain backward compatibility with existing simple filter dropdowns when the corpus does not have facet configuration.

#### Scenario: Non-faceted corpus uses simple filters
- **GIVEN** a corpus built with the folder workflow (no facets in manifest)
- **WHEN** the user selects a filter from the existing dropdown
- **THEN** the retriever applies simple equality filtering on `filter_1`
- **AND** the retrieval behaviour is identical to the current implementation

#### Scenario: Faceted corpus supports both filter modes
- **GIVEN** a TEI-XML corpus with facet configuration
- **WHEN** the user uses faceted search controls
- **THEN** advanced ChromaDB operators are used
- **AND** the simple filter dropdowns are replaced by the faceted search panel

### Requirement: TEI Metadata in Citations

The citation display SHALL include TEI metadata fields (sender, recipient, date, place) when available in the retrieved chunk's metadata.

#### Scenario: Citation includes TEI metadata
- **GIVEN** a retrieved chunk from a TEI-XML corpus with `tei_sender`, `tei_date`, and `tei_place` metadata
- **WHEN** the citation is formatted for display
- **THEN** the citation includes sender, date, and place information
- **AND** the metadata is presented in a readable format

#### Scenario: Citation falls back for non-TEI chunks
- **GIVEN** a retrieved chunk without TEI metadata fields
- **WHEN** the citation is formatted
- **THEN** the existing citation format is used
- **AND** no TEI-specific fields are displayed

### Requirement: Faceted Search API Endpoint

The system SHALL provide an API endpoint that returns the active corpus's facet configuration for the frontend to consume.

#### Scenario: Facet configuration returned via API
- **GIVEN** a deployed corpus with facet configuration
- **WHEN** the frontend requests `/api/config` or `/api/retriever/filters`
- **THEN** the response includes the facets array with field names, labels, types, and available values
- **AND** the frontend can render appropriate filter controls

#### Scenario: API returns empty facets for non-TEI corpus
- **GIVEN** a deployed corpus without facet configuration
- **WHEN** the frontend requests facet information
- **THEN** the facets array is empty or absent
- **AND** the frontend renders simple filter dropdowns as before

## MODIFIED Requirements

### Requirement: Retriever Template Filter Construction

The retriever template SHALL construct ChromaDB `where` clauses that support both simple equality filters and advanced operators (`$and`, `$or`, `$gte`, `$lte`).

#### Scenario: Simple filter for backward compatibility
- **GIVEN** a query with `filter_1` set to a corpus name
- **WHEN** no faceted filters are active
- **THEN** the retriever uses `filter={"filter_1": value}` as currently implemented

#### Scenario: Advanced filter from faceted search
- **GIVEN** a query with multiple faceted filter selections
- **WHEN** the retriever processes the query
- **THEN** it constructs a `where` clause using `$and` to combine all filter conditions
- **AND** date ranges use `$gte`/`$lte` and keyword multi-select uses `$or`

### Requirement: Citation Metadata Formatting

The `format_document_for_citation()` function SHALL include TEI-specific metadata fields when present in chunk metadata.

#### Scenario: TEI metadata included in citation output
- **GIVEN** a document chunk with `tei_sender`, `tei_recipient`, `tei_date`, and `tei_place` metadata
- **WHEN** `format_document_for_citation()` processes the chunk
- **THEN** the citation output includes these fields with human-readable labels
- **AND** existing metadata fields (corpus, corpus_label, source_url) remain present
