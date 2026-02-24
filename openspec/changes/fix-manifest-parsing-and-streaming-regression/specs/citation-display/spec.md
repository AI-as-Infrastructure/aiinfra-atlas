# Citation Display

## MODIFIED Requirements

### Requirement: Citations MUST display complete metadata in the frontend

The citation pipeline MUST deliver structured citation objects with all fields expected by CitationList.vue: text, quote, url, source_url, retrieval_id, full_content. Citations MUST render correctly in both the collapsed preview and the expanded modal view.

#### Scenario: User receives a response with structured citations

Given a successful query response with retrieved documents containing metadata (url, title, date, source_url)
When the response completes and citations are displayed
Then each citation shows text/quote content, a clickable link when url is present, retrieval_id in the expanded view, and source_url as a clickable link when available
