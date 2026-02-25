## Context

ATLAS processes corpora through a wizard-driven build pipeline. The current pipeline treats XML as plain text (`UnstructuredXMLLoader`), losing all structural and metadata information. TEI-XML (Text Encoding Initiative P5) is the dominant encoding standard for scholarly digital texts, with well-defined conventions for correspondence metadata (`correspDesc`), subject classification (`textClass`), dates, persons, and places.

The Darwin Correspondence Project corpus (`source_examples/Darwin/`, 15,239 TEI-XML letters) demonstrates the richness available: each letter has sender, recipient, date, place, subject keywords, and abstract — none of which reaches the current vector store.

### Stakeholders
- Digital humanities researchers building TEI-XML corpora
- Users of the ATLAS wizard who want richer filtering and retrieval
- Maintainers of the corpus builder pipeline

### Constraints
- Must not break existing folder-based workflow
- ChromaDB 1.0.15 is the current vector store (supports `$and`, `$or`, `$gte`, `$lte`, `$in` operators)
- `lxml` already available in project dependencies
- Frontend uses Vue 3 + Bulma CSS framework
- Wizard uses `currentStep` ref with `v-if` conditional rendering (not a router)

## Goals / Non-Goals

### Goals
- Parse TEI-XML documents preserving structural and metadata information
- Provide wizard steps for interactive metadata discovery, mapping, and filter configuration
- Prepend extracted metadata to chunk text so LLMs receive contextual information
- Store metadata in ChromaDB fields enabling faceted search at query time
- Build a faceted search UI supporting date ranges, multi-select, and type-ahead
- Work with any TEI-XML corpus, not just Darwin (corpus-agnostic discovery)

### Non-Goals
- Generic XML support (future work — TEI-first)
- Full TEI schema validation (we parse what's available, skip what's missing)
- Custom embedding models for metadata fields (use same model for all text)
- Server-side search (filtering is client-side ChromaDB `where` clauses, not a search engine)
- Modifying the existing folder-based workflow

## Decisions

### Decision 1: TEI Parser Architecture

**Decision**: Single `tei_xml_parser.py` module using `lxml.etree` with namespace-aware XPath queries. Discovery-based approach: scan corpus sample to identify available TEI elements, then extract based on discovered schema.

**Rationale**: TEI-XML has a large schema but individual corpora use subsets. Discovery avoids hardcoding Darwin-specific paths while still providing intelligent defaults for common patterns (correspDesc, textClass, profileDesc).

**Alternatives considered**:
- `BeautifulSoup`: Slower, less XPath support. `lxml` is already a project dependency.
- `xml.etree.ElementTree`: No namespace support, no XPath. Insufficient for TEI.
- Hardcoded field extraction: Would only work for Darwin. Rejected for corpus-agnosticism.

### Decision 2: Metadata Prepending Strategy

**Decision**: Prepend a structured text block to each chunk before embedding:
```
[Metadata]
Sender: Charles Robert Darwin
Recipient: Joseph Dalton Hooker
Date: 1859-03-15
Place: Down
Keywords: natural selection, species theory
Abstract: Discussion of species distribution...
[/Metadata]

[Content]
<actual chunk text>
[/Content]
```

**Rationale**: Embedding models encode the full text including metadata, meaning semantic search queries like "Darwin's letters about natural selection from Down" will match chunks with relevant metadata. The structured format is parseable if needed but primarily serves the LLM's context window.

**Alternatives considered**:
- JSON prefix: Less readable for LLMs, adds token overhead with braces/quotes.
- Separate metadata embeddings: Doubles storage, requires fusion at retrieval time. Over-engineered.
- Metadata only in ChromaDB fields (not in text): LLM wouldn't see metadata in context, reducing answer quality.

### Decision 3: Chunking Strategies

**Decision**: Support two chunking modes, selectable in wizard:

1. **Structural chunking**: Split on TEI structural elements (`<div>`, `<p>`, `<body>` children). Merge small adjacent chunks up to configurable size. Each chunk inherits the document's header metadata.

2. **Whole-document chunking**: One chunk per TEI document. Best for short documents (letters, poems) where splitting would lose coherence.

Both modes prepend metadata identically.

**Rationale**: The Darwin corpus has letters ranging from one paragraph to several pages. Short letters should stay whole; long documents benefit from structural splitting. User choice in the wizard accommodates both patterns.

### Decision 4: ChromaDB Metadata Schema

**Decision**: Store TEI metadata in ChromaDB chunk metadata using typed fields:

```python
{
    "chunk_id": "DCP-LETT-1234-001",
    "corpus": "darwin_correspondence",
    "filter_1": "Charles Robert Darwin",        # backward-compat sender
    "filter_2": "Joseph Dalton Hooker",          # backward-compat recipient
    "tei_sender": "Charles Robert Darwin",
    "tei_recipient": "Joseph Dalton Hooker",
    "tei_date": "1859-03-15",                    # ISO 8601 string for $gte/$lte
    "tei_place": "Down",
    "tei_keywords": "natural selection; species theory",  # semicolon-delimited
    "source_filename": "DCP-LETT-1234.xml",
    "date": "1859-03-15",
    "source_url": ""
}
```

**Rationale**:
- `tei_` prefix avoids collision with existing metadata fields
- `filter_1`/`filter_2` populated for backward compatibility with existing dropdown UI
- Date as ISO 8601 string enables `$gte`/`$lte` range queries (ChromaDB string comparison works for ISO dates)
- Keywords semicolon-delimited for `$contains` substring matching (ChromaDB limitation: no array metadata)

**Alternatives considered**:
- Nested metadata objects: ChromaDB only supports flat key-value metadata. Not possible.
- Integer timestamps for dates: Less readable, harder to debug. ISO string comparison works for date ranges.

### Decision 5: Faceted Search UI Architecture

**Decision**: New `FacetedSearch.vue` component rendered in a collapsible panel above or beside the chat input (not inline with the query box). Component reads facet configuration from `corpus_active.json` and constructs ChromaDB `where` clauses.

Facet types:
- **Text facet** (sender, recipient): Dropdown with type-ahead, populated from manifest's distinct values
- **Date range facet**: Two date inputs (from/to), generates `$gte`/`$lte` clause
- **Keyword facet**: Multi-select checkboxes, generates `$or` clause with `$contains`
- **Combined**: All active facets joined with `$and`

**Rationale**: Faceted search is a standard pattern for structured metadata. The panel must be separate from the query input because it represents a different interaction mode (filtering context vs asking questions). The component is data-driven — it renders based on what facets are declared in the manifest, making it corpus-agnostic.

**Alternatives considered**:
- Sidebar panel: Takes horizontal space on smaller screens. Collapsible top panel is more responsive.
- Query syntax (e.g., `sender:Darwin`): Requires users to learn syntax. Explicit UI facets are more discoverable.

### Decision 6: Manifest Schema Extension (v1.5)

**Decision**: Add a `facets` array to `manifest.json`:

```json
{
    "version": "1.5",
    "facets": [
        {
            "field": "tei_sender",
            "label": "Sender",
            "type": "text",
            "values": ["Charles Robert Darwin", "Joseph Dalton Hooker", "..."]
        },
        {
            "field": "tei_date",
            "label": "Date",
            "type": "date_range",
            "min": "1821-01-01",
            "max": "1882-04-19"
        },
        {
            "field": "tei_keywords",
            "label": "Subject",
            "type": "keyword",
            "values": ["natural selection", "geology", "botany", "..."]
        }
    ]
}
```

This propagates to `corpus_active.json` at deploy time, making facet configuration available to the frontend.

**Rationale**: The manifest already records corpus configuration. Adding facets here means the frontend can render appropriate filter UI without hardcoding field names. The `values` arrays are populated during build from actual corpus data.

### Decision 7: XML Security

**Decision**: Use `lxml` with XXE (XML External Entity) protection disabled. Specifically:
- Parse with `lxml.etree.XMLParser(resolve_entities=False, no_network=True)`
- Reject DTD processing
- Validate well-formedness before full parsing

**Rationale**: TEI-XML files from scholarly projects may contain entity declarations. Disabling external entity resolution prevents XXE attacks while still parsing the document content correctly.

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Large TEI corpora slow wizard analysis | Medium | Sample-based discovery (analyse first N files, not all) |
| ChromaDB string date comparison edge cases | Low | Enforce ISO 8601 format during ingestion; validate in parser |
| Keyword `$contains` false positives | Low | Use semicolon delimiter; document limitation |
| Faceted search panel clutters UI for simple corpora | Medium | Panel only renders when facets exist in manifest; collapsible |
| TEI namespace variations across corpora | Medium | Support both default namespace and explicit `tei:` prefix |
| Memory pressure with large XML files | Low | Stream-parse with `lxml.iterparse` for file discovery; full parse only for metadata extraction |

## Migration Plan

No migration needed — this is additive functionality. Existing corpora built with the folder workflow continue to work unchanged. The simple filter dropdowns remain for corpora without facet configuration.

### Rollback
Remove the TEI workflow option from Step 1 to disable the feature entirely. No data migration required.

## Open Questions

1. **Facet panel placement**: Should it be a collapsible section above the chat, a sidebar, or a modal? Needs UX review during implementation.
2. **Maximum facet values**: For fields with thousands of distinct values (e.g., all Darwin correspondents), should we cap the dropdown and require type-ahead? Likely yes — implementation detail.
3. **TEI namespace handling**: Some corpora use `xmlns="http://www.tei-c.org/ns/1.0"`, others use unnamespaced elements. Need to handle both at parse time.
