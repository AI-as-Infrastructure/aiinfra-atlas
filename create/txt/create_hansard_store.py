#!/usr/bin/env python3

# hansard_blert_chroma_store.py
# Creates a Chroma vector store with corpus as a metadata field for filtering.

# Ensure project root on path *before* any local package imports
import sys, os
from pathlib import Path
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Standard libs
import re, torch, json, nltk, time, subprocess, numpy as np, shutil
import platform
import psutil
import traceback
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel, AutoConfig
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
from create.prepare_embedding_model import ensure_st_model
from chromadb import PersistentClient
from chromadb.config import Settings

# Fine-tuning utilities
from sentence_transformers import SentenceTransformer, losses, InputExample
from torch.utils.data import DataLoader

# -------------------------------------------------------------
# Load environment variables (development, staging, production)
# -------------------------------------------------------------

repo_root = Path(__file__).resolve().parents[2]  # project root
env_candidates = [
    repo_root / "config" / ".env.development",
    repo_root / "config" / ".env.staging",
    repo_root / "config" / ".env.production",
]

for _env in env_candidates:
    if _env.exists():
        print(f"Loading environment variables from: {_env}")
        load_dotenv(dotenv_path=_env, override=False)
        break
else:
    print("[WARN] No .env.* file found under config/. Proceeding with current environment.")

# Download NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    print(f"Warning: NLTK download failed: {e}")

# =====================
# Data source locations
# =====================
#
# Set the base directory where your Hansard sources live. You can:
# - export HANSARD_SOURCES_ROOT=/abs/path
# - or set VECTOR_SOURCES_BASE=/abs/path
# - or edit DEFAULT_VECTOR_SOURCES_BASE below
#
# Prefer the in-repo TXT snapshot if available
DEFAULT_VECTOR_SOURCES_BASE = str((Path(__file__).resolve().parents[2] / "hansard_sources_FULL_TXT").resolve())
VECTOR_SOURCES_BASE = os.environ.get("HANSARD_SOURCES_ROOT", os.environ.get("VECTOR_SOURCES_BASE", DEFAULT_VECTOR_SOURCES_BASE))
print(f"[vs] Vector sources base: {VECTOR_SOURCES_BASE}")

"""
Corpus discovery
----------------
We prefer the external hansard_sources_FULL_TXT layout, but users may have
nested directories where AU/NZ/UK appear deeper in the tree. To keep this
robust and corpus-agnostic, we:
  1) Try the simple AU/NZ/UK directories directly under the base.
  2) If missing, auto-discover any directories named AU/NZ/UK anywhere under
      the base and map them to 1901_au/1901_nz/1901_uk respectively.
  3) If nothing matches but *.txt files exist, index the entire base as a
      single corpus (1901_all).
"""
USE_HANSARD_SOURCES_FULL_LAYOUT = True

# Helper to resolve relative paths based on this script's directory
def resolve_path(path_str: str) -> str:
    """Resolve a path string relative to this script, unless it's absolute."""
    p = Path(path_str)
    if p.is_absolute():
        return str(p)
    script_dir = Path(__file__).resolve().parent
    return str((script_dir / path_str).resolve())

def _discover_corpora(base: str) -> Dict[str, str]:
    base_path = Path(base)
    region_map = {"au": "1901_au", "nz": "1901_nz", "uk": "1901_uk"}
    discovered: Dict[str, str] = {}

    # Step 1: look for AU/NZ/UK directly under base
    for region, cid in region_map.items():
        p = base_path / region.upper()
        if p.exists() and p.is_dir():
            discovered[str(p.resolve())] = cid

    # Step 2: if not found, look anywhere under base for directories named exactly AU/NZ/UK
    if not discovered:
        for region, cid in region_map.items():
            # Find the first directory named region (case-insensitive)
            try:
                match = next((d for d in base_path.rglob("*") if d.is_dir() and d.name.lower() == region), None)
            except Exception:
                match = None
            if match:
                discovered[str(match.resolve())] = cid

    # Step 3: if still nothing, but there are .txt files under base, index whole base
    if not discovered:
        try:
            has_txt = any(base_path.rglob("*.txt"))
        except Exception:
            has_txt = False
        if has_txt:
            discovered[str(base_path.resolve())] = "1901_all"

    return discovered

if USE_HANSARD_SOURCES_FULL_LAYOUT:
    # Try canonical AU/NZ/UK under base first
    au_path = resolve_path(f"{VECTOR_SOURCES_BASE}/AU")
    nz_path = resolve_path(f"{VECTOR_SOURCES_BASE}/NZ")
    uk_path = resolve_path(f"{VECTOR_SOURCES_BASE}/UK")
    corpora: Dict[str, str] = {
        au_path: "1901_au",
        nz_path: "1901_nz",
        uk_path: "1901_uk",
    }
    # Check existence; if missing, auto-discover
    if not any(Path(p).exists() for p in corpora.keys()):
        print("[vs] Canonical AU/NZ/UK dirs not found; auto-discovering corpus roots…")
        corpora = _discover_corpora(VECTOR_SOURCES_BASE)
else:
    # Legacy local layout under repo_root/vector_sources
    corpora = {
        resolve_path(f"{VECTOR_SOURCES_BASE}/1901/au/hofreps/txt"): "1901_au",
        resolve_path(f"{VECTOR_SOURCES_BASE}/1901/nz/hofreps/txt"): "1901_nz",
        resolve_path(f"{VECTOR_SOURCES_BASE}/1901/uk/hofcoms/txt"): "1901_uk",
    }

# Log what we're using
for path, cid in corpora.items():
    state = "OK" if Path(path).exists() else "MISSING"
    print(f"[vs] corpus={cid} dir={path} [{state}]")
if not corpora:
    print(f"[vs] No corpus roots discovered under {VECTOR_SOURCES_BASE}. Nothing to index.")

def _init_counters(corpora_map: Dict[str, str]):
    ids = sorted(set(corpora_map.values())) if corpora_map else ["1901_all"]
    return (
        {cid: 0 for cid in ids},  # corpus_file_counts
        {cid: 0 for cid in ids},  # chunk_counts_per_corpus
        {cid: 0 for cid in ids},  # chars_per_corpus
        {cid: 0 for cid in ids},  # words_per_corpus
        ids,
    )

# This TXT builder will ignore XML files; it operates only on *.txt recursively.
corpus_file_counts, chunk_counts_per_corpus, chars_per_corpus, words_per_corpus, CORPUS_IDS = _init_counters(corpora)
total_chunks_processed = 0
field_values = defaultdict(set)  # for manifest field schema discovery

# BM25 JSONL output under create/output
BM25_JSONL_PATH = str((Path(__file__).resolve().parents[2] / "create/output/bm25_corpus.jsonl").resolve())
MANIFEST_JSON_PATH = str((Path(__file__).resolve().parents[2] / "create/output/manifest.json").resolve())

def guess_field_type(values):
    try:
        if not values:
            return "string"
        if all(str(v).isdigit() and len(str(v)) == 4 for v in values):
            return "year"
        import re as _re
        if all(_re.match(r"\d{4}-\d{2}-\d{2}", str(v)) for v in values):
            return "date"
        if len(values) <= 50:
            return "enum"
        return "string"
    except Exception:
        return "string"

def get_target_config():
    """Get configuration from environment variables."""
    try:
        # Get the collection name from environment
        collection_name = os.getenv('CHROMA_COLLECTION_NAME')
        if not collection_name:
            print("Error: CHROMA_COLLECTION_NAME environment variable not set")
            sys.exit(1)
            
        # Get configuration from environment variables
        chunk_size = os.getenv('CHUNK_SIZE')
        chunk_overlap = os.getenv('CHUNK_OVERLAP')
        text_splitter = os.getenv('TEXT_SPLITTER_TYPE')
        
        if not all([chunk_size, chunk_overlap, text_splitter]):
            print("Error: Could not find all required configuration in environment variables")
            print("Missing variables:")
            if not chunk_size:
                print("  - CHUNK_SIZE")
            if not chunk_overlap:
                print("  - CHUNK_OVERLAP")
            if not text_splitter:
                print("  - TEXT_SPLITTER_TYPE")
            sys.exit(1)
            
        return {
            'COLLECTION_NAME': collection_name,
            'CHUNK_SIZE': int(chunk_size),
            'CHUNK_OVERLAP': int(chunk_overlap),
            'TEXT_SPLITTER_TYPE': text_splitter
        }
    except Exception as e:
        print(f"Error reading target configuration: {e}")
        sys.exit(1)

# Get configuration from target file first
target_config = get_target_config()
COLLECTION_NAME = target_config['COLLECTION_NAME']

# Then get other environment variables
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')
FINE_TUNE = os.getenv('FINE_TUNE', 'false').lower() == 'true'
POOLING = os.getenv('POOLING')

# Validate required environment variables
required_vars = {
    'EMBEDDING_MODEL': EMBEDDING_MODEL,
    'POOLING': POOLING
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    print("Error: The following required environment variables are not set:")
    for var in missing_vars:
        print(f"  - {var}")
    sys.exit(1)

# Get other configuration from target file
TEXT_SPLITTER_TYPE = target_config['TEXT_SPLITTER_TYPE']
CHUNK_SIZE = target_config['CHUNK_SIZE']
CHUNK_OVERLAP = target_config['CHUNK_OVERLAP']

# Processing configuration
BATCH_SIZE = 100  # This is a processing parameter, not a target configuration
LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS = int(os.getenv('LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS', '0'))
LARGE_RETRIEVAL_SIZE_ALL_CORPUS = int(os.getenv('LARGE_RETRIEVAL_SIZE_ALL_CORPUS', '0'))

# -------------------------------------------------------------
# Pooling strategy
#   Controlled via the POOLING environment variable so that
#   the same setting can be used during both index time and
#   query time.
#   Supported values:
#       mean       – arithmetic mean of all token vectors (default)
#       cls        – [CLS] token only
#       mean+max   – concatenation of mean & max vectors (doubles dim)
# -------------------------------------------------------------
POOLING = os.getenv("POOLING", "mean").lower()

# Define output directories under repo_root/create/output
OUTPUT_DIR = str((Path(__file__).resolve().parents[2] / "create" / "output").resolve())
OUTPUT_CHROMA_DIR = os.path.join(OUTPUT_DIR, "chroma_db")

# Optional: CHROMA_PERSIST_DIRECTORY can be used by deployments, but we do not require it here
FINAL_CHROMA_DIR = os.environ.get("CHROMA_PERSIST_DIRECTORY")

def ensure_chroma_directory(chroma_dir):
    """Ensure the Chroma directory exists and is empty."""
    try:
        if os.path.exists(chroma_dir):
            # Clear existing directory
            shutil.rmtree(chroma_dir)
        
        # Create fresh directory
        os.makedirs(chroma_dir, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error preparing Chroma directory: {e}")
        return False

def get_text_splitter(splitter_type, chunk_size, chunk_overlap):
    if splitter_type == 'RecursiveCharacterTextSplitter':
        return RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif splitter_type == 'CharacterTextSplitter':
        return CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    else:
        raise ValueError(f"Unsupported text splitter type: {splitter_type}")

def document_generator(directory, glob_pattern="**/*.txt"):
    loader = DirectoryLoader(
        directory,
        glob=glob_pattern,
        loader_cls=TextLoader,
        loader_kwargs={"autodetect_encoding": True}
    )
    try:
        docs = loader.load()
        for doc in docs:
            yield doc
    except Exception as e:
        print(f"Error loading documents from {directory}: {e}")
        return

def compute_embedding(text, tokenizer, model):
    try:
        # Get the device from the model
        device = next(model.parameters()).device
        
        # Tokenize and move to the same device as the model
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Forward pass
        with torch.no_grad():
            outputs = model(**inputs)

        hidden = outputs.last_hidden_state  # (batch, seq_len, dim)

        # Pool according to POOLING strategy
        if POOLING == "cls":
            pooled = hidden[:, 0, :]  # first token
        elif POOLING == "mean+max":
            mean_vec = hidden.mean(dim=1)
            max_vec = hidden.max(dim=1).values
            pooled = torch.cat([mean_vec, max_vec], dim=1)  # (batch, 2*dim)
        else:  # default to mean pooling
            pooled = hidden.mean(dim=1)

        # Move result back to CPU for numpy conversion
        embedding = pooled.squeeze().cpu().numpy()
        return embedding
    except Exception as e:
        print(f"Error computing embedding for text: {text[:50]}... - {str(e)}")
        return None

def extract_date_from_filename(filename):
    if filename:
        match = re.search(r'(\w+, \d{1,2}(?:st|nd|rd|th)? \w+, \d{4})', filename)
        if match:
            return match.group(0)
    return "Unknown Date"

def extract_url(text):
    matches = re.finditer(r'<url>(https?://[^\s]+)</url>', text)
    return [(match.start(), match.group(1)) for match in matches]

def extract_page_number(text):
    matches = re.finditer(r'<page>(\d+)</page>', text)
    return [(match.start(), match.group(1)) for match in matches]

def generate_unique_key(base_key, chunk_idx, corpus_metadata, page=None):
    # Deterministic ID used by both Chroma and BM25 JSONL
    p = f"p{page}" if page is not None else "p0"
    return f"{corpus_metadata}::{base_key}::{p}::c{chunk_idx}"

def process_corpus(directory, metadata, vector_store, tokenizer, model, bm25_out):
    # Set up corpus-specific logging
    corpus_log_file = os.path.join(OUTPUT_DIR, f"{metadata}_processing.log")
    print(f"Starting processing for corpus: {metadata} (Logging to {corpus_log_file})")
    
    # Initialize corpus log file
    with open(corpus_log_file, 'w') as log_file:
        log_file.write(f"=== Processing Log for {metadata} Corpus ===\n")
        log_file.write(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    # Helper function for corpus-specific logging
    def corpus_log(message):
        print(f"[{metadata}] {message}")
        with open(corpus_log_file, 'a') as log_file:
            log_file.write(f"{message}\n")
    
    text_splitter = get_text_splitter(TEXT_SPLITTER_TYPE, CHUNK_SIZE, CHUNK_OVERLAP)
    global corpus_file_counts, chunk_counts_per_corpus, chars_per_corpus, words_per_corpus, total_chunks_processed
    # Counters are already initialised globally; do not reset here to avoid wiping
    # results when the same corpus directory is processed multiple times.
    texts, metadatas, embeddings, ids = [], [], [], []
    chunk_counter = 0
    skipped_chunks = 0
    successful_batches = 0
    
    # Helper function to add batches to vector store with validation
    def add_batch_to_store(texts_batch, metadatas_batch, embeddings_batch, ids_batch, add_debug_info=False):
        nonlocal texts, metadatas, embeddings, ids, successful_batches
        
        if not texts_batch:
            corpus_log("Empty batch, skipping")
            return True
        
        # Filter out any entries with None or empty values
        valid_entries = []
        for i, (text, meta, emb, _id) in enumerate(zip(texts_batch, metadatas_batch, embeddings_batch, ids_batch)):
            if text and meta and emb is not None:
                # Convert any potential None values in metadata to strings
                for key in meta:
                    if meta[key] is None:
                        meta[key] = "None"
                valid_entries.append((text, meta, emb, _id))
            elif add_debug_info:
                corpus_log(f"  Skipping index {i}: missing {'text' if not text else ''}{' metadata' if not meta else ''}{' embedding' if emb is None else ''}")
        
        if not valid_entries:
            corpus_log("No valid entries in batch after filtering, skipping")
            return True

        # Unpack the valid entries
        texts_filtered, metadatas_filtered, embeddings_filtered, ids_filtered = zip(*valid_entries)
        texts_filtered, metadatas_filtered, embeddings_filtered, ids_filtered = list(texts_filtered), list(metadatas_filtered), list(embeddings_filtered), list(ids_filtered)

        try:
            corpus_log(f"Adding batch with {len(texts_filtered)} valid entries")
            vector_store.add_texts(texts_filtered, metadatas=metadatas_filtered, embeddings=embeddings_filtered, ids=ids_filtered)
            texts, metadatas, embeddings, ids = [], [], [], []
            successful_batches += 1
            return True
        except Exception as e:
            corpus_log(f"Error adding batch to vector store: {e}")
            # If batch is small or there's a NoneType error, try verbose debugging
            if len(texts_filtered) <= 10 or "NoneType" in str(e):
                for i, (t, m, emb) in enumerate(zip(texts_filtered, metadatas_filtered, embeddings_filtered)):
                    corpus_log(f"  Entry {i}: text={type(t)}, metadata={type(m)}, embedding={type(emb)}")
                    if "NoneType" in str(e):
                        corpus_log(f"    Metadata: {m}")
            
            # Try half-size batch if original batch is large enough
            if len(texts_filtered) > 10:
                half_size = len(texts_filtered) // 2
                corpus_log(f"Trying with reduced batch size ({half_size})")
                try:
                    vector_store.add_texts(
                        texts_filtered[:half_size],
                        metadatas=metadatas_filtered[:half_size],
                        embeddings=embeddings_filtered[:half_size],
                        ids=ids_filtered[:half_size]
                    )
                    texts = texts_filtered[half_size:]
                    metadatas = metadatas_filtered[half_size:]
                    embeddings = embeddings_filtered[half_size:]
                    ids = ids_filtered[half_size:]
                    successful_batches += 1
                    return True
                except Exception as e2:
                    corpus_log(f"Failed with reduced batch: {e2}")
                    if "NoneType" in str(e2):
                        # Try even smaller batch with item-by-item inspection
                        return False
            return False
    
    try:
        documents = list(document_generator(directory))
        corpus_file_counts[metadata] = len(documents)
        corpus_log(f"Loaded {len(documents)} documents from {metadata}")
        
        for doc in tqdm(documents, desc=f"Processing {metadata}", ncols=80):
            try:
                date_info = extract_date_from_filename(doc.metadata.get('source', '')) 
                if date_info == "Unknown Date":
                    content_match = re.search(r'(\w+, \d{1,2}(?:st|nd|rd|th)? \w+, \d{4})', doc.page_content)
                    if content_match:
                        date_info = content_match.group(0)
                
                url_info = extract_url(doc.page_content)
                page_info = extract_page_number(doc.page_content)
                top_url = url_info[0][1] if url_info else None  # Use None value instead of "None" string
                
                if not page_info:
                    current_url = top_url
                    clean_section = re.sub(r'<url>https?://[^\s]+</url>', '', doc.page_content)
                    if not clean_section.strip():
                        print(f"Skipping empty document")
                        continue
                        
                    chunked_texts = text_splitter.split_text(clean_section)
                    for chunk_idx, chunk in enumerate(chunked_texts):
                        if not chunk.strip():
                            skipped_chunks += 1
                            continue
                            
                        embedding = compute_embedding(chunk, tokenizer, model)
                        if embedding is not None:
                            chunk_counter += 1
                            
                            base_file = Path(doc.metadata.get('source', '')).name
                            doc_id = generate_unique_key(base_file, chunk_idx, metadata, page=None)
                            metadata_dict = {
                                "date": date_info or "Unknown",
                                "url": current_url,  # Will be None if no URL is found
                                "page": None,
                                "loc": json.dumps({
                                    "lines": {
                                        "from": chunk_idx * (CHUNK_SIZE - CHUNK_OVERLAP) + 1,
                                        "to": (chunk_idx + 1) * CHUNK_SIZE
                                    }
                                }),
                                "corpus": metadata,
                                "id": doc_id,
                                "source_path": doc.metadata.get('source', ''),
                                "source_relpath": str(Path(doc.metadata.get('source', '')).relative_to(directory)) if doc.metadata.get('source') else base_file,
                            }
                            # Update field schema
                            for k, v in metadata_dict.items():
                                field_values[k].add(str(v))
                            
                            # Validate embedding before adding
                            if isinstance(embedding, np.ndarray) and not np.isnan(embedding).any() and not np.isinf(embedding).any():
                                texts.append(chunk)
                                metadatas.append(metadata_dict)
                                embeddings.append(embedding.tolist())
                                ids.append(doc_id)

                                # Stream to BM25 JSONL
                                bm25_out.write(json.dumps({
                                    "id": doc_id,
                                    "text": chunk,
                                    "metadata": metadata_dict,
                                }, ensure_ascii=False) + "\n")

                                # Update corpus-level statistics for this chunk
                                chunk_counts_per_corpus[metadata] += 1
                                total_chunks_processed += 1
                                chars_per_corpus[metadata] += len(chunk)
                                words_per_corpus[metadata] += len(chunk.split())
                            else:
                                print(f"Skipping chunk with invalid embedding (contains NaN/inf)")
                                skipped_chunks += 1
                                continue
                                
                            # Process batch when we reach the batch size
                            if len(texts) >= BATCH_SIZE:
                                success = add_batch_to_store(texts, metadatas, embeddings, ids)
                                if success:
                                    corpus_log(f"Added batch to vector store. Total: {chunk_counter} (Skipped: {skipped_chunks})")
                        else:
                            skipped_chunks += 1
                            if skipped_chunks % 10 == 0:
                                corpus_log(f"Skipped {skipped_chunks} chunks due to embedding failures")
                else:
                    sections = re.split(r'(<page>\d+</page>)', doc.page_content)
                    current_page = None
                    current_url = None
                    
                    for section in sections:
                        if section.startswith('<page>'):
                            page_match = re.search(r'<page>(\d+)</page>', section)
                            if page_match:
                                current_page = int(page_match.group(1))
                                if not any(url for pos, url in url_info if pos > section.find('<page>')):
                                    current_url = top_url
                        else:
                            # Skip empty sections
                            if not section.strip():
                                continue
                                
                            # Find URL in section    
                            for _, url in url_info:
                                if section.find(url) != -1:
                                    current_url = url
                                    break
                                    
                            if current_page is not None:
                                clean_section = re.sub(r'<url>https?://[^\s]+</url>', '', section)
                                if not clean_section.strip():
                                    continue
                                    
                                chunked_texts = text_splitter.split_text(clean_section)
                                for chunk_idx, chunk in enumerate(chunked_texts):
                                    if not chunk.strip():
                                        skipped_chunks += 1
                                        continue
                                        
                                    embedding = compute_embedding(chunk, tokenizer, model)
                                    if embedding is not None:
                                        chunk_counter += 1
                                        base_file = Path(doc.metadata.get('source', '')).name
                                        doc_id = generate_unique_key(base_file, chunk_idx, metadata, page=current_page)
                                        metadata_dict = {
                                            "date": date_info or "Unknown",
                                            "url": current_url,  # Will be None if no URL is found
                                            "page": current_page,
                                            "loc": json.dumps({
                                                "lines": {
                                                    "from": chunk_idx * (CHUNK_SIZE - CHUNK_OVERLAP) + 1,
                                                    "to": (chunk_idx + 1) * CHUNK_SIZE
                                                }
                                            }),
                                            "corpus": metadata,
                                            "id": doc_id,
                                            "source_path": doc.metadata.get('source', ''),
                                            "source_relpath": str(Path(doc.metadata.get('source', '')).relative_to(directory)) if doc.metadata.get('source') else base_file,
                                        }
                                        # Update field schema
                                        for k, v in metadata_dict.items():
                                            field_values[k].add(str(v))
                                        
                                        # Validate embedding before adding
                                        if isinstance(embedding, np.ndarray) and not np.isnan(embedding).any() and not np.isinf(embedding).any():
                                            texts.append(chunk)
                                            metadatas.append(metadata_dict)
                                            embeddings.append(embedding.tolist())
                                            ids.append(doc_id)

                                            # Stream to BM25 JSONL
                                            bm25_out.write(json.dumps({
                                                "id": doc_id,
                                                "text": chunk,
                                                "metadata": metadata_dict,
                                            }, ensure_ascii=False) + "\n")

                                            # Update corpus-level statistics for this chunk
                                            chunk_counts_per_corpus[metadata] += 1
                                            total_chunks_processed += 1
                                            chars_per_corpus[metadata] += len(chunk)
                                            words_per_corpus[metadata] += len(chunk.split())
                                        else:
                                            print(f"Skipping chunk with invalid embedding (contains NaN/inf)")
                                            skipped_chunks += 1
                                            continue
                                            
                                        # Process batch when we reach the batch size
                                        if len(texts) >= BATCH_SIZE:
                                            success = add_batch_to_store(texts, metadatas, embeddings, ids)
                                            if success:
                                                corpus_log(f"Added batch to vector store. Total: {chunk_counter} (Skipped: {skipped_chunks})")
                                    else:
                                        skipped_chunks += 1
                                        if skipped_chunks % 10 == 0:
                                            corpus_log(f"Skipped {skipped_chunks} chunks due to embedding failures")
            except Exception as e:
                corpus_log(f"Error processing document: {e}")
    except Exception as e:
        corpus_log(f"Error processing corpus {metadata}: {e}")
    
    # Log final statistics for this corpus
    corpus_log(f"\nProcessing complete for corpus: {metadata}")
    corpus_log(f"Files processed: {corpus_file_counts[metadata]}")
    corpus_log(f"Chunks processed: {chunk_counts_per_corpus[metadata]}")
    corpus_log(f"Successful batches: {successful_batches}")
    corpus_log(f"Skipped chunks: {skipped_chunks}")
    corpus_log(f"Characters processed: {chars_per_corpus[metadata]}")
    corpus_log(f"Words processed: {words_per_corpus[metadata]}")
    corpus_log(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def get_machine_info():
    """Get detailed information about the machine running the script."""
    try:
        # Get CPU information
        cpu_info = {
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(logical=False),  # Physical cores
            "cpu_count_logical": psutil.cpu_count(logical=True),  # Logical cores
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "python_version": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "gpu_available": torch.cuda.is_available(),
        }
        
        # Get GPU information if available
        if cpu_info["gpu_available"]:
            gpu = torch.cuda.get_device_properties(0)
            cpu_info.update({
                "gpu_name": gpu.name,
                "gpu_memory_gb": round(gpu.total_memory / (1024**3), 2),
                "gpu_memory_allocated_gb": round(torch.cuda.memory_allocated(0) / (1024**3), 2),
                "gpu_memory_reserved_gb": round(torch.cuda.memory_reserved(0) / (1024**3), 2),
                "gpu_capability": f"{gpu.major}.{gpu.minor}",
                "gpu_multi_processor_count": gpu.multi_processor_count,
            })
        
        # Get disk information
        disk = psutil.disk_usage('/')
        cpu_info.update({
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
        })
        
        return cpu_info
    except Exception as e:
        print(f"Warning: Could not get complete machine info: {e}")
        return {
            "processor": "Unknown",
            "cpu_count": 0,
            "cpu_count_logical": 0,
            "memory_total_gb": 0,
            "python_version": platform.python_version(),
            "system": platform.system(),
            "architecture": platform.machine(),
            "gpu_available": torch.cuda.is_available(),
        }

def get_model_info():
    """Get information about the embedding model."""
    global model_info
    return model_info

def generate_vector_store_stats(
    collection_name: str,
    model_name: str,
    embedding_dimension: int,
    is_quantized: bool,
    model_hash: str,
    total_chunks: int,
    total_chars: int,
    total_words: int,
    corpus_stats: Dict[str, Dict[str, int]],
    processing_time: float,
    chunk_size: int,
    chunk_overlap: int,
    text_splitter_type: str,
    batch_size: int,
    output_file: str,
    created_iso: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Generate comprehensive statistics about the vector store creation process.

    Returns a tuple of (human_readable_report_text, structured_report_dict).
    """
    try:
        # Get system information
        system_info = {
            "OS": platform.system(),
            "OS Version": platform.version(),
            "Python Version": platform.python_version(),
            "CPU": platform.processor(),
            "CPU Cores": f"{os.cpu_count()} physical, {psutil.cpu_count()} logical",
            "RAM": f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
            "GPU": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
            "CUDA Version": torch.version.cuda if torch.cuda.is_available() else "N/A"
        }

        # Calculate totals first
        total_files = sum(stats['files'] for stats in corpus_stats.values())
        total_corpus_chunks = sum(stats['chunks'] for stats in corpus_stats.values())
        total_corpus_chars = sum(stats['chars'] for stats in corpus_stats.values())
        total_corpus_words = sum(stats['words'] for stats in corpus_stats.values())

        # Start building the statistics string
        created_display = created_iso if created_iso else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        stats_lines = [
            "Vector Store Creation Statistics",
            "=====================================",
            "",
            f"Collection: {collection_name}",
            f"Created: {created_display}",
            "",
            "Model Information",
            "---------------",
            f"Model: {model_name}",
            f"Embedding Dimension: {embedding_dimension}",
            f"Quantized: {is_quantized}",
            f"Model Hash: {model_hash if model_hash != 'unknown' else 'N/A'}",
            "",
            "Processing Configuration",
            "----------------------",
            f"Text Splitter: {text_splitter_type}",
            f"Chunk Size: {chunk_size}",
            f"Chunk Overlap: {chunk_overlap}",
            f"Batch Size: {batch_size}",
            "",
            "Corpus Statistics",
            "---------------"
        ]

        # Add corpus-specific statistics
        composition: Dict[str, Dict[str, float]] = {}
        for corpus_id, stats in corpus_stats.items():
            stats_lines.extend([
                f"\n{corpus_id}:",
                f"  Files: {stats['files']:,}",
                f"  Chunks: {stats['chunks']:,}",
                f"  Characters: {stats['chars']:,}",
                f"  Words: {stats['words']:,}"
            ])

        # Add total corpus statistics
        stats_lines.extend([
            "\nTotal Corpus Statistics",
            "---------------------",
            f"Total Files: {total_files:,}",
            f"Total Chunks: {total_corpus_chunks:,}",
            f"Total Characters: {total_corpus_chars:,}",
            f"Total Words: {total_corpus_words:,}",
            "",
            "Corpus Composition",
            "-----------------"
        ])

        # Add percentage breakdown for each corpus
        for corpus_id, stats in corpus_stats.items():
            files_pct = (stats['files'] / total_files * 100) if total_files > 0 else 0.0
            chunks_pct = (stats['chunks'] / total_corpus_chunks * 100) if total_corpus_chunks > 0 else 0.0
            chars_pct = (stats['chars'] / total_corpus_chars * 100) if total_corpus_chars > 0 else 0.0
            words_pct = (stats['words'] / total_corpus_words * 100) if total_corpus_words > 0 else 0.0

            composition[corpus_id] = {
                "files_pct": round(files_pct, 1),
                "chunks_pct": round(chunks_pct, 1),
                "characters_pct": round(chars_pct, 1),
                "words_pct": round(words_pct, 1),
            }

            stats_lines.extend([
                f"\n{corpus_id}:",
                f"  Files: {files_pct:.1f}%",
                f"  Chunks: {chunks_pct:.1f}%",
                f"  Characters: {chars_pct:.1f}%",
                f"  Words: {words_pct:.1f}%"
            ])

        stats_lines.extend([
            "",
            "Processing Statistics",
            "-------------------",
            f"Total Processing Time: {format_processing_time(processing_time)}",
            f"Total Chunks: {total_chunks:,}",
            f"Total Characters: {total_chars:,}",
            f"Total Words: {total_words:,}",
            "",
            "System Information",
            "----------------",
            f"OS: {system_info['OS']} {system_info['OS Version']}",
            f"Python: {system_info['Python Version']}",
            f"CPU: {system_info['CPU']}",
            f"CPU Cores: {system_info['CPU Cores']}",
            f"RAM: {system_info['RAM']}",
            f"GPU: {system_info['GPU']}",
            f"CUDA Version: {system_info['CUDA Version']}"
        ])

        # Join all lines with newlines and write to file
        stats = "\n".join(stats_lines)
        with open(output_file, 'w') as f:
            f.write(stats)
            
        print(f"\nStatistics written to: {output_file}")

        # Build a structured report dict mirroring the text file
        report_dict: Dict[str, Any] = {
            "collection": collection_name,
            "created": created_display,
            "model": {
                "name": model_name,
                "embedding_dimension": embedding_dimension,
                "quantized": is_quantized,
                "hash": model_hash if model_hash not in (None, "unknown") else None,
            },
            "processing_config": {
                "text_splitter": text_splitter_type,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "batch_size": batch_size,
            },
            "corpus_stats": {
                cid: {
                    "files": s["files"],
                    "chunks": s["chunks"],
                    "characters": s["chars"],
                    "words": s["words"],
                }
                for cid, s in corpus_stats.items()
            },
            "totals": {
                "total_files": total_files,
                "total_chunks": total_corpus_chunks,
                "total_characters": total_corpus_chars,
                "total_words": total_corpus_words,
            },
            "composition": composition,
            "processing_stats": {
                "total_processing_time": format_processing_time(processing_time),
                "total_chunks": total_chunks,
                "total_characters": total_chars,
                "total_words": total_words,
            },
            "system": system_info,
        }

        return stats, report_dict
        
    except Exception as e:
        print(f"Error generating statistics: {e}")
        traceback.print_exc()
        return "", {}

def verify_corpus_documents(vector_store):
    """Verify that documents from all corpora are retrievable from the vector store."""
    verification_results = {}
    
    # Test query for each corpus
    test_query = "parliament"
    
    for corpus_id in CORPUS_IDS:
        try:
            # Try to retrieve documents with corpus filter
            results = vector_store.similarity_search(
                test_query,
                k=5,  # Retrieve up to 5 documents
                filter={"corpus": corpus_id}
            )
            
            # Check if we got any results
            if results:
                verification_results[corpus_id] = {
                    "status": "SUCCESS",
                    "count": len(results),
                    "sample": results[0].page_content[:100] + "..."
                }
            else:
                verification_results[corpus_id] = {
                    "status": "EMPTY",
                    "count": 0,
                    "error": "No documents found"
                }
                
        except Exception as e:
            verification_results[corpus_id] = {
                "status": "ERROR",
                "error": str(e)
            }
    
    # Write verification results to file
    verification_file = os.path.join(OUTPUT_DIR, "corpus_verification.json")
    with open(verification_file, 'w') as f:
        json.dump(verification_results, f, indent=2)
    
    # Check if any corpus failed verification
    failed_corpora = [corpus for corpus, result in verification_results.items() 
                     if result.get("status") != "SUCCESS"]
    
    if failed_corpora:
        print(f"⚠️ WARNING: Some corpora may have issues - check verification report")
    
    return verification_results

def get_collection(chroma_dir: str):
    """Get the Chroma collection."""
    try:
        client = PersistentClient(path=chroma_dir)
        return client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Error getting collection: {e}")
        return None

def get_corpus_document_counts(collection) -> Dict[str, int]:
    """Get document counts for each corpus."""
    try:
        counts = {}
        for corpus_id in CORPUS_IDS:
            result = collection.get(
                where={"corpus": corpus_id},
                include=["metadatas"]
            )
            counts[corpus_id] = len(result['ids'])
        return counts
    except Exception as e:
        print(f"Error getting corpus counts: {e}")
        return {}

def get_embedding_dimensions(collection) -> int:
    """Get the embedding dimensions from the collection."""
    try:
        # Get a single document to check dimensions
        result = collection.get(limit=1)
        if result and result['embeddings']:
            return len(result['embeddings'][0])
        return 0
    except Exception as e:
        print(f"Error getting embedding dimensions: {e}")
        return 0

def format_processing_time(seconds: float) -> str:
    """Format processing time in a human-friendly way."""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"

def main():
    """Main function to create the Chroma vector store."""
    print("Starting Chroma vector store creation...")
    
    # Prepare output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Persist the Chroma DB only to create/output/chroma_db (avoid overwriting a working store)
    chroma_dir = os.path.join(OUTPUT_DIR, "chroma_db")
    
    # Ensure Chroma directory is ready
    if not ensure_chroma_directory(chroma_dir):
        print("Failed to prepare Chroma directory. Exiting.")
        sys.exit(1)
    
    # Check for GPU availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Initialize the embedding model
    print(f"Initializing embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    # Store model information
    global model_info
    model_info = {
        "model_name": EMBEDDING_MODEL,
        "model_dimensions": 768,  # Default for BERT models
        "is_quantized": False,
        "model_hash": None
    }
    
    # Initialize the vector store with journal mode settings
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=chroma_dir
    )
    
    # Set SQLite journal mode to DELETE to prevent WAL files
    try:
        import sqlite3
        db_path = os.path.join(chroma_dir, "chroma.sqlite3")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA journal_mode = DELETE;")
            conn.commit()
            conn.close()
            print("Set SQLite journal mode to DELETE")
    except Exception as e:
        print(f"Warning: Could not set journal mode: {e}")
    
    # Initialize tokenizer and model for fine-tuning
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    model = AutoModel.from_pretrained(EMBEDDING_MODEL)
    model.to(device)
    
    # Update model info with actual model properties
    model_info["model_dimensions"] = model.config.hidden_size
    
    # Check if model is quantized (basic check)
    model_info["is_quantized"] = hasattr(model, 'quantization_config') and model.quantization_config is not None
    
    # Get model hash from config if available
    try:
        import hashlib
        model_str = str(model.config.to_dict())
        model_info["model_hash"] = hashlib.md5(model_str.encode()).hexdigest()[:8]
    except:
        model_info["model_hash"] = "unknown"
    
    # Prepare BM25 JSONL
    Path(BM25_JSONL_PATH).parent.mkdir(parents=True, exist_ok=True)
    bm25_out = open(BM25_JSONL_PATH, 'w', encoding='utf-8')

    # Process each corpus
    start_time = time.time()
    processing_times = {}
    
    for directory, corpus_id in corpora.items():
        corpus_start_time = time.time()
        print(f"\nProcessing corpus: {corpus_id}")
        process_corpus(directory, corpus_id, vector_store, tokenizer, model, bm25_out)
        processing_times[corpus_id] = time.time() - corpus_start_time
    
    total_time = time.time() - start_time
    
    # Persist the vector store
    vector_store.persist()
    print("\nChroma vector store created and automatically persisted")
    
    # Set journal mode to DELETE after persistence to prevent WAL files
    try:
        import sqlite3
        db_path = os.path.join(chroma_dir, "chroma.sqlite3")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA journal_mode = DELETE;")
            conn.commit()
            conn.close()
            print("Final SQLite journal mode set to DELETE")
    except Exception as e:
        print(f"Warning: Could not set final journal mode: {e}")

    # Note: we persist only to create/output/chroma_db to prevent accidental overwrite of a live store
    
    # Close BM25 JSONL
    try:
        bm25_out.close()
        print(f"BM25 JSONL written to: {BM25_JSONL_PATH}")
    except Exception:
        pass

    # Generate statistics
    stats_file = os.path.join(OUTPUT_DIR, f"{COLLECTION_NAME}.txt")
    # Prepare a single created timestamp for both the text report and manifest
    created_iso = datetime.utcnow().isoformat() + "Z"
    report_text, report_struct = generate_vector_store_stats(
        collection_name=COLLECTION_NAME,
        model_name=EMBEDDING_MODEL,
        embedding_dimension=model_info.get('model_dimensions', 768),
        is_quantized=False,
        model_hash=None,
        total_chunks=total_chunks_processed,
        total_chars=sum(chars_per_corpus.values()),
        total_words=sum(words_per_corpus.values()),
        corpus_stats={corpus_id: {"files": corpus_file_counts[corpus_id], "chunks": chunk_counts_per_corpus[corpus_id], "chars": chars_per_corpus[corpus_id], "words": words_per_corpus[corpus_id]} for corpus_id in CORPUS_IDS},
        processing_time=total_time,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        text_splitter_type=TEXT_SPLITTER_TYPE,
        batch_size=BATCH_SIZE,
        output_file=stats_file,
        created_iso=created_iso,
    )
    
    # Verify corpus documents and create verification report
    verify_corpus_documents(vector_store)
    
    print(f"\n✅ Vector store creation completed successfully!")
    print(f"📊 Statistics file: {stats_file}")
    print(f"🗂️  Database location: {chroma_dir}")
    print(f"📝 Verification report: {os.path.join(OUTPUT_DIR, 'corpus_verification.json')}")
    print(f"📋 Processing logs: {OUTPUT_DIR}/*_processing.log")
    print(f"\n📝 Next steps:")
    print(f"   1. Run 'make r' to generate the matching hansard_retriever.py file")
    print(f"   2. Copy the database to your target location (set by CHROMA_PERSIST_DIRECTORY)")
    print(f"   3. Move hansard_retriever.py to backend/retrievers/ to use with the ATLAS system")
    
    # Build standardized manifest.json
    try:
        # Prepare schema
        schema = {}
        for field, values in field_values.items():
            ftype = guess_field_type(values)
            entry = {"type": ftype}
            if ftype == "enum":
                entry["values"] = sorted(set(values))
            schema[field] = entry

        # Standardized stats structure
        # Compute DB size from the freshly built output directory
        try:
            db_size_mb = round(sum(p.stat().st_size for p in Path(chroma_dir).rglob('*') if p.is_file()) / (1024*1024), 2)
        except Exception:
            db_size_mb = 0.0

        stats = {
            "total_chunks": total_chunks_processed,
            "total_files": sum(corpus_file_counts.values()),
            "db_size_mb": db_size_mb,
            "corpora": {
                cid: {
                    "files": corpus_file_counts[cid],
                    "chunks": chunk_counts_per_corpus[cid],
                    "chars": chars_per_corpus[cid],
                    "words": words_per_corpus[cid],
                }
                for cid in CORPUS_IDS
            }
        }

        manifest = {
            "schema_version": "1.1",
            "index_name": COLLECTION_NAME,
            "embedding_model": EMBEDDING_MODEL,
            "created": created_iso,
            "fields": schema,
            "stats": stats,
            # Include a structured report and the raw text mirroring blert_XXXX.txt
            "report": report_struct,
            "report_text": report_text,
        }

        Path(MANIFEST_JSON_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest written to: {MANIFEST_JSON_PATH}")
    except Exception as e:
        print(f"Warning: could not write manifest.json: {e}")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())