# Tasks: Add TEI-XML Corpus Ingestion Workflow

## Phase 1: TEI Parser and Chunking (backend foundation)

- [x] 1. Create `backend/modules/tei_xml_parser.py`: namespace-aware TEI parsing with `lxml`, XXE protection, metadata extraction (correspDesc, textClass, abstract, titleStmt), corpus-agnostic field discovery
- [x] 2. Create `backend/modules/tei_chunking.py`: structural chunking (split on `<div>`/`<p>` boundaries with merge) and whole-document chunking, metadata prepending to chunk text with `[Metadata]`/`[Content]` delimiters
- [x] 3. Add unit tests for TEI parser: test against Darwin corpus samples, test namespace handling (with/without TEI namespace), test missing fields, test XXE rejection, test malformed XML (33 tests, all passing)
- [x] 4. Add unit tests for TEI chunking: structural split with merge, whole-document mode, metadata prepending format, chunk metadata fields (`tei_` prefix) (28 tests, all passing)

## Phase 2: Schema Discovery and Corpus Builder Integration

- [x] 5. Add TEI schema discovery to `corpus_analyzer.py`: sample-based scanning of TEI-XML files, report available teiHeader elements with frequency/coverage, distinguish TEI from generic XML
- [x] 6. Modify `corpus_builder.py`: route XML workflow through TEI pipeline (parser + chunker), populate ChromaDB metadata with `tei_` prefixed fields and backward-compat `filter_1`/`filter_2`, skip `UnstructuredXMLLoader` for TEI
- [x] 7. Update `corpus_config.py`: add Pydantic models for TEI workflow configuration (selected metadata fields, chunking strategy, metadata mappings, filter facet selections)
- [x] 8. Add integration tests: build a small TEI corpus end-to-end through the pipeline, verify ChromaDB metadata fields, verify chunk text includes prepended metadata (33 tests, 27 passed, 6 skipped due to torch dependency)

## Phase 3: Manifest and Configuration Extension

- [x] 9. Extend manifest schema to v1.5: add `facets` array (field, label, type, values/min/max), populate facets from build-time corpus metadata analysis
- [x] 10. Update `manifest_loader.py`: load and expose facet configuration via `get_facets()` and `has_facets()`
- [x] 11. Update `corpus_active.json` generation in `mode.py`: include facets array from manifest when present
- [x] 12. Add tests for manifest v1.5: facets present for TEI corpus, facets absent for folder corpus, backward compatibility (18 tests, all passing)

## Phase 4: Wizard TEI Steps (frontend)

- [x] 13. Enable XML Workflow option in CorpusWizard.vue Step 1: activate the existing disabled radio button, wire it to set workflow type
- [x] 14. Add wizard API endpoint for TEI schema discovery: `POST /api/corpus-wizard/tei/discover` accepts directory path, returns discovered elements with coverage
- [x] 15. Create TEI Schema Discovery wizard step: display discovered metadata elements with coverage percentages, user selects fields to extract
- [x] 16. Create Metadata Mapping wizard step: map discovered TEI fields to metadata roles (sender, recipient, date, place, keywords, abstract), pre-populate sensible defaults for common TEI patterns (combined with TEI Fields step)
- [x] 17. Create Chunking Strategy wizard step: radio selection of structural vs whole-document, preview panel showing example chunks with prepended metadata from sample files
- [x] 18. Create Filter Configuration wizard step: user selects which metadata fields become searchable facets, system suggests facet types (text, date_range, keyword) based on field content
- [x] 19. Wire TEI steps into wizard flow: conditional step rendering when XML workflow selected, update step labels and `canProceed` validation, pass TEI configuration to build endpoint

## Phase 5: Faceted Search UI (frontend)

- [x] 20. Create `FacetedSearch.vue` component: data-driven rendering from facet configuration, collapsible panel layout
- [x] 21. Implement text facet control: searchable dropdown with type-ahead, clear button, emits filter selection
- [x] 22. Implement date range facet control: from/to date inputs, validates ISO 8601, supports partial range (from-only or to-only)
- [x] 23. Implement keyword facet control: multi-select checkboxes or tag selector, emits selected keywords
- [x] 24. Integrate FacetedSearch.vue into chat interface: render when facets exist in config, position in dedicated UI area (not inline with query input), emit combined filter state
- [x] 25. Modify UserInput.vue: consume facet filter state, pass faceted filters to query API instead of simple filter_1/filter_2 when facets active
- [x] 26. Add API support for faceted filter parameters: extend `/api/ask/stream` to accept faceted filter object, pass through document_retrieval to retriever

## Phase 6: Retriever and Citation Updates (backend)

- [x] 27. Update retriever template: construct ChromaDB `where` clauses with `$and`, `$or`, `$gte`, `$lte` based on faceted filter parameters, fall back to simple equality for non-faceted corpora (added `_build_faceted_where_clause` static method)
- [x] 28. Update `base_retriever.py` `format_document_for_citation()`: include `tei_sender`, `tei_recipient`, `tei_date`, `tei_place` in citation output when present (added `tei` sub-object and top-level convenience fields)
- [x] 29. Update `/api/retriever/filters` endpoint: return facet configuration alongside existing filter capabilities (imports `get_facets`/`has_facets` from manifest_loader)
- [x] 30. Add integration tests for faceted retrieval: test date range queries, combined facets, backward compatibility with simple filters (29 tests, all passing)

## Phase 7: End-to-End Testing and Documentation

- [ ] 31. End-to-end test with Darwin corpus: build full 15,239-letter corpus via wizard TEI workflow, verify faceted search works, verify citations include TEI metadata
- [ ] 32. Update `docs/corpus_wizard.md`: document TEI-XML workflow steps, metadata mapping, chunking strategies
- [ ] 33. Update `docs/RAG_search.md`: document faceted search, advanced ChromaDB operators, metadata-enhanced retrieval
- [ ] 34. Update `docs/manifest.md`: document v1.5 schema with facets array
- [ ] 35. Update `docs/configuration.md`: document facet configuration in corpus_active.json

## Dependencies

- Phase 1 has no dependencies (pure backend, can start immediately)
- Phase 2 depends on Phase 1 (parser and chunker must exist)
- Phase 3 depends on Phase 2 (manifest needs build pipeline to populate facets)
- Phase 4 depends on Phase 2 (wizard steps call backend TEI endpoints)
- Phase 5 depends on Phase 3 (faceted search reads facet config from manifest)
- Phase 6 depends on Phases 3 and 5 (retriever needs facet parameters from frontend)
- Phase 7 depends on all prior phases
