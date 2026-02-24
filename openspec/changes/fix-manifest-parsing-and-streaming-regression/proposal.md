# Fix Manifest Parsing and Streaming Regression

## Summary

Fix three regressions introduced on the `feature/add-corpus-wizard` branch: (1) the Vector Store Overview displays `(unknown)` and raw dict objects because the API endpoint parses flat manifest keys that don't exist in the wizard-built v1.3/v1.4 manifest structure, (2) user queries fail with `streaming_error` during response generation, and (3) citation metadata changes from `fix-ui-polish-and-metadata-gaps` are not reaching the frontend.

## Motivation

These are blocking regressions that break core functionality:

- **Vector Store Overview is unreadable** — shows `Vector Store: (unknown)` and dumps the `embedding_model` dict as a string instead of extracting the model ID. The API endpoint at `backend/routers/retriever.py:75-85` was written for a legacy flat manifest format. The corpus wizard generates a nested manifest (v1.3/v1.4) with `corpus_name` instead of `index_name`, `embedding_model` as a nested object, and `chunk_size`/`chunk_overlap` inside the `embeddings` object.

- **Streaming error on query** — the exact error message `"An error occurred during response generation"` originates from `backend/modules/response.py:140`, indicating the LLM streaming pipeline fails during chunk generation. This needs diagnosis — possible causes include import changes (`streaming.py` now imports `format_document_for_citation` from `base_retriever` instead of `hansard_retriever`), retriever configuration issues, or telemetry span errors.

- **Citation metadata not updated** — the `format_document_for_citation()` fix in `base_retriever.py` restores missing fields but there is also a null-safety bug at `backend/modules/streaming.py:306` where `citation["idx"] = idx` is called without checking if `format_document_for_citation()` returned `None`. Additionally, the streaming error may prevent citations from ever being sent to the frontend.

## Detailed Design

### 1. Fix Vector Store Info API Manifest Parsing

Update `backend/routers/retriever.py:75-85` to read the correct nested paths from the v1.3/v1.4 manifest:

| Field | Current (broken) | Correct path |
|-------|------------------|--------------|
| `index_name` | `data.get("index_name")` | `data.get("corpus_name")` or `data.get("vector_store", {}).get("collection_name")` |
| `embedding_model` | `data.get("embedding_model")` (gets dict) | `data.get("embedding_model", {}).get("id")` |
| `chunk_size` | `data.get("chunk_size")` | `data.get("embeddings", {}).get("chunk_size")` |
| `chunk_overlap` | `data.get("chunk_overlap")` | `data.get("embeddings", {}).get("chunk_overlap")` |
| `stats` | `data.get("stats")` | `data.get("statistics")` |
| `total_chunks` | `stats.get("total_chunks")` | `statistics.get("total_chunks")` |
| `total_files` | `stats.get("total_files")` | Not in v1.4 — derive from `statistics.filters` if available |
| `db_size_mb` | `stats.get("db_size_mb")` | Not in v1.4 — calculate from chroma_db directory size or omit |
| `corpora` | `stats.get("corpora")` | Derive from `filters` object in manifest |

Also check `backend/routers/corpus_wizard.py:1318-1323` which reads `collection_name`, `embedding_model`, `chunk_size`, `chunk_overlap` from the manifest with the same broken flat-key assumptions.

### 2. Diagnose and Fix Streaming Error

The error `"An error occurred during response generation"` at `response.py:140` fires when the LLM chunk generator raises an exception. Investigation steps:

- Check if the `base_retriever` import in `streaming.py` causes an import-time error or circular dependency
- Check if the retriever is correctly configured for the wizard-built corpus (collection name, embedding model path)
- Check logs for the actual exception behind the `streaming_error` — the `logger.error(f"Error during streaming: {e}")` at `response.py:138` will contain the root cause
- Test with the backend running and examine the full traceback

This may be caused by the retriever not finding the correct ChromaDB collection, or an embedding model mismatch between what's configured and what's available.

### 3. Fix Citation Null Safety

At `backend/modules/streaming.py:305-307`:
```python
citation = format_document_for_citation(doc, idx)
citation["idx"] = idx  # TypeError if citation is None
citations.append(citation)
```

Add a null check: skip the document if `format_document_for_citation()` returns `None`.

### 4. Verify Citation Pipeline End-to-End

After fixing the streaming error, verify:
- `format_document_for_citation()` returns the full field set (`text`, `quote`, `url`, `retrieval_id`, `full_content`, `source_url`, etc.)
- `stream_documents_as_references()` sends properly structured citations to the frontend
- `CitationList.vue` renders the citations correctly

## Known Issues (discovered during testing, require separate proposals)

### A. VITE_SITE_TITLE persists after `make reset`

`make reset` (`deploy/dev/scripts/reset_dev.sh`) removes corpus data, configs, and targets but does NOT reset `config/.env.development`. The VITE_SITE_TITLE value written by a previous corpus wizard build persists. The reset script should either restore `.env.development` from `.env.template` or at minimum reset the `VITE_SITE_TITLE` line to the template default (`"ATLAS Hansard"`).

### B. Stale manifest in `backend/targets/` after reset + rebuild

The Vector Store Overview reads from `backend/targets/manifest.json`, but this file may be stale (from a previous build). Two issues:
1. After `make reset`, the old `backend/targets/manifest.json` may not be cleaned (depends on reset script)
2. After a new build, `backend/modules/manifest_loader.py` caches the manifest in memory and the `invalidate_cache()` function at line 118 is **never called** anywhere in the codebase. The corpus wizard copies the manifest to targets (`corpus_wizard.py:1487-1492`) but doesn't invalidate the cache, so the old cached data is served until the server restarts.

### C. Streaming error persists — LLM provider failure (not a code bug)

The streaming error at `response.py:140` fires on the `create_llm_span=False` path (called by `generate_response_with_telemetry` at line 498). The fix applied at line 318 was on the `create_llm_span=True` path — a different code branch. The error at line 140 is triggered when `llm.stream(final_prompt)` at line 103 raises an exception, which indicates an LLM provider/configuration failure (API key, model availability, or test target misconfiguration after reset). The actual exception is logged at `response.py:138` but only as a one-line message with no traceback — better error logging would help diagnose this.

### D. Error logging gap in response.py

At `response.py:138`, the error is logged as `logger.error(f"Error during streaming: {e}")` without `exc_info=True`, so no traceback is captured. The telemetry-enabled path at line 335 does include `exc_info=True`. Both paths should log full tracebacks for debugging.

## Scope

Bug fixes only — no new features. All changes restore intended behaviour that existed on the main branch or was planned in `fix-ui-polish-and-metadata-gaps`.

## Risks

- The streaming error root cause at response.py:140 is an LLM provider failure, not a code bug — requires server log investigation
- Manifest field mapping needs to support both the legacy flat format (if any old manifests exist) and the v1.3/v1.4 nested format
