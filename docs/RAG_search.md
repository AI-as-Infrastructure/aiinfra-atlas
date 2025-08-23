# Retrieval-Augmented Generation (RAG) – Search Pipeline

This document explains, in reader-friendly terms, how ATLAS performs Retrieval-Augmented Generation (RAG) using a Hybrid (Dense + BM25) search approach fused by Reciprocal Rank Fusion (RRF). Developer-level details are provided in call‑outs.

## 1	Pipeline Overview

```text
┌─ User query ─┐
│              ▼
│  1. Hybrid search: Dense vectors (HNSW) + BM25 lexical
│              ▼
│  2. Reciprocal Rank Fusion (RRF)  →  Top‑K passages
│              ▼
└► 3. LLM context builder (chat memory + citations) ─► Answer
```

1. Hybrid search combines dense vector search (HNSW) with sparse BM25 lexical search to capture both semantic similarity and exact term matches.
2. RRF fusion merges and re‑ranks results from both methods for a balanced final list.
3. The LLM receives the fused top‑K passages plus running chat memory to generate the answer.

---

## 2	Hybrid Search Architecture

Dense vector and sparse lexical components work together, enriched by robust metadata.

• Dense vectors (Chroma + HNSW)
  - Backend: `langchain_community.vectorstores.Chroma` with HNSW indexing
  - Typical chunking: ~1 000 chars with overlap (configurable)
  - Metadata per chunk: `id`, `corpus`, `date`, `url`, `page`, `loc`, etc.

• Sparse BM25 (lexical)
  - Algorithm: BM25 for exact term matching
  - Storage: precomputed `bm25_corpus.jsonl` with the same deterministic `id` values as the vector store
  - Loaded at runtime if present; otherwise the system runs dense‑only

• Metadata & URLs
  - Canonical HTTP(S) URLs only (no file://)
  - Deterministic IDs support alignment between dense and lexical search and power clear citations in the UI

Vector‑store creation is handled by scripts under `create/`. Each run emits a minimal manifest with stats and configuration.

---

## 3	Reciprocal Rank Fusion (RRF)

Hybrid search merges ranked results from dense and BM25 lists using Reciprocal Rank Fusion. Each list contributes by position (lower rank = better), and the scores are summed:

• RRF scoring: `score = 1 / (rank + k)`, commonly `k = 60`
• Fusion is rank‑based (robust to raw score scales), duplicates accumulate score
• Final top‑K is selected after fusion

Candidate sizing and controls (defaults in this repo):

| Variable | Purpose | Default |
|----------|---------|---------|
| `LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS` | Per‑side candidate count when a specific corpus is selected | 120 |
| `LARGE_RETRIEVAL_SIZE_ALL_CORPUS`    | Per‑side candidate count when no corpus filter is applied   | 80  |
| `SEARCH_K`                           | Final top‑K (target config)                                 | from `backend/targets/*.txt` |
| `HANSARD_SEARCH_TYPE`                | `hybrid` or `similarity` (dense‑only)                       | `hybrid` |
| `HANSARD_BM25_CORPUS` / `BM25_CORPUS`| Path to `bm25_corpus.jsonl`                                 | `backend/targets/bm25_corpus.jsonl` |

If the BM25 corpus file isn’t found or `rank_bm25` isn’t installed, retrieval falls back to dense‑only automatically.

---

## 4	Corpus Filtering (UI & API)

• Frontend: Dropdown labelled Collection inside Test Target.  
• API: Value sent as `corpus_filter` in `/api/ask` & `/api/ask/stream` requests.  
• Backend: Applied as `filter={"corpus": corpus_id}` to vector search and to BM25 materialization.

---

## 5	Chat Memory & Stateless Retrieval

During a multi‑turn conversation the frontend sends the running `chat_history` array. The backend:

1. Serialises that history into the system prompt (last ~3 000 tokens; configurable).  
2. Does not change retrieval parameters—the same hybrid retrieval is executed every turn.  
3. May provide message‑level memory to the LLM (provider‑specific).

Because search is stateless, earlier turns do not bias result selection; only the current user question determines retrieval.

---

## 6	Document Reranking (Why the second pass?)

Once the fused candidate set is collected the reranker scores each document more precisely using plain‑text signals that embeddings miss:

| Signal | Weight (default) | Note |
|--------|------------------|------|
| Exact phrase match | 0.5 | Highest boost when the query appears verbatim |
| Keyword frequency | 0.3 | More hits → higher score |
| Keyword proximity | 0.2 | Closer terms signal topical tightness |
| Metadata match bonus | 0.5 each | e.g. date, speaker, or custom tags |

Weights live in `backend/modules/document_reranking.py` and can be tuned at runtime via `configure_reranker()`. This reranker is complementary to hybrid fusion and refines the final context passed to the LLM.

---

## 7	Telemetry & Diagnostics

All retrieval spans emit OpenTelemetry attributes:

• Attributes include `search_type`, `search_k`, `pooling`, `corpus_filter`, etc.  
• When hybrid is enabled, the retriever records whether BM25 was available; downstream spans can include counts per stage.

Use Phoenix to validate retrieval health and ensure configuration matches expectations.

---

## 8	Configuration Cheatsheet

| Setting | Location | Example |
|---------|----------|---------|
| Vector store path | `.env` → `CHROMA_PERSIST_DIRECTORY` | `backend/targets/chroma_db` |
| Collection name | `.env` → `CHROMA_COLLECTION_NAME` | `blert_1000` |
| Embedding model | `.env` → `EMBEDDING_MODEL` | `Livingwithmachines/bert_1890_1900` |
| Pooling strategy | `.env` → `POOLING` | `mean` |
| Search type | `.env` → `HANSARD_SEARCH_TYPE` | `hybrid` |
| BM25 corpus path | `.env` → `HANSARD_BM25_CORPUS` or `BM25_CORPUS` | `backend/targets/bm25_corpus.jsonl` |
| Single‑corpus candidates | `.env` → `LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS` | `120` |
| All‑corpus candidates | `.env` → `LARGE_RETRIEVAL_SIZE_ALL_CORPUS` | `80` |
| Final top‑K | `backend/targets/<target>.txt` → `SEARCH_K` | `15` |

---

Key takeaway: Hybrid search balances semantic understanding with lexical precision. RRF prevents either method from dominating, and deterministic IDs plus canonical URLs ensure clear, auditable citations.