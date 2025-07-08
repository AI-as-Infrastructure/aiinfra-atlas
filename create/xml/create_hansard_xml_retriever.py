#!/usr/bin/env python3
"""Generate an ATLAS-compatible retriever for the XML Hansard Chroma store.

The script reads the `manifest.json` that is written by
`create_hansard_xml_store.py` and outputs a retriever file into
`backend/retrievers/hansard_xml_retriever.py`.

The generated retriever:
• Loads the manifest at runtime to expose metadata schema
• Accepts a single `filters` dict for flexible where-clause filtering
• Provides helper `list_metadata_schema` & `get_filter_suggestions`
  required for a generic front-end.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
import textwrap

TEMPLATE = textwrap.dedent('''
    #!/usr/bin/env python3
    """Auto-generated Hansard XML retriever for ATLAS.

    Generated: {generated}
    Source manifest: {manifest_path}
    """

    import json
    import os
    import logging
    from typing import Dict, Any, List, Optional

    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_core.documents.base import Document
    from backend.retrievers.base_retriever import BaseRetriever

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    _MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "..", "targets", "chroma_db_xml", "manifest.json")

    class HansardXMLRetriever(BaseRetriever):
        """Retriever that works with the generic XML Hansard Chroma store."""

        def __init__(self, config: Dict[str, Any] | None = None):
            if config is None:
                config = {}
            # load manifest to get embedding model + schema
            with open(_MANIFEST_PATH, "r", encoding="utf-8") as fp:
                self._manifest = json.load(fp)

            # Fill required BaseRetriever fields into config
            config.setdefault("embedding_model", self._manifest["embedding_model"])
            config.setdefault("index_name", self._manifest["index_name"])
            super().__init__(config)

            # Vector store path – same directory as manifest
            chroma_dir = os.path.abspath(os.path.join(_MANIFEST_PATH, ".."))
            self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
            self.vector_store = Chroma(
                collection_name=self.index_name,
                embedding_function=self.embeddings,
                persist_directory=chroma_dir,
            )
            self._retriever = self.vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 10})

        # ------------------------------------------------------------------
        # BaseRetriever API
        # ------------------------------------------------------------------
        def get_retriever(self):
            return self

        def get_config(self) -> Dict[str, Any]:
            return {
                "index_name": self.index_name,
                "embedding_model": self.embedding_model,
                "supports_corpus_filtering": True,
                "fields": list(self._manifest["fields"].keys()),
            }

        @property
        def supports_corpus_filtering(self) -> bool:
            return True  # generic filtering via where dict

        def get_corpus_options(self) -> List[Dict[str, str]]:
            # Provide list of corpus IDs if such a field exists
            if "corpus" in self._manifest["fields"] and self._manifest["fields"]["corpus"].get("type") == "enum":
                return [{"value": v, "label": v} for v in self._manifest["fields"]["corpus"]["values"]]
            return []

        # ------------------------------------------------------------------
        # Extra helper methods for dynamic UIs
        # ------------------------------------------------------------------
        def list_metadata_schema(self) -> Dict[str, Any]:
            return self._manifest["fields"]

        def get_filter_suggestions(self, field: str, prefix: str = "", limit: int = 20) -> List[str]:
            try:
                res = self.vector_store._collection.get(where={field: {"$contains": prefix}}, limit=limit, include=["metadatas"])
                values = []
                for md in res["metadatas"]:
                    if field in md:
                        values.append(str(md[field]))
                return sorted(set(values))[:limit]
            except Exception:
                return []

        # ------------------------------------------------------------------
        # LangChain Retriever protocol
        # ------------------------------------------------------------------
        def _build_where(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            return filters if filters else None

        def similar_search(self, query: str, k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
            where = self._build_where(filters)
            docs = self.vector_store.similarity_search(query, k=k, filter=where)
            return [
                {
                    "id": doc.metadata.get("loc"),
                    "content": doc.page_content,
                    **doc.metadata,
                }
                for doc in docs
            ]

        # LangChain-compatible async / sync wrappers
        def invoke(self, input: str, config: Optional[Dict] = None, **kwargs):
            import asyncio
            filters = kwargs.get("filters")
            return asyncio.run(self._get_relevant_documents(input, filters=filters))

        async def ainvoke(self, input: str, config: Optional[Dict] = None, **kwargs):
            filters = kwargs.get("filters")
            return await self._get_relevant_documents(input, filters=filters)

        async def _get_relevant_documents(self, query: str, filters: Optional[Dict[str, Any]] = None, **kwargs):
            where = self._build_where(filters)
            return self.vector_store.similarity_search(query, k=kwargs.get("k", 10), filter=where)
''')

def main(manifest: Path, output: Path):
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = TEMPLATE.format(generated=generated, manifest_path=manifest.as_posix())
    output.write_text(code, encoding="utf-8")
    os.chmod(output, 0o755)
    print(f"Generated retriever: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Hansard XML retriever")
    parser.add_argument("--manifest", type=Path, default=Path("backend/targets/chroma_db_xml/manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("backend/retrievers/hansard_xml_retriever.py"))
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"Manifest not found at {args.manifest}, please build the store first.")
        sys.exit(1)

    main(args.manifest, args.output) 