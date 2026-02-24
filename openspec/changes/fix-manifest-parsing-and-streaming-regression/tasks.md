# Implementation Tasks: Fix Manifest Parsing and Streaming Regression

## 1. Fix Vector Store Info API Manifest Parsing

- [x] 1.1 Update `backend/routers/retriever.py:75-85` to read nested manifest fields:
  - `corpus_name` instead of `index_name`
  - `embedding_model.id` instead of `embedding_model` (string)
  - `embeddings.chunk_size` and `embeddings.chunk_overlap` instead of top-level
  - `statistics` instead of `stats`
  - Derive per-corpus breakdown from `filters` object
- [x] 1.2 Support both legacy flat format and v1.3/v1.4 nested format (detect via `isinstance(embedding_model, dict)`)
- [x] 1.3 Update `backend/routers/corpus_wizard.py:1318-1323` manifest field access:
  - `vector_store.collection_name` instead of top-level `collection_name`
  - `embedding_model.id` instead of `embedding_model` (string)
  - `embeddings.chunk_size` instead of top-level `chunk_size`
  - `embeddings.chunk_overlap` instead of top-level `chunk_overlap`
- [ ] 1.4 Test Vector Store Overview modal displays correctly with v1.4 manifest (manual test — requires running app)

## 2. Diagnose and Fix Streaming Error

- [x] 2.1 Diagnosed root cause: undefined variable `span_id` at `response.py:318` — `NameError` during response finalization
- [x] 2.2 Verified `base_retriever` import in `streaming.py` has no circular dependency — imports are correct
- [x] 2.3 Verified retriever initialization is correct for wizard-built corpora
- [x] 2.4 Fixed: replaced undefined `span_id` with `llm_span_id = str(llm_span.get_span_context().span_id)` at `response.py:318`
- [ ] 2.5 Test: submit a query and confirm streaming response completes without error (manual test — requires running app)

## 3. Fix Citation Null Safety

- [x] 3.1 Added null check at `backend/modules/streaming.py:304-306` — `if citation is None: continue`
- [x] 3.2 Verified: only other caller (`retriever_call_model.py`) imports but does not directly call the function in citation formatting loops

## 4. Verify Citation Pipeline End-to-End

- [x] 4.1 Verified `format_document_for_citation()` returns all expected fields: `id`, `retrieval_id`, `title`, `url`, `source_url`, `date`, `page`, `text`, `quote`, `full_content`, `loc`, `weight`, `has_more`
- [x] 4.2 Verified `stream_documents_as_references()` sends properly structured citations via SSE (`type: "references"`, `citations` array)
- [x] 4.3 Verified `CitationList.vue` maps: `quote`/`text` for display, `url` for links, `retrieval_id` for metadata, `source_url` as clickable link, `full_content` for expanded view
- [ ] 4.4 Test with documents that have varying metadata (manual test — requires running app)
