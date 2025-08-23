from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/vector-store-info")
async def get_vector_store_info(raw: bool = False):
    try:
        # Serve pretty-printed manifest.json or a concise human-readable summary
        current_dir = os.path.dirname(os.path.abspath(__file__))
        manifest_path = os.path.join(current_dir, "targets", "manifest.json")

        if not os.path.exists(manifest_path):
            raise HTTPException(status_code=404, detail="Vector store manifest.json not found in backend/targets")

        try:
            import json as _json
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = _json.load(f)
        except Exception:
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
            return {"content": raw_text}

        if raw:
            return {"content": _json.dumps(data, indent=2)}

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
            try:
                sorted_items = sorted(corpora.items(), key=lambda kv: kv[1].get("chunks", 0), reverse=True)
            except Exception:
                sorted_items = list(corpora.items())
            lines.append("")
            lines.append("Corpora:")
            for i, (cid, cstats) in enumerate(sorted_items[:8]):
                c_files = _fmt_num(cstats.get("files")) if cstats.get("files") is not None else "?"
                c_chunks = _fmt_num(cstats.get("chunks")) if cstats.get("chunks") is not None else "?"
                summary = f"  • {cid}: files {c_files}, chunks {c_chunks}"
                lines.append(summary)
            if len(corpora) > 8:
                lines.append(f"  • (+{len(corpora) - 8} more)")

        if fields:
            enum_fields = [k for k, v in fields.items() if isinstance(v, dict) and v.get("type") == "enum"]
            lines.append("")
            lines.append(f"Metadata fields: {len(fields)}" + (f" (enums: {', '.join(enum_fields)})" if enum_fields else ""))

        return {"content": "\n".join(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))