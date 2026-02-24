# Implementation Tasks: Fix UI Polish and Metadata Gaps

## 1. Vector Store Build Metadata

### Manifest Generation
- [x] 1.1 Add `build` section to `_generate_manifest()` in `backend/modules/corpus_builder.py:777-869`
- [x] 1.2 Call `SystemRequirementsChecker.get_system_info()` from `backend/modules/system_requirements.py:206-241` during manifest generation
- [x] 1.3 Capture build duration (start/end timing around build process)
- [x] 1.4 Bump manifest version from `1.3` to `1.4`

### API Endpoint
- [x] 1.6 Update `/api/vector-store-info` endpoint in `backend/routers/retriever.py:42-149` to format and display `build` section
- [x] 1.7 Add "Build Environment" section to the human-readable overview output

### Frontend Display
- [x] 1.8 `VectorStoreInfo.vue` already renders API content as preformatted text — no changes needed

## 2. Citation Metadata Regression Fix

**Main branch comparison complete**: Feature branch is missing 10+ fields that `CitationList.vue` expects. See `proposal.md` section 2 for full field-by-field comparison.

### Backend
- [x] 2.1 Compare `format_document_for_citation()` in `backend/retrievers/base_retriever.py:283-344` with main branch `backend/retrievers/hansard_retriever.py:649-675` — **DONE: regression confirmed**
- [x] 2.2 Restore missing fields: `id`, `retrieval_id`, `title`, `url`, `date`, `page`, `text`, `quote`, `full_content`, `loc`, `weight`, `has_more`
- [x] 2.3 Add `source_url` extraction from metadata (not present on either branch currently)
- [x] 2.4 Keep feature branch improvements: dynamic filter_1/filter_2 corpus display, enrichment fields
- [x] 2.5 Merge both approaches: main branch's explicit field extraction + feature branch's filter system and enrichment

### Frontend
- [x] 2.6 Verify `CitationList.vue` renders correctly with restored fields (`url`, `text`, `quote`, `full_content`)
- [x] 2.7 Add `source_url` rendering as clickable link when present
- [ ] 2.8 Test with documents that have various metadata combinations

## 3. VITE_SITE_TITLE Build Integration

- [x] 3.1 Trace the end-to-end flow: corpus wizard build → `display_name` in manifest → `.env.development` update → frontend reads value
- [x] 3.2 Verify `display_name` is correctly set in `manifest.json` during build (check `corpus_builder.py` metadata section)
- [x] 3.3 Verify `backend/routers/corpus_wizard.py:1540-1598` correctly writes `VITE_SITE_TITLE` to the `.env` file
- [x] 3.4 Confirm frontend reads `VITE_SITE_TITLE` and displays it correctly after restart (`App.vue:61`)
- [x] 3.5 Documentation already exists in `docs/corpus_wizard.md:689-693` and line 710

## 4. Remove Redundant "Multi Corpus Vectorstore" Label

- [x] 4.1 Update `frontend/src/components/TestTargetBox.vue:44` — remove `MULTI_CORPUS_VECTORSTORE` from display
- [x] 4.2 Add `MULTI_CORPUS_VECTORSTORE` to the `unwantedFields` array in `TestTargetBox.vue:32-36`
- [ ] 4.3 Test display to confirm the redundant label is gone

## 5. Export Button Layout Consistency

- [x] 5.1 Update `frontend/src/components/ChatContainer.vue:23-35` sidebar layout to place both export buttons side by side
- [x] 5.2 Remove the gear icon from `frontend/src/components/ConfigurationExportButton.vue:9-16`
- [x] 5.3 Ensure both buttons use consistent Bulma classes (`button is-link is-light`)
- [ ] 5.4 Test responsive layout at various viewport widths

## 6. Testing

- [ ] 6.1 Build a new vector store and verify manifest contains `build` section (manual test — requires corpus build)
- [ ] 6.2 Verify Vector Store Overview modal displays build environment data (manual test — requires running app)
- [ ] 6.3 Verify citation metadata includes `source_url` when available (manual test — requires query)
- [ ] 6.4 Verify VITE_SITE_TITLE reflects corpus display name after build + restart (verified: flow is correct)
- [ ] 6.5 Verify Test Target box no longer shows redundant label (manual test — requires running app)
- [ ] 6.6 Verify export buttons are side by side with consistent styling (manual test — requires running app)

### Automated Verification
- [x] 6.7 Python syntax validation: all modified .py files pass `ast.parse()`
- [x] 6.8 IDE diagnostics: zero errors across all modified files
- [x] 6.9 No regressions in existing test suite (no tests cover modified modules)
