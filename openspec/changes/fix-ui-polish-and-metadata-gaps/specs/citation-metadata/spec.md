## ADDED Requirements

### Requirement: Citation Feature Parity with Main Branch
The citation response object returned by `format_document_for_citation()` in `backend/retrievers/base_retriever.py` SHALL include all fields present in the main branch version (`backend/retrievers/hansard_retriever.py:649-675`): `id`, `retrieval_id`, `title`, `url`, `date`, `page`, `corpus`, `text`, `quote`, `content`, `full_content`, `loc`, `weight`, `has_more`.

The feature branch improvements (dynamic filter_1/filter_2 corpus display, enrichment fields, 500-char content preview) SHALL be retained alongside the restored fields.

#### Scenario: Citation object contains all expected fields
- **WHEN** a document is formatted for citation display
- **THEN** the citation object SHALL include `id`, `retrieval_id`, `title`, `url`, `date`, `page`, `corpus`, `text`, `quote`, `content`, `full_content`, `loc`, `weight`, and `has_more`
- **AND** the `CitationList.vue` frontend component SHALL render citations correctly using these fields

#### Scenario: Dynamic corpus filter display preserved
- **WHEN** a document has `filter_1` and `filter_2` metadata fields
- **THEN** the `corpus` field in the citation SHALL display the combined filter values
- **AND** the legacy `corpus` metadata field SHALL still be supported as a fallback

### Requirement: Citation Source URL
The citation response object SHALL include `source_url` when present in document metadata, to support scholarly referencing. This field is not present on either the main or feature branch currently but is stored by `CitationEnricher`.

#### Scenario: Citation includes source_url when available
- **WHEN** a retrieved document has `source_url` in its metadata
- **THEN** the citation object SHALL include `source_url` as a top-level field
- **AND** the frontend SHALL render it as a clickable link

#### Scenario: Citation omits source_url when not available
- **WHEN** a retrieved document does not have `source_url` in its metadata
- **THEN** the citation object SHALL NOT include a `source_url` field
- **AND** the citation display SHALL remain unchanged
