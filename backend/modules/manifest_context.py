"""
Manifest context utilities.

This module provides helpers to load backend/corpus/manifest.json and
expose a concise summary as a LangChain Document for inclusion in LLM context
when users ask meta questions about the vector store (counts, model, etc.).
"""

from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any


def _manifest_path() -> str:
    """Return absolute path to backend/corpus/manifest.json."""
    # This file lives in backend/modules -> ascend to backend/corpus
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(current_dir, "..", "corpus", "manifest.json"))


def load_manifest() -> Optional[Dict[str, Any]]:
    """Load manifest.json if available, else None."""
    path = _manifest_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Fall back to raw text as a minimal compatibility measure
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_text = f.read()
            return {"_raw": raw_text}
        except Exception:
            return None


def _fmt_num(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        try:
            return f"{float(n):,.2f}"
        except Exception:
            return str(n)


def build_manifest_summary(data: Dict[str, Any]) -> str:
    """Build a concise human-readable summary string from manifest JSON."""
    if "_raw" in data:
        return data["_raw"]  # return raw content if JSON parse failed but file was readable

    index_name = data.get("index_name", "(unknown)")
    embedding_model = data.get("embedding_model", "(unknown)")
    created = data.get("created")
    chunk_size = data.get("chunk_size")
    chunk_overlap = data.get("chunk_overlap")
    stats = data.get("stats", {}) or {}
    corpora = (stats.get("corpora") or {}) if isinstance(stats, dict) else {}
    total_chunks = stats.get("total_chunks")
    # We intentionally avoid non-standard totals (e.g., speeches) to keep
    # parity across corpora. Only display standardized fields.
    total_files = stats.get("total_files")
    db_size_mb = stats.get("db_size_mb")

    # Aggregate totals for words and chars if available per-corpus
    total_words = None
    total_chars = None
    try:
        total_words = sum(int(c.get("words", 0)) for c in corpora.values()) if corpora else None
        total_chars = sum(int(c.get("chars", 0)) for c in corpora.values()) if corpora else None
    except Exception:
        pass

    lines = []
    lines.append(f"Vector Store: {index_name}")
    if created:
        lines.append(f"Created: {created}")
    lines.append(f"Embedding model: {embedding_model}")
    if chunk_size is not None and chunk_overlap is not None:
        lines.append(f"Chunking: size {chunk_size}, overlap {chunk_overlap}")
    if db_size_mb is not None:
        lines.append(f"DB size: {_fmt_num(db_size_mb)} MB")

    totals_line = []
    if total_files is not None:
        totals_line.append(f"files {_fmt_num(total_files)}")
    if total_chunks is not None:
        totals_line.append(f"chunks {_fmt_num(total_chunks)}")
    if total_words is not None:
        totals_line.append(f"words {_fmt_num(total_words)}")
    if total_chars is not None:
        totals_line.append(f"chars {_fmt_num(total_chars)}")
    if totals_line:
        lines.append("Totals: " + ", ".join(totals_line))

    if corpora:
        # Compact one-liners for each corpus
        lines.append("")
        lines.append("Corpora:")
        try:
            sorted_items = sorted(corpora.items(), key=lambda kv: kv[1].get("chunks", 0), reverse=True)
        except Exception:
            sorted_items = list(corpora.items())
        for cid, cstats in sorted_items[:8]:
            c_files = _fmt_num(cstats.get("files")) if cstats.get("files") is not None else "?"
            c_chunks = _fmt_num(cstats.get("chunks")) if cstats.get("chunks") is not None else "?"
            summary = f"  • {cid}: files {c_files}, chunks {c_chunks}"
            lines.append(summary)
        if len(corpora) > 8:
            lines.append(f"  • (+{len(corpora) - 8} more)")

    return "\n".join(lines)


def get_manifest_document() -> Optional[Any]:
    """Return a LangChain Document containing the manifest summary, if possible."""
    # Check if manifest context is disabled via environment variable
    if os.getenv("MANIFEST_CONTEXT_ENABLED", "true").lower() in ("false", "0", "no", "off", "disabled"):
        return None
        
    data = load_manifest()
    if not data:
        return None
    summary = build_manifest_summary(data)
    # Import Document lazily to avoid import-time failures when LC is unavailable in some envs
    try:
        from langchain_core.documents.base import Document  # type: ignore
    except Exception:
        return None
    metadata = {
        "source": "manifest",
        "title": "Vector Store Manifest",
        "corpus": "meta",
        "created": data.get("created"),
        "embedding_model": data.get("embedding_model"),
    }
    return Document(page_content=summary, metadata=metadata)


def looks_like_manifest_question(question: str) -> bool:
    """Heuristic to decide if a query is about the store stats/manifest."""
    if not question:
        return False
    q = question.lower()
    keywords = [
        "vector store", "manifest", "index name", "collection name", "chroma", "bm25",
        "embedding model", "chunks", "speeches", "files", "documents", "db size", "corpora",
        "how many", "count", "total", "size of the database",
    ]
    return any(k in q for k in keywords)
