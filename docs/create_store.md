# Building a Chroma Vector Store (Create-Store Workflow)

This guide walks through the end-to-end pipeline that converts a folder of plain-text documents into a Chroma/HNSW vector store usable by ATLAS.  The process is corpus-agnostic—the same steps work whether you have three Hansard corpora or a single collection of legal opinions.

> **Terminology**  
> *Corpus* = a logical source (e.g. `us_case_law`, `uk_hansard`). Each chunk is tagged with its corpus so we can filter at query time.

## 1. Pipeline at a Glance

| Stage | Script / Class | Role |
|-------|----------------|------|
| 1️⃣ **Model prep** | `create/prepare_embedding_model.py` (`ensure_st_model`) | Downloads/creates a *Sentence-Transformer* wrapper around 19-century BERT, sets pooling mode, and saves to `models/…` |
| 2️⃣ **Auto fine-tune** | integrated in `create_hansard_store.py` | Samples ≈ 20 k in-domain sentence pairs and runs a 2-epoch contrastive fine-tune, saved to `models/<base>_st_ft` |
| 3️⃣ **Index build** | `create/txt/create_hansard_store.py` (or an equivalent script under `create/<type>/`) | • Splits source files into 1 000-character chunks<br>• Embeds with **the fine-tuned model**<br>• Stores chunks + metadata in **Chroma** |
| 4️⃣ **Retrieval** | LangChain `Chroma` retriever | Given a user query, embeds it with *the same* model, then runs similarity search (`k` nearest) with an optional metadata filter (`filter={"corpus": …}`) |
| 5️⃣ **RAG** | LLM orchestrator (e.g. QA chain) | Feeds retrieved chunks to the LLM for answer synthesis |

---

## 2. Embedding model

* **Backbone:** Any Hugging-Face BERT/DistilBERT/… checkpoint.  The default shipped with the project is `Livingwithmachines/bert_1890_1900`.

The fine-tune now happens automatically the first time you build the
store; subsequent runs detect `models/<base>_st_ft` and skip the step.

### Pooling strategy (`POOLING`)

```ini
# .env.*
POOLING=mean        # mean | cls | mean+max
```

| Value | Description | Vector size |
|-------|-------------|-------------|
| `mean` (default) | Average of token vectors (robust recall) | 768 |
| `cls`            | Only the `[CLS]` token (sometimes sharper) | 768 |
| `mean+max`       | Concatenate mean & max (context + keyword) | 1 536 |

The env-var is **read twice**:

1. In *model prep* – so the saved Sentence-Transformer has the
   corresponding pooling head;
2. In *index build* – so per-chunk embeddings match the head.

---

## 3. Vector-store (Chroma)

* **Collection:** `CHROMA_COLLECTION_NAME` *(default `blert_1000`)*  
* **Schema (metadata):**

| Field | Example | Purpose |
|-------|---------|---------|
| `id`    | `"k15_openai40:1901_nz:42"` | unique chunk ID |
| `text`  | chunk contents | retrieval payload |
| `date`  | `"Thursday, 11th July, 1901"` | filtering / display |
| `url`   | source URL | citations |
| `page`  | `"302"` | citation context |
| `loc`   | `{"lines":{"from":2701,"to":4000}}` | snippet position |
| `corpus`| `"us_case_law"` | enables `filter={"corpus": "us_case_law"}` |

*Chroma* persists automatically to the directory set in
`CHROMA_PERSIST_DIRECTORY`.

---

## 4. Retriever

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

Hybrid mode (dense + BM25) is recommended for production; blend scores
with a simple linear mix or re-ranker.

> **Note on BM25 / hybrid search**  
> ATLAS currently ships only the dense-vector search described above **plus** its own lexical reranker (`document_reranking.py`).  A true Okapi-BM25 index is _not_ built at store-creation time.  If you need a classic term-frequency scorer you can integrate `langchain.retrievers.BM25Retriever`, then blend its scores with the dense results (see `docs/RAG_search.md` for a sketch).

---

## 5. Workflow summary

```