# Vector Store Manifest

This document describes the single-source `manifest.json` used by ATLAS to capture metadata and statistics about any vector store, how it’s used across the system, and how to regenerate it. While examples reference “Hansard,” the format is corpus-agnostic and applies to any text collection you index.

## What is the manifest?

The manifest is a JSON file located at:

- Build output: `create/output/manifest.json`
- Runtime copy: `backend/targets/manifest.json`

It captures key information about the vector store and its corpora so the backend and UI can auto-configure and display concise stats, and the LLM can answer meta questions with ground-truth numbers.

## Schema (v1.1)

Top-level fields:

- `schema_version`: Manifest schema version (e.g., `"1.1"`).
- `index_name`: Name of the vector DB collection (e.g., a Chroma collection).
- `embedding_model`: Local path or model ID used for embeddings.
- `created`: ISO timestamp when the store was built (UTC).
- `chunk_size`, `chunk_overlap`: Chunking parameters used.
- `fields`: Inferred metadata schema map. Each field has a `type` (enum, year, date, string). If `enum`, a `values` array is provided. This is generic and driven by your parsers’ output metadata.
- `stats`: Aggregated statistics (standardized, corpus‑agnostic):
  - `total_files`, `total_chunks`, `db_size_mb`
  - `corpora`: Map per corpus id (e.g., `collection_a`, `collection_b`) to:
    - `files`, `chunks`, `chars`, `words`

Notes:
- The standardized set avoids corpus‑specific counters (e.g., speeches, sessions, debates, speakers, date ranges) to keep numbers consistent across heterogeneous sources.
- Builders may compute corpus‑specific analytics separately, but these should live under a corpus‑specific or experimental key that the default UI/LLM do not consume.

Notes:
- Names like “speeches,” “sessions,” and “debates” are domain examples (Hansard). For a different corpus, these may be absent or replaced by analogous domain terms (e.g., “articles,” “issues,” “sections”).
- Optional counters appear only when your parser emits the required metadata; consumers should tolerate their absence.

## How is it generated?

The manifest is written by your corpus builder script (for Hansard, `create/xml/create_hansard_xml_store.py`). In general, a builder will:

1. Parse input documents using a parser registry for each corpus.
2. Chunk content and write to the vector DB (e.g., Chroma) and a lexical index source (e.g., a BM25‑aligned `bm25_corpus.jsonl`).
3. Track stats incrementally and infer a metadata schema from emitted fields.
4. Write `create/output/manifest.json` with the schema and stats.

After a successful build, copy the artifacts into the runtime target directory:

- `cp -r create/output/chroma_db backend/targets/chroma_db`
- `cp create/output/manifest.json backend/targets/manifest.json`
- `cp create/output/bm25_corpus.jsonl backend/targets/bm25_corpus.jsonl`

## How is it used?

- Backend API: `/api/vector-store-info` reads `backend/targets/manifest.json` and returns a concise text summary for the UI (or pretty JSON with `?raw=true`).
- Targets/config: `backend/targets/base_target.py` loads chunking/model/index info from the manifest.
- LLM context: For meta/store‑stats questions (files, chunks, model, DB size, chunking), the server injects a one‑page summary so the model answers with exact manifest numbers. The LLM must only cite stats present in the manifest; it does not derive or infer counts (like speeches/sessions/debates/speakers/date ranges). For content questions, the model relies on retrieved documents, not the manifest.

### Source URLs and citation metadata

- Canonical URLs should be HTTP(S) links to the public page for the source document. Do not synthesize `file://` links in metadata for citations.
- Parsers/builders may include `source_relpath` (relative to their local base directory) for debugging and offline traceability, but UI citations should rely on the canonical HTTP(S) `url` when available.
- Frontend citations expect metadata fields: `id`, `url`, `date` (optional), `page` (optional), `corpus`, and `loc` (a small JSON string like `{ "chunk": 3 }`).
- If a corpus can deterministically map `source_relpath` to an HTTP(S) permalink (e.g., via a known domain + path pattern), the builder should set `metadata.url` accordingly during build. Otherwise, leave `url` empty.

### Using the manifest with different corpora

- Keep the standardized fields stable so the backend/UI/LLM behave consistently regardless of source.
- If a corpus can authoritatively provide extra analytics, add them under a corpus‑specific section (e.g., `corpus_extras` or namespaced keys). Avoid changing the standardized fields.
- Downstream consumers should ignore unknown keys. Future versions may include opt‑in sections for richer analytics when all corpora can support them symmetrically.

## Regenerating and validating

- Build (CPU or GPU): see `utils/scripts/create_store_cpu.sh` or `utils/scripts/create_store_gpu.sh`.
- Always copy the three outputs into `backend/targets/` after the build.
- In the UI, open the Config/Test Target and click "Vector Store Overview" to confirm the summary renders.

## Backward/forward compatibility

- Consumers should ignore unknown fields.
- New stats may appear in future versions; `schema_version` will be bumped accordingly.

## Troubleshooting

- If the UI shows raw JSON or errors, verify `backend/targets/manifest.json` exists and is valid JSON.
- Domain‑specific optional stats (e.g., sessions/debates/speakers) may be absent when parsers don’t emit those fields; this is expected.
