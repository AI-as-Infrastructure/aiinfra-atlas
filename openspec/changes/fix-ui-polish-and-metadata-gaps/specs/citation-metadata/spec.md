## ADDED Requirements

### Requirement: Citation Source URL
The citation response object returned by `format_document_for_citation()` SHALL explicitly include the `source_url` field when present in the document metadata, to support scholarly referencing and provenance tracking.

#### Scenario: Citation includes source_url when available
- **WHEN** a retrieved document has `source_url` in its metadata
- **THEN** the citation object SHALL include `source_url` as a top-level field
- **AND** the frontend SHALL render it as a clickable link

#### Scenario: Citation omits source_url when not available
- **WHEN** a retrieved document does not have `source_url` in its metadata
- **THEN** the citation object SHALL NOT include a `source_url` field
- **AND** the citation display SHALL remain unchanged

#### Scenario: Feature parity with main branch citations
- **WHEN** comparing citation metadata on the feature branch with main
- **THEN** all metadata fields surfaced on main SHALL also be surfaced on the feature branch
