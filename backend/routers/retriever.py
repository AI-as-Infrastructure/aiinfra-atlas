"""
Retriever API endpoints for ATLAS.

Handles retriever filter capabilities and vector store information.
"""

import os
import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.modules.config import get_retriever_instance

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/retriever/filters")
def get_retriever_filters():
    """Return available filter capabilities for the current retriever."""
    try:
        retriever = get_retriever_instance()

        # Check if retriever supports the new filter capabilities interface
        if hasattr(retriever, 'get_filter_capabilities'):
            filter_capabilities = retriever.get_filter_capabilities()
        else:
            # Fallback for retrievers that haven't implemented the new interface yet
            filter_capabilities = {
                "corpus_filtering": {
                    "supported": retriever.supports_corpus_filtering if hasattr(retriever, 'supports_corpus_filtering') else False,
                    "options": retriever.get_corpus_options() if hasattr(retriever, 'get_corpus_options') else []
                },
                "time_period_filtering": {
                    "supported": False,
                    "options": []
                },
                "direction_filtering": {
                    "supported": False,
                    "options": []
                }
            }

        return JSONResponse(content=filter_capabilities)

    except Exception as e:
        logger.error(f"Error getting filter capabilities: {e}")
        # Return minimal fallback response
        return JSONResponse(content={
            "corpus_filtering": {
                "supported": False,
                "options": []
            },
            "time_period_filtering": {
                "supported": False,
                "options": []
            },
            "direction_filtering": {
                "supported": False,
                "options": []
            }
        })


@router.get("/api/vector-store-info")
async def get_vector_store_info(raw: bool = False):
    """Return vector store manifest information."""
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifest_path = os.path.join(current_dir, "targets", "manifest.json")

        if not os.path.exists(manifest_path):
            raise HTTPException(status_code=404, detail="Vector store manifest.json not found in backend/targets")

        # Load manifest JSON
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
            return {"content": raw_text}

        # If raw requested, pretty-print JSON
        if raw:
            return {"content": json.dumps(data, indent=2)}

        # Otherwise, render a concise, human-readable overview
        def _fmt_num(n):
            try:
                return f"{int(n):,}"
            except Exception:
                try:
                    return f"{float(n):,.2f}"
                except Exception:
                    return str(n)

        index_name = data.get("index_name", "(unknown)")
        embedding_model = data.get("embedding_model", "(unknown)")
        created = data.get("created")
        chunk_size = data.get("chunk_size")
        chunk_overlap = data.get("chunk_overlap")
        fields = data.get("fields", {}) or {}
        stats = data.get("stats", {}) or {}
        corpora = (stats.get("corpora") or {}) if isinstance(stats, dict) else {}
        total_chunks = stats.get("total_chunks")
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

        # Compose lines
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

        # Per-corpus breakdown (limit to top 8 by chunks)
        if corpora:
            try:
                sorted_items = sorted(corpora.items(), key=lambda kv: kv[1].get("chunks", 0), reverse=True)
            except Exception:
                sorted_items = list(corpora.items())
            lines.append("")
            lines.append("Corpora:")
            for i, (cid, cstats) in enumerate(sorted_items[:8]):
                c_files = _fmt_num(cstats.get("files")) if cstats.get("files") is not None else "?"
                c_chunks = _fmt_num(cstats.get("chunks")) if cstats.get("chunks") is not None else "?"
                c_words = _fmt_num(cstats.get("words")) if cstats.get("words") is not None else None
                summary = f"  - {cid}: files {c_files}, chunks {c_chunks}"
                if c_words is not None:
                    summary += f", words {c_words}"
                lines.append(summary)
            if len(corpora) > 8:
                lines.append(f"  - (+{len(corpora) - 8} more)")

        # Metadata fields summary
        if fields:
            enum_fields = [k for k, v in fields.items() if isinstance(v, dict) and v.get("type") == "enum"]
            lines.append("")
            lines.append(f"Metadata fields: {len(fields)}" + (f" (enums: {', '.join(enum_fields)})" if enum_fields else ""))

        return {"content": "\n".join(lines)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vector store info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
