# Change: Add TEI-XML Corpus Ingestion Workflow

## Why

ATLAS currently treats XML files as plain text via `UnstructuredXMLLoader`, discarding all structural markup and metadata. For TEI-XML corpora — the dominant scholarly encoding standard — this wastes rich, machine-readable metadata (correspondents, dates, places, subject keywords, abstracts) that would dramatically improve RAG retrieval quality through better chunk context and faceted filtering. The corpus wizard already has a disabled "XML Workflow" placeholder in Step 1, signalling this was always planned.

## What Changes

### Backend: TEI-XML Processing

- **New module `tei_xml_parser.py`**: Parses TEI-XML documents, extracts `teiHeader` metadata (correspDesc, profileDesc, textClass, abstract), and produces structured metadata dictionaries. Corpus-agnostic — discovers available TEI elements at analysis time rather than hardcoding field names.
- **New module `tei_chunking.py`**: XML-aware chunking with two strategies:
  - **Structural chunking**: Splits on TEI structural elements (`<div>`, `<p>`, `<body>` sections) preserving document boundaries
  - **Whole-document chunking**: Treats each TEI document as a single chunk (suited for short documents like letters)
  - Both strategies prepend extracted metadata (sender, date, place, abstract) to chunk text so the LLM receives contextual information alongside content
- **Modified `corpus_builder.py`**: Routes XML workflow through TEI-specific pipeline instead of `UnstructuredXMLLoader`. Writes TEI-extracted metadata fields into ChromaDB chunk metadata for filtering.
- **Modified `corpus_analyzer.py`**: Enhanced XML analysis to discover TEI schema elements and report available metadata fields, informing wizard step configuration.

### Wizard: New TEI-Specific Steps

- **Modified Step 1 (Workflow)**: Enable XML Workflow option. When selected, triggers TEI-specific analysis and steps.
- **New Step: TEI Schema Discovery** (after source selection): Scans uploaded TEI-XML files, reports discovered metadata elements (e.g., `correspDesc/sender`, `date[@when]`, `textClass/keywords`), and lets users confirm which fields to extract.
- **New Step: Metadata Mapping**: Users map discovered TEI fields to chunk metadata roles (e.g., `correspAction[@type='sent']/persName` → "sender", `date[@when]` → "date"). Pre-populated with sensible defaults for common TEI patterns.
- **New Step: Chunking Strategy**: Users choose structural vs whole-document chunking, with preview showing chunk boundaries and prepended metadata.
- **New Step: Filter Configuration**: Users select which metadata fields become searchable facets (e.g., date ranges, sender/recipient selection, subject keywords). Configures ChromaDB metadata indexing.

### Frontend: Faceted Search Panel

- **New component `FacetedSearch.vue`**: Replaces simple filter dropdowns with a multi-facet search panel. Supports:
  - Text facets (sender, recipient) with type-ahead search
  - Date range facets using ChromaDB `$gte`/`$lte` operators
  - Keyword/tag facets with multi-select
  - Combined filtering via ChromaDB `$and` operator
- **Modified `UserInput.vue`**: Renders faceted search panel in a dedicated location (not inline with query input) when corpus metadata supports faceted filtering.
- **Modified manifest/corpus_active.json**: Extended to declare available facets and their types, so the frontend knows what filtering UI to render.

### Retrieval: Metadata-Enhanced Filtering

- **Modified retriever template**: Constructs ChromaDB `where` clauses using `$and`, `$or`, `$gte`, `$lte` operators based on active facets. Falls back to simple equality filtering for non-TEI corpora.
- **Modified `base_retriever.py`**: `format_document_for_citation()` extended to surface TEI metadata fields in citations (sender, date, place, etc.).
- **Manifest schema v1.5**: New `facets` array in manifest declaring filterable fields, their types (text, date, keyword), and available values.

## Impact

- Affected specs: New capabilities (`tei-xml-ingestion`, `faceted-search`, `metadata-enhanced-retrieval`)
- Affected code:
  - New: `backend/modules/tei_xml_parser.py`, `backend/modules/tei_chunking.py`, `frontend/src/components/FacetedSearch.vue`
  - Modified: `backend/modules/corpus_builder.py`, `backend/modules/corpus_analyzer.py`, `backend/modules/corpus_config.py`, `backend/retrievers/templates/corpus_retriever_template.py`, `backend/retrievers/base_retriever.py`, `frontend/src/pages/CorpusWizard.vue`, `frontend/src/components/UserInput.vue`
  - Config: `backend/corpus/manifest.json` (schema v1.5), `backend/corpus/corpus_active.json` (extended)
- **BREAKING**: None. Existing folder-based workflow unchanged. TEI-XML is a new workflow path. Simple filter dropdowns remain as fallback for non-faceted corpora.

## Alternatives Considered

1. **Generic XML parser first**: Build a universal XML parser that works with any schema.
   - Rejected: TEI-XML is the dominant scholarly standard and has well-defined metadata conventions. Generic XML parsing would require users to manually specify all structure, losing the benefit of intelligent defaults. A generic workflow can be added later.

2. **XSLT preprocessing**: Transform TEI-XML to plain text with metadata via XSLT stylesheets before ingestion.
   - Rejected: Adds an external dependency and a complex intermediate step. Direct Python parsing with `lxml` is simpler and allows tighter integration with the wizard's interactive metadata mapping.

3. **Keep metadata only in chunk text (no ChromaDB metadata)**: Prepend metadata to text without storing it separately in ChromaDB.
   - Rejected: Prevents faceted filtering. Both approaches are needed: metadata in chunk text for LLM context, and metadata in ChromaDB fields for search-time filtering.

4. **Advanced filter dropdowns instead of faceted search panel**: Extend existing dropdowns with more options.
   - Rejected: Date ranges, multi-select keywords, and type-ahead search don't fit dropdown UIs. A dedicated faceted search panel provides a better user experience and scales to arbitrary metadata complexity.

## Security Considerations

- XML parsing uses `lxml` with `defusedxml` or equivalent XXE protection (no external entity resolution)
- User-provided TEI-XML files are validated for well-formedness before processing
- Metadata field names are sanitised before use as ChromaDB metadata keys

## Testing Strategy

1. Unit tests for TEI parser against Darwin corpus samples and synthetic TEI documents
2. Unit tests for structural and whole-document chunking strategies
3. Integration tests for wizard flow with TEI-XML corpus
4. Integration tests for faceted search query construction and ChromaDB filtering
5. Manual testing with Darwin corpus (15,239 TEI-XML letters) as primary test dataset
6. Verify backward compatibility: existing folder-based workflow must work unchanged

## Implementation Priority

High — This is the next major feature for the corpus wizard, enabling ATLAS to exploit structured scholarly corpora for significantly better RAG retrieval quality.
