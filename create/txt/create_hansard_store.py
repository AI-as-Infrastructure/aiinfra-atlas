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
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime
from create.prepare_embedding_model import ensure_st_model

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

VECTOR_SOURCES_BASE = "../../../vector_sources"

# Helper to resolve relative paths based on this script's directory
def resolve_path(relative_path):
    script_dir = Path(__file__).resolve().parent
    return str((script_dir / relative_path).resolve())

corpora = {
    resolve_path(f"{VECTOR_SOURCES_BASE}/1901/au/hofreps/txt"): "1901_au",
    resolve_path(f"{VECTOR_SOURCES_BASE}/1901/nz/hofreps/txt"): "1901_nz",
    resolve_path(f"{VECTOR_SOURCES_BASE}/1901/uk/hofcoms/txt"): "1901_uk",
}
CORPUS_IDS = ["1901_au", "1901_nz", "1901_uk"]
corpus_file_counts = {corpus_id: 0 for corpus_id in CORPUS_IDS}
chunk_counts_per_corpus = {corpus_id: 0 for corpus_id in CORPUS_IDS}
chars_per_corpus = {corpus_id: 0 for corpus_id in CORPUS_IDS}
words_per_corpus = {corpus_id: 0 for corpus_id in CORPUS_IDS}
total_chunks_processed = 0

# Chroma configuration
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "blert_1000")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Livingwithmachines/bert_1890_1900")
TEXT_SPLITTER_TYPE = "RecursiveCharacterTextSplitter"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
BATCH_SIZE = 100

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

# Define output directories
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
OUTPUT_CHROMA_DIR = os.path.join(OUTPUT_DIR, "chroma_db")

# Get Chroma directory from environment variable
FINAL_CHROMA_DIR = os.environ.get("CHROMA_PERSIST_DIRECTORY")
if not FINAL_CHROMA_DIR:
    raise ValueError("CHROMA_PERSIST_DIRECTORY environment variable is not set")

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

def document_generator(directory, glob_pattern="*.txt"):
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

def generate_unique_key(base_key, chunk_idx, corpus_metadata):
    return f"{base_key}:{corpus_metadata}:{chunk_idx}"

def process_corpus(directory, metadata, vector_store, tokenizer, model):
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
    texts, metadatas, embeddings = [], [], []
    chunk_counter = 0
    skipped_chunks = 0
    successful_batches = 0
    
    # Helper function to add batches to vector store with validation
    def add_batch_to_store(texts_batch, metadatas_batch, embeddings_batch, add_debug_info=False):
        nonlocal texts, metadatas, embeddings, successful_batches
        
        if not texts_batch:
            corpus_log("Empty batch, skipping")
            return True
        
        # Filter out any entries with None or empty values
        valid_entries = []
        for i, (text, meta, emb) in enumerate(zip(texts_batch, metadatas_batch, embeddings_batch)):
            if text and meta and emb is not None:
                # Convert any potential None values in metadata to strings
                for key in meta:
                    if meta[key] is None:
                        meta[key] = "None"
                valid_entries.append((text, meta, emb))
            elif add_debug_info:
                corpus_log(f"  Skipping index {i}: missing {'text' if not text else ''}{' metadata' if not meta else ''}{' embedding' if emb is None else ''}")
        
        if not valid_entries:
            corpus_log("No valid entries in batch after filtering, skipping")
            return True
            
        # Unpack the valid entries
        texts_filtered, metadatas_filtered, embeddings_filtered = zip(*valid_entries)
        texts_filtered, metadatas_filtered, embeddings_filtered = list(texts_filtered), list(metadatas_filtered), list(embeddings_filtered)
        
        try:
            corpus_log(f"Adding batch with {len(texts_filtered)} valid entries")
            vector_store.add_texts(texts_filtered, metadatas=metadatas_filtered, embeddings=embeddings_filtered)
            texts, metadatas, embeddings = [], [], []
            successful_batches += 1
            return True
        except Exception as e:
            corpus_log(f"Error adding batch to vector store: {e}")
            # If batch is small or there's a NoneType error, try verbose debugging
            if len(texts_filtered) <= 10 or "NoneType" in str(e):
                for i, (t, m, e) in enumerate(zip(texts_filtered, metadatas_filtered, embeddings_filtered)):
                    corpus_log(f"  Entry {i}: text={type(t)}, metadata={type(m)}, embedding={type(e)}")
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
                        embeddings=embeddings_filtered[:half_size]
                    )
                    texts = texts_filtered[half_size:]
                    metadatas = metadatas_filtered[half_size:]
                    embeddings = embeddings_filtered[half_size:]
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
                            
                            # Track statistics for this chunk
                            chunk_counts_per_corpus[metadata] += 1
                            total_chunks_processed += 1
                            chars_per_corpus[metadata] += len(chunk)
                            words_per_corpus[metadata] += len(chunk.split())
                            
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
                                "corpus": metadata 
                            }
                            
                            # Validate embedding before adding
                            if isinstance(embedding, np.ndarray) and not np.isnan(embedding).any() and not np.isinf(embedding).any():
                                texts.append(chunk)
                                metadatas.append(metadata_dict)
                                embeddings.append(embedding.tolist())

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
                                success = add_batch_to_store(texts, metadatas, embeddings)
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
                            for pos, url in url_info:
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
                                            "corpus": metadata 
                                        }
                                        
                                        # Validate embedding before adding
                                        if isinstance(embedding, np.ndarray) and not np.isnan(embedding).any() and not np.isinf(embedding).any():
                                            texts.append(chunk)
                                            metadatas.append(metadata_dict)
                                            embeddings.append(embedding.tolist())

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
                                            success = add_batch_to_store(texts, metadatas, embeddings)
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

def generate_vector_store_stats(chroma_dir=None, output_file=None, processing_times=None, total_time=None):
    """Generate statistics for the Chroma vector store."""
    # Set default output file if not provided
    if output_file is None:
        output_file = os.path.join(OUTPUT_DIR, f"{COLLECTION_NAME}.txt")
    
    # Initialize stats dictionary using tracked statistics
    stats = {
        "total_chunks": total_chunks_processed,
        "total_files": sum(corpus_file_counts.values()),
        "total_chars": sum(chars_per_corpus.values()),
        "total_words": sum(words_per_corpus.values()),
        "total_tokens": 0,  # Will calculate below
        "chroma_size_mb": 0,
        "chunks_per_corpus": chunk_counts_per_corpus,
        "files_per_corpus": corpus_file_counts,
        "chars_per_corpus": chars_per_corpus,
        "words_per_corpus": words_per_corpus,
        "tokens_per_corpus": {corpus_id: 0 for corpus_id in CORPUS_IDS},
        "processing_times": processing_times or {},
        "total_time": total_time or 0
    }
    
    # Store collection name for later use
    collection_name = COLLECTION_NAME
    
    # Try to get Chroma directory size
    if chroma_dir and os.path.exists(chroma_dir):
        try:
            chroma_size = 0
            for dirpath, dirnames, filenames in os.walk(chroma_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    chroma_size += os.path.getsize(fp)
            stats["chroma_size_mb"] = chroma_size / (1024 * 1024)
        except Exception as e:
            print(f"Warning: Could not get Chroma directory size: {e}")
    
    # We don't need to query Chroma since we've tracked statistics during processing
    print(f"Processing statistics for {stats['total_chunks']:,} chunks across {len(CORPUS_IDS)} corpora")
    
    # Calculate estimated token statistics for each corpus based on actual word counts
    # A reasonable estimate is that tokens are about 0.75x the number of words for English text
    for corpus_id in CORPUS_IDS:
        tokens_estimate = int(stats["words_per_corpus"][corpus_id] * 0.75)
        stats["tokens_per_corpus"][corpus_id] = tokens_estimate
        stats["total_tokens"] += tokens_estimate
        
    # Create content for the statistics file (reset content for final manifest)
    content = f"# Vector Store Statistics: {COLLECTION_NAME}\n"
    content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    # Configuration in KEY = VALUE form so the retriever generator can parse it
    content += "## Configuration\n"
    content += f"INDEX_NAME = \"{collection_name}\"\n"
    content += f"EMBEDDING_MODEL = \"{EMBEDDING_MODEL}\"\n"
    content += f"ALGORITHM = \"HNSW\"\n"
    content += f"CHUNK_SIZE = {CHUNK_SIZE}\n"
    content += f"CHUNK_OVERLAP = {CHUNK_OVERLAP}\n"

    # Additional processing information (human-readable)
    content += "\n## Processing Information\n"
    content += f"Text Splitter: {TEXT_SPLITTER_TYPE}\n"
    content += f"Chunk Size: {CHUNK_SIZE}\n"
    content += f"Chunk Overlap: {CHUNK_OVERLAP}\n"
    
    # Creation metadata section
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content += f"## Creation Information\n"
    content += f"Created: {current_time}\n"
    
    if stats["total_time"] > 0:
        hours, remainder = divmod(stats["total_time"], 3600)
        minutes, seconds = divmod(remainder, 60)
        # Store a human-friendly duration string for later reuse
        stats["total_time_human"] = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d} (HH:MM:SS)"
        content += f"Total Processing Time: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d} (HH:MM:SS)\n"
    
    # Processing times per corpus if available
    if stats["processing_times"]:
        content += "\n### Processing Times by Corpus\n"
        for corpus_id, time_seconds in stats["processing_times"].items():
            minutes, seconds = divmod(time_seconds, 60)
            content += f"- {corpus_id}: {int(minutes):02d}:{int(seconds):02d} (MM:SS)\n"
    
    # Overall statistics section
    content += "\n## Overall Statistics\n"
    content += f"Total Chunks: {stats['total_chunks']:,}\n"
    content += f"Total Files Processed: {stats['total_files']:,}\n"
    
    if stats["total_chars"] > 0:
        content += f"Total Characters: {stats['total_chars']:,}\n"
    if stats["total_words"] > 0:
        content += f"Total Words (est.): {stats['total_words']:,}\n"
    if stats["total_tokens"] > 0:
        content += f"Total Tokens (est.): {stats['total_tokens']:,}\n"
    
    if stats["total_time"] > 0:
        content += f"Total Processing Time: {stats['total_time_human']}\n"
    
    if stats["chroma_size_mb"] > 0:
        content += f"Database Size: {stats['chroma_size_mb']:.2f} MB\n"
    
    # Corpus distribution metrics
    content += "\n## Corpus Distribution\n"
    content += f"Number of Corpora: {len(CORPUS_IDS)}\n"
    content += f"Corpora: {', '.join(CORPUS_IDS)}\n"
    
    # Calculate and show corpus distribution percentages
    if stats["total_chunks"] > 0:
        content += "\n### Distribution by Chunk Count\n"
        for corpus_id in CORPUS_IDS:
            chunks = stats["chunks_per_corpus"][corpus_id]
            if chunks > 0:
                percentage = (chunks / stats["total_chunks"]) * 100
                content += f"{corpus_id}: {chunks:,} chunks ({percentage:.1f}%)\n"
    
    # Detailed corpus statistics
    content += "\n## Detailed Corpus Statistics\n"
    for corpus_id in CORPUS_IDS:
        chunks = stats["chunks_per_corpus"][corpus_id]
        if chunks > 0:
            content += f"\n### {corpus_id}\n"
            content += f"Chunks: {chunks:,}\n"
            if stats["files_per_corpus"][corpus_id] > 0:
                content += f"Files Processed: {stats['files_per_corpus'][corpus_id]}\n"
            if stats["chars_per_corpus"][corpus_id] > 0:
                content += f"Characters: {stats['chars_per_corpus'][corpus_id]:,}\n"
            if stats["words_per_corpus"][corpus_id] > 0:
                content += f"Words (est.): {stats['words_per_corpus'][corpus_id]:,}\n"
            if stats["tokens_per_corpus"][corpus_id] > 0:
                content += f"Tokens (est.): {stats['tokens_per_corpus'][corpus_id]:,}\n"
            if stats["files_per_corpus"][corpus_id] > 0:
                avg_chunks = chunks / stats["files_per_corpus"][corpus_id]
                content += f"Average Chunks per File: {avg_chunks:.2f}\n"
    
    # Model information
    content += "\n## Model Information\n"
    content += f"Model: {EMBEDDING_MODEL}\n"
    if "bert_1890_1900" in EMBEDDING_MODEL:
        content += "This model was trained on historical texts from 1890-1900.\n"
    
    # Write the statistics file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"Vector store statistics written to {output_file}")
    print("\nVector Store Creation Complete!")
    print(f"- Chroma directory: {chroma_dir}")
    print(f"- Statistics file: {output_file}")
    
    # Add instructions for moving to final location
    if chroma_dir != FINAL_CHROMA_DIR:
        print("\nIMPORTANT: The Chroma database has been created in a temporary location.")
        print(f"To use it with the application, you need to move it to: {FINAL_CHROMA_DIR}")
        print("\nYou can do this with the following commands:")
        print(f"rm -rf {FINAL_CHROMA_DIR}  # Remove existing database if needed")
        print(f"mkdir -p {os.path.dirname(FINAL_CHROMA_DIR)}  # Ensure parent directory exists")
        print(f"cp -r {chroma_dir} {FINAL_CHROMA_DIR}  # Copy the database to the final location")
    
    return output_file

def verify_corpus_documents(vector_store):
    """Verify that documents from all corpora are retrievable from the vector store."""
    print("\n=== Verifying Corpus Document Retrieval ===")
    verification_results = {}
    
    # Test query for each corpus
    test_query = "parliament"
    
    for corpus_id in CORPUS_IDS:
        print(f"Testing retrieval from corpus: {corpus_id}")
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
                print(f"  ✅ Successfully retrieved {len(results)} documents from {corpus_id}")
            else:
                verification_results[corpus_id] = {
                    "status": "EMPTY",
                    "count": 0,
                    "error": "No documents found"
                }
                print(f"  ⚠️ No documents found for corpus: {corpus_id}")
                
        except Exception as e:
            verification_results[corpus_id] = {
                "status": "ERROR",
                "error": str(e)
            }
            print(f"  ❌ Error retrieving documents from {corpus_id}: {e}")
    
    # Write verification results to file
    verification_file = os.path.join(OUTPUT_DIR, "corpus_verification.json")
    with open(verification_file, 'w') as f:
        json.dump(verification_results, f, indent=2)
    
    print(f"Verification results written to: {verification_file}")
    
    # Check if any corpus failed verification
    failed_corpora = [corpus for corpus, result in verification_results.items() 
                     if result.get("status") != "SUCCESS"]
    
    if failed_corpora:
        print(f"\n⚠️ WARNING: The following corpora may have issues: {', '.join(failed_corpora)}")
        print("Please check the verification results and corpus logs for more details.")
    else:
        print("\n✅ All corpora verified successfully!")
    
    return verification_results

def main():
    """Main function to create the Chroma vector store."""
    print("Starting Chroma vector store creation...")
    
    # Prepare output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    chroma_dir = OUTPUT_CHROMA_DIR
    
    # Ensure Chroma directory is ready
    if not ensure_chroma_directory(chroma_dir):
        print("Failed to prepare Chroma directory. Exiting.")
        sys.exit(1)
    
    # Check for GPU availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"GPU detected! Using {torch.cuda.get_device_name(0)} for acceleration")
    else:
        print("No GPU detected. Using CPU for processing (this may be slower)")
    
    # Determine where the Sentence-Transformer model actually lives
    # 1. If EMBEDDING_MODEL is already a local directory containing modules.json,
    #    use it directly so we don't append another "_st".
    # 2. Otherwise store (or convert) the wrapper under models/<name>_st
    print(f"EMBEDDING_MODEL env-var: {EMBEDDING_MODEL}")
    embed_path = Path(EMBEDDING_MODEL).expanduser()

    print(f"Resolved embed_path: {embed_path}")

    # If EMBEDDING_MODEL already points to a prepared ST directory with
    # modules.json, use it directly.
    if embed_path.is_dir() and (embed_path / "modules.json").exists():
        local_model_path = embed_path
    else:
        # Derive destination folder under ./models while *avoiding*
        # appending a second "_st" when the user has already supplied a
        # wrapper or fine-tuned model name such as *_st* or *_st_ft*.
        base_name = embed_path.name
        if base_name.endswith("_st") or base_name.endswith("_st_ft"):
            local_model_path = Path("models") / base_name
        else:
            local_model_path = Path("models") / f"{base_name}_st"

    print(f"local_model_path selected: {local_model_path}")

    ensure_st_model(EMBEDDING_MODEL, local_model_path)

    print(f"Loading embedding model: {local_model_path} on {device}")
    model_root = local_model_path
    # If the path is a Sentence-Transformer folder, the underlying HF
    # model lives in 0_Transformer; use that for tokenizer/encoder.
    if (local_model_path / "0_Transformer").exists():
        model_root = local_model_path / "0_Transformer"

    tokenizer = AutoTokenizer.from_pretrained(str(model_root))
    model = AutoModel.from_pretrained(str(model_root))
    
    # Move model to GPU if available
    if device == "cuda":
        model = model.to(device)
        print("Model successfully moved to GPU")
    
    # Create Chroma vector store
    print(f"Creating Chroma vector store in {chroma_dir}")
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=HuggingFaceEmbeddings(model_name=str(model_root)),
        persist_directory=chroma_dir
    )
    
    # Initialize tokenizer and model for embeddings with GPU support
    print("Initializing tokenizer and model…")
    
    # Process each corpus
    start_time = time.time()
    processing_times = {}
    
    for directory, corpus_id in corpora.items():
        if os.path.exists(directory):
            print(f"\nProcessing corpus: {corpus_id} from {directory}")
            corpus_start = time.time()
            process_corpus(directory, corpus_id, vector_store, tokenizer, model)
            corpus_end = time.time()
            processing_times[corpus_id] = corpus_end - corpus_start
        else:
            print(f"Warning: Directory not found for corpus {corpus_id}: {directory}")
    
    # Chroma automatically persists data in version 0.4.x and later
    print("\nChroma vector store created and automatically persisted")
    
    # Generate statistics
    total_time = time.time() - start_time
    output_file = os.path.join(OUTPUT_DIR, f"{COLLECTION_NAME}.txt")
    print(f"\nGenerating statistics file: {output_file}")
    generate_vector_store_stats(
        chroma_dir=chroma_dir,
        output_file=output_file,
        processing_times=processing_times,
        total_time=total_time
    )
    
    # Verify that documents from all corpora are retrievable
    print("\nVerifying corpus document retrieval...")
    verification_results = verify_corpus_documents(vector_store)
    
    # Final summary
    def _fmt_dur(secs):
        h, r = divmod(int(secs), 3600)
        m, s = divmod(r, 60)
        return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

    print("\n=== Vector Store Creation Summary ===")
    print(f"Total processing time: {_fmt_dur(total_time)} ({total_time:.2f} seconds)")
    print(f"Total documents processed: {sum(corpus_file_counts.values())}")
    print(f"Total chunks processed: {sum(chunk_counts_per_corpus.values())}")
    print(f"Corpus distribution:")
    for corpus_id in CORPUS_IDS:
        print(f"  - {corpus_id}: {chunk_counts_per_corpus[corpus_id]} chunks from {corpus_file_counts[corpus_id]} files")
        verification_status = verification_results.get(corpus_id, {}).get("status", "UNKNOWN")
        verification_count = verification_results.get(corpus_id, {}).get("count", 0)
        print(f"    Verification: {verification_status} ({verification_count} documents retrievable)")
    
    print("\nChroma vector store creation completed successfully!")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())