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

        # If no retriever is configured yet (e.g., before corpus is built),
        # return the same format the frontend expects (matching base_retriever schema)
        if retriever is None:
            logger.info("No retriever configured yet - returning empty filter capabilities")
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

        filter_capabilities = retriever.get_filter_capabilities()
        return JSONResponse(content=filter_capabilities)

    except Exception as e:
        logger.error(f"Error getting filter capabilities: {e}")
        raise HTTPException(status_code=500, detail="Failed to get filter capabilities")


@router.get("/api/vector-store-info")
async def get_vector_store_info(raw: bool = False):
    """Return vector store manifest information."""
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Check canonical corpus manifest first, then fall back to targets copy
        manifest_path = os.path.join(current_dir, "corpus", "manifest.json")
        if not os.path.exists(manifest_path):
            manifest_path = os.path.join(current_dir, "targets", "manifest.json")

        if not os.path.exists(manifest_path):
            raise HTTPException(status_code=404, detail="No manifest.json found. Please build a corpus using the wizard.")

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

        # Support both legacy flat manifest (v1.1) and nested wizard manifest (v1.2+)
        em = data.get("embedding_model", "(unknown)")
        if isinstance(em, dict):
            # v1.2+ nested format
            index_name = data.get("corpus_name") or data.get("metadata", {}).get("display_name", "(unknown)")
            embedding_model = em.get("id", "(unknown)")
            chunk_size = data.get("embeddings", {}).get("chunk_size")
            chunk_overlap = data.get("embeddings", {}).get("chunk_overlap")
            stats = data.get("statistics", {}) or {}
        else:
            # v1.1 legacy flat format
            index_name = data.get("index_name", "(unknown)")
            embedding_model = em
            chunk_size = data.get("chunk_size")
            chunk_overlap = data.get("chunk_overlap")
            stats = data.get("stats", {}) or {}

        created = data.get("created")
        fields = data.get("fields", {}) or {}
        corpora = (stats.get("corpora") or {}) if isinstance(stats, dict) else {}
        total_chunks = stats.get("total_chunks")
        total_files = stats.get("total_files")
        db_size_mb = stats.get("db_size_mb")

        # v1.2+ stores per-filter stats; derive total_documents from statistics
        total_documents = stats.get("total_documents")

        # v1.2+ filters can serve as corpus breakdown
        if not corpora:
            filters_data = data.get("filters", {})
            filter_stats = stats.get("filters", {})
            if filters_data and isinstance(filters_data, dict):
                for fkey, finfo in filters_data.items():
                    if isinstance(finfo, dict):
                        fid = finfo.get("id", fkey)
                        fstat = filter_stats.get(fid, {}) if filter_stats else {}
                        corpora[finfo.get("label", fid)] = {
                            "files": fstat.get("processed"),
                            "chunks": None
                        }

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
        if total_documents is not None:
            totals_line.append(f"documents {_fmt_num(total_documents)}")
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

        # Build environment section (v1.4+)
        build = data.get("build")
        if build and isinstance(build, dict):
            lines.append("")
            lines.append("Build Environment:")
            mode = build.get("mode")
            if mode:
                lines.append(f"  Mode: {mode.upper()}")
            duration = build.get("duration_seconds")
            if duration is not None:
                mins = int(duration // 60)
                secs = int(duration % 60)
                lines.append(f"  Duration: {mins}m {secs}s" if mins else f"  Duration: {secs}s")
            gpu_used = build.get("gpu_used")
            gpu_name = build.get("gpu_name")
            gpu_mem = build.get("gpu_memory_gb")
            if gpu_used and gpu_name:
                gpu_str = f"  GPU: {gpu_name}"
                if gpu_mem:
                    gpu_str += f" ({gpu_mem} GB)"
                lines.append(gpu_str)
            elif gpu_used is False:
                lines.append("  GPU: Not used")
            cpu_cores = build.get("cpu_cores")
            ram = build.get("system_ram_gb")
            if cpu_cores or ram:
                hw_parts = []
                if cpu_cores:
                    hw_parts.append(f"{cpu_cores} cores")
                if ram:
                    hw_parts.append(f"{ram} GB RAM")
                lines.append(f"  Hardware: {', '.join(hw_parts)}")
            platform_str = build.get("platform")
            machine = build.get("machine")
            if platform_str or machine:
                parts = [p for p in [platform_str, machine] if p]
                lines.append(f"  Platform: {', '.join(parts)}")
            py_ver = build.get("python_version")
            pt_ver = build.get("pytorch_version")
            cuda_ver = build.get("cuda_version")
            if py_ver or pt_ver:
                sw_parts = []
                if py_ver:
                    sw_parts.append(f"Python {py_ver}")
                if pt_ver:
                    sw_parts.append(f"PyTorch {pt_ver}")
                if cuda_ver:
                    sw_parts.append(f"CUDA {cuda_ver}")
                lines.append(f"  Software: {', '.join(sw_parts)}")

        return {"content": "\n".join(lines)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vector store info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
