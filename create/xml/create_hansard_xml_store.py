#!/usr/bin/env python3
"""Build a Chroma HNSW store from Hansard XML corpora (AU + UK).

• Scans input directories for XML files (default relative paths used in
  previous prototype).
• Uses the parser registry in `hansard_parsers.py` to extract `Speech`
  objects (plain-text + metadata).
• Chunks speeches with RecursiveCharacterTextSplitter, embeds with a
  HuggingFace model, and stores them in Chroma.
• Writes a `manifest.json` capturing metadata schema so that retrievers
  & UIs can self-configure later.

Run:
    python create/xml/create_hansard_xml_store.py \
        --out-dir backend/targets/chroma_db_xml

Environment variables that can override defaults:
    CHROMA_PERSIST_DIRECTORY
    EMBEDDING_MODEL

The script is intentionally dependency-free apart from LangChain +
Chroma stack already used elsewhere in the project.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from tqdm import tqdm
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
import numpy as np

# Local imports
# (we can import because create/xml is a package via __init__.py)
from create.xml.hansard_parsers import PARSER_REGISTRY, Speech
from create.prepare_embedding_model import ensure_st_model

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_EMBEDDING_MODEL = "Livingwithmachines/bert_1890_1900"
DEFAULT_CHROMA_DIR = "backend/targets/chroma_db_xml"

# Input corpus mapping: path -> parser key
CORPORA: Dict[str, str] = {
    # AUSTRALIA
    "xml/au/hofreps": "1901_au",
    # UNITED KINGDOM
    "xml/uk/hofcoms": "1901_uk",
}

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
BATCH_SIZE = 100

# ---------------------------------------------------------------------------
# Helper – decide field type for manifest
# ---------------------------------------------------------------------------

def guess_field_type(values: Set[str]):
    if not values:
        return "string"
    if all(v.isdigit() and len(v) == 4 for v in values):
        return "year"
    if all(re.match(r"\d{4}-\d{2}-\d{2}", v) for v in values):
        return "date"
    if len(values) <= 50:
        return "enum"
    return "string"

# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_store(out_dir: Path, embedding_model: str):
    # Prepare output directory
    if out_dir.exists():
        print(f"Removing existing Chroma directory at {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Ensure the model exists locally in ST format (under models/)
    local_model_path = Path("models") / Path(embedding_model).name
    ensure_st_model(embedding_model, local_model_path)

    model_to_load = str(local_model_path)
    print(f"Embedding model path: {model_to_load}")
    embeddings = HuggingFaceEmbeddings(model_name=model_to_load)

    vector_store = Chroma(
        collection_name="hansard_xml",
        embedding_function=embeddings,
        persist_directory=str(out_dir),
    )

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    # Schema discovery
    field_values: Dict[str, Set[str]] = defaultdict(set)

    # Stats trackers
    stats = {
        "total_chunks": 0,
        "total_files": 0,
        "corpora": defaultdict(lambda: {"files": 0, "chunks": 0, "chars": 0, "words": 0}),
    }

    for corpus_path, corpus_id in CORPORA.items():
        parser = PARSER_REGISTRY.get(corpus_id)
        if parser is None:
            print(f"[WARN] No parser registered for {corpus_id}, skipping")
            continue
        xml_root = Path(corpus_path)
        xml_files = list(xml_root.glob("*.xml")) if xml_root.exists() else list(xml_root.glob("*.txt"))
        print(f"Processing {len(xml_files)} XML files for corpus {corpus_id} ({corpus_path})")

        stats["corpora"][corpus_id]["files"] += len(xml_files)

        for xml_file in tqdm(xml_files, desc=f"{corpus_id}"):
            try:
                for speech in parser.iter_speeches(xml_file):
                    # Update schema tracker
                    for k, v in speech.metadata.items():
                        field_values[k].add(str(v))

                    # Chunking
                    chunks = splitter.split_text(speech.text)
                    metadatas: List[Dict[str, str]] = []
                    texts: List[str] = []
                    for idx, chunk in enumerate(chunks):
                        md = speech.metadata.copy()
                        md["loc"] = json.dumps({"chunk": idx})
                        texts.append(chunk)
                        metadatas.append(md)
                        # flush batch
                        if len(texts) >= BATCH_SIZE:
                            vector_store.add_texts(texts=texts, metadatas=metadatas)
                            texts, metadatas = [], []
                    if texts:
                        vector_store.add_texts(texts=texts, metadatas=metadatas)

                    # stats
                    stats["corpora"][corpus_id]["chunks"] += 1
                    stats["total_chunks"] += 1
                    stats["corpora"][corpus_id]["chars"] += len(chunk)
                    stats["corpora"][corpus_id]["words"] += len(chunk.split())
            except Exception as e:
                print(f"[ERROR] Failed to parse {xml_file}: {e}")

    print("Persisting Chroma store …")
    vector_store.persist()

    stats["total_files"] = sum(c["files"] for c in stats["corpora"].values())

    # Add DB size in MB
    size_bytes = 0
    for p in out_dir.rglob("*"):
        if p.is_file():
            size_bytes += p.stat().st_size
    stats["db_size_mb"] = round(size_bytes / (1024 * 1024), 2)

    # ---------------------------------------------------------------------
    # Manifest
    # ---------------------------------------------------------------------
    schema: Dict[str, Dict] = {}
    for field, values in field_values.items():
        ftype = guess_field_type(values)
        entry: Dict = {"type": ftype}
        if ftype == "enum":
            entry["values"] = sorted(values)
        schema[field] = entry

    manifest = {
        "index_name": "hansard_xml",
        "embedding_model": model_to_load,
        "created": datetime.utcnow().isoformat() + "Z",
        "fields": schema,
        "stats": stats,
    }

    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {manifest_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Hansard XML Chroma store")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_CHROMA_DIR, help="Directory for Chroma persistence")
    parser.add_argument("--embedding-model", default=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL), help="HF repo or local path of embedding model")
    args = parser.parse_args()

    build_store(args.out_dir, args.embedding_model) 