# Retrieval-Augmented Generation (RAG) – Search Pipeline

This document explains, in reader-friendly terms, how ATLAS performs **Retrieval-Augmented Generation (RAG)** search across _any_ collection of corpora stored in a Chroma/HNSW vector database.  Developer-level details are provided in call-outs.

## 1 Pipeline Overview

```text
┌─ User query ─┐
│              ▼
│  1. Balanced multi-corpus vector search (Chroma + HNSW)
│              ▼
│  2. Document reranker  →  Top-K passages
│              ▼
└► 3. LLM context builder (chat memory + citations) ─► Answer
```

1. **Vector search** uses the HNSW index inside Chroma to pull a large pool of candidate chunks.  When more than one corpus is available the retriever balances the sample so that no single corpus dominates.
2. **Reranking** re-orders those candidates with lexical heuristics (exact match, keyword frequency, proximity, metadata boosts – see §6).
3. The **LLM** receives the top-K passages plus the running chat-memory to generate an answer.

---

## 2 Chroma + HNSW Vector Store

* **Backend:** [`langchain_community.vectorstores.Chroma`].
* **Index:** HNSW (`algorithm = "hnsw"`).  Provides sub-millisecond approximate nearest-neighbour search.
* **Chunks:** 1 000-character sliding window (`chunk_size = 1000`, `chunk_overlap = 100`).
* **Metadata:** Each chunk carries a `corpus` field (e.g. `legal_us`, `legal_uk`, `legislation_nz`).  The value is free-form – any label that helps you filter at query time.

Vector-store creation is handled by the family of `create/.../create_*_store.py` scripts.  Each run emits a **manifest** (stats & config) under `create/<type>/output/<COLLECTION_NAME>.txt` – this allows the retriever generator to stay in sync with the store.

---

## 3 Balanced Multi-Corpus Retrieval

When the UI corpus selector is **"All"** the retriever pulls a *fixed* number of vectors from **each** corpus to avoid size bias:

```python
for corpus in os.getenv("MULTI_CORPUS_METADATA", "legal_us,legal_uk,legislation_nz").split(','):
    docs = vector_store.similarity_search(
        query,
        k=int(os.getenv('LARGE_RETRIEVAL_SIZE_ALL_CORPUS', 200)),
        filter={"corpus": corpus}
    )
    pool.extend(docs)
```

Environment variables:

| Variable | Purpose | Default |
|----------|---------|--------|
| `LARGE_RETRIEVAL_SIZE_ALL_CORPUS` | Candidates fetched *per corpus* when corpus = `all` | **200** |
| `LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS` | Candidates fetched when a specific corpus is selected | **500** |
| `SEARCH_K` | Final top-K after reranking | **10** (via `.txt` target config) |

Change these in `.env.*` or the target config to trade recall vs. speed.

---

## 4 Corpus Filtering (UI & API)

• **Frontend:** Dropdown labelled *Collection* inside *Test Target* box.  
• **API:** Value sent as `corpus_filter` in `/api/ask` & `/api/ask/stream` requests.  
• **Backend:** Passed straight into `HansardRetriever.retrieve(query, corpus_filter=…)` which adds `filter={"corpus": corpus_id}` to the Chroma call.

---

## 5 Chat Memory & Stateless Retrieval

During a multi-turn conversation the frontend sends the running `chat_history` array.  The backend:

1. Serialises that history into the system prompt (last ~3 000 tokens; configurable).  
2. Does **not** change the vector search parameters—the same balanced retrieval is executed every turn.  
3. May provide message-level memory to the LLM (provider-specific).

Because search is stateless, earlier turns do not bias corpus selection; only the **current** user question determines retrieval.

---

## 6 Document Reranking (Why the second pass?)

Once the balanced candidate set is collected the **reranker** scores each document more precisely using plain-text signals that embeddings miss:

| Signal | Weight (default) | Note |
|--------|-----------------|------|
| Exact phrase match | **0.5** | Highest boost when the query appears verbatim. |
| Keyword frequency | 0.3 | More hits → higher score. |
| Keyword proximity | 0.2 | Closer terms signal topical tightness. |
| Metadata match bonus | 0.5 each | e.g. date, speaker, or custom tags.

Weights live in `backend/modules/document_reranking.py` and can be tuned at runtime via `configure_reranker()`.

> **Why bother?** Approximate-nearest-neighbour search is great for recall but its ranking is wholly vector-based.  A lexical reranker restores precision, ensuring the final **K** passages handed to the LLM truly answer the user's question.

The reranker also trims the candidate list down to `SEARCH_K` (default 10), improving LLM context efficiency.

---

## 7 Telemetry & Diagnostics

All retrieval spans emit OpenTelemetry attributes:

* `search_type`, `search_k`, `large_retrieval_size`, `pooling`, `corpus_filter`, etc.  
* Per-corpus document counts (after reranking) are logged for imbalance monitoring.

Use **Phoenix** to confirm that AU/NZ get equal candidate counts when no filter is applied.

---

## 8 Configuration Cheatsheet

| Setting | Location | Example |
|---------|----------|---------|
| Vector store path | `.env` → `CHROMA_PERSIST_DIRECTORY` | `/data/chroma_db` |
| Collection name | `.env` → `CHROMA_COLLECTION_NAME` | `blert_1000` |
| Embedding model | `.env` → `EMBEDDING_MODEL` | `models/bert_1890_1900_st_ft` |
| Pooling strategy | `.env` → `POOLING` | `mean+max` |
| Per-corpus fetch-K | `.env` → `LARGE_RETRIEVAL_SIZE_ALL_CORPUS` | `300` |
| Single-corpus fetch-K | `.env` → `LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS` | `600` |
| Final top-K | `backend/targets/<target>.txt` → `SEARCH_K` | `15` |

---

**Key takeaway:** Size imbalances between corpora do not skew answers: the retriever draws an equal-sized candidate set from each corpus, then a lexical reranker and the LLM decide which passages matter most. 