# Vector Store Creation

This guide covers how to create vector stores for ATLAS. The **corpus wizard** is the standard method; manual creation is available as an advanced alternative.

## Wizard Method (Recommended)

The corpus wizard provides a guided, end-to-end workflow for building vector stores:

1. Start the backend and frontend (`make b`, `make f`)
2. Open http://localhost:5173 and navigate to the Corpus Wizard
3. Select a source directory or GitHub repository
4. Configure filters, embedding model, and chunking parameters
5. Configure the LLM test target
6. Build the corpus (GPU-accelerated when available)
7. Enter Deploy Mode to activate

The wizard handles the entire pipeline: model preparation, fine-tuning, chunking, embedding, vector store creation, BM25 index generation, manifest writing, and retriever adapter generation. All artifacts are written to `backend/corpus/`.

See [Corpus Wizard Documentation](corpus_wizard.md) for full details.

## Pipeline Overview

Whether using the wizard or manual scripts, the vector store creation pipeline follows the same stages:

| Stage | Role |
|-------|------|
| **Model prep** | Downloads/creates a Sentence-Transformer wrapper, sets pooling mode |
| **Auto fine-tune** | Samples in-domain sentence pairs and runs contrastive fine-tuning |
| **Index build** | Splits source files into chunks, embeds with the fine-tuned model, stores in Chroma |
| **BM25 index** | Writes `bm25_corpus.jsonl` for hybrid (dense + BM25) search via RRF |
| **Manifest** | Writes `manifest.json` with schema version, stats, and metadata |
| **Retriever adapter** | Generates a Python adapter class extending `BaseRetriever` |

## Embedding Model

* **Backbone:** Any Hugging-Face BERT/DistilBERT checkpoint. The default is `Livingwithmachines/bert_1890_1900`.
* Fine-tuning happens automatically the first time you build a store; subsequent runs detect the fine-tuned model and skip the step.

### Pooling Strategy

| Value | Description | Vector size |
|-------|-------------|-------------|
| `mean` (default) | Average of token vectors (robust recall) | 768 |
| `cls` | Only the `[CLS]` token (sometimes sharper) | 768 |
| `mean+max` | Concatenate mean & max (context + keyword) | 1,536 |

Pooling is configured during the wizard build step or via the `POOLING` setting in manual scripts.

## Vector Store (Chroma)

### Schema (metadata per chunk)

| Field | Example | Purpose |
|-------|---------|---------|
| `id` | `"k15_openai40:1901_nz:42"` | Unique chunk ID |
| `text` | chunk contents | Retrieval payload |
| `date` | `"Thursday, 11th July, 1901"` | Filtering / display |
| `url` | source URL | Citations |
| `page` | `"302"` | Citation context |
| `loc` | `{"lines":{"from":2701,"to":4000}}` | Snippet position |
| `corpus` | `"us_case_law"` | Enables corpus filtering |

Chroma persists to `backend/corpus/chroma_db/` (wizard) or the directory set by the build script (manual).

## Hybrid Search (Dense + BM25)

Store creation writes both a vector database (Chroma) and a BM25-aligned corpus file (`bm25_corpus.jsonl`). Each JSONL record contains `id`, `text`, and `metadata`. The `id` matches the vector-store chunk id to enable fusion and citation.

At query time, if the BM25 corpus file is available and `rank_bm25` is installed, the retriever performs hybrid fusion (dense + BM25 via RRF). Otherwise it falls back to dense-only.

See [RAG Search Documentation](RAG_search.md) for RRF details and configuration.

## Build Artifacts

### Wizard Output (`backend/corpus/`)

| File | Purpose |
|------|---------|
| `manifest.json` | Corpus metadata, stats, schema (v1.4) |
| `corpus_active.json` | Runtime configuration for the backend |
| `corpus_config.yaml` | Build configuration (reproducibility) |
| `chroma_db/` | ChromaDB vector store |
| `bm25_corpus.jsonl` | BM25 lexical index |
| `{name}_adapter.py` | Retriever adapter extending `BaseRetriever` |

### Manual Output (`create/output/`)

Manual scripts write to `create/output/`. After a successful build, artifacts must be copied into place:

```bash
cp -r create/output/chroma_db backend/corpus/chroma_db
cp create/output/manifest.json backend/corpus/manifest.json
cp create/output/bm25_corpus.jsonl backend/corpus/bm25_corpus.jsonl
```

## Advanced: Manual Vector Store Creation

For scripted builds or custom pipelines, use the scripts in the `create/` directory:

```bash
make vs      # Build vector store (auto-detects GPU)
make r       # Generate retriever adapter
```

Both targets will:
- Ensure the Python virtual environment is set up and dependencies are installed
- Use the unified `pyproject.toml` for consistency
- Output results to `create/output/`

### Custom Corpora

You can add new corpora by copying and adapting the template scripts in `create/`. The process is corpus-agnostic: provide your source documents, configure the embedding model and chunking parameters, and run the build.

### Retriever

```python
vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=HuggingFaceEmbeddings(model_name=str(local_model_path)),
    persist_directory=CHROMA_PERSIST_DIRECTORY
)

docs = vector_store.similarity_search(
    query,
    k=15,
    filter={"corpus": "us_case_law"}   # optional
)
```

Hybrid mode (dense + BM25) is recommended for production and is supported at runtime via Reciprocal Rank Fusion (RRF).

---

Key takeaway: Use the wizard for standard corpus builds. Manual creation is available for advanced users or automated pipelines, but requires manual artifact placement and configuration.
