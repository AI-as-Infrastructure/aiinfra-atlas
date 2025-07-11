#!/usr/bin/env python3
"""
ATLAS-Compatible Retriever Generator for HNSW Hansard Vector Store

This script generates a retriever class that is fully compatible with the ATLAS system,
aligned with backend/retrievers/hansard_retriever.py, for a vector store created by hansard_blert_HNSW_store.py.

It reads a manifest file describing the vector store configuration, then auto-generates a Python retriever
class that connects to the Redis vector database, loads the correct embedding model, and exposes methods
for semantic search and document retrieval. The generated retriever can be used directly in the ATLAS backend
or as a standalone script for querying the Hansard vector store.
"""
import os
import re
import sys
from pathlib import Path
import argparse
from datetime import datetime
# Ensure project root is on sys.path so `import backend` works no matter where
# this script is executed from (Makefile may invoke it from a sub-shell).
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from typing import Dict, List, Any, Optional, Tuple
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents.base import Document
from backend.retrievers.base_retriever import BaseRetriever

def parse_manifest_file(manifest_path):
    config = {}
    try:
        with open(manifest_path, 'r') as f:
            content = f.read()
            # Extract key parameters from stats file format
            index_name = re.search(r'Collection:\s*(.+)', content)
            embedding_model = re.search(r'Model:\s*(.+)', content)
            chunk_size = re.search(r'Chunk Size:\s*(\d+)', content)
            chunk_overlap = re.search(r'Chunk Overlap:\s*(\d+)', content)
            created = re.search(r'Created:\s*(.+)', content)
            
            if index_name: config['INDEX_NAME'] = index_name.group(1).strip()
            if embedding_model: config['EMBEDDING_MODEL'] = embedding_model.group(1).strip()
            if chunk_size: config['CHUNK_SIZE'] = chunk_size.group(1).strip()
            if chunk_overlap: config['CHUNK_OVERLAP'] = chunk_overlap.group(1).strip()
            if created: config['CREATED'] = created.group(1).strip()
            
            # Default algorithm for Chroma
            config['ALGORITHM'] = 'HNSW'
            
    except Exception as e:
        print(f"Error parsing manifest: {e}")
        sys.exit(1)
    req = ['INDEX_NAME','EMBEDDING_MODEL','CHUNK_SIZE','CHUNK_OVERLAP']
    for k in req:
        if k not in config:
            print(f"Missing {k} in manifest!")
            sys.exit(1)
    return config

def generate_atlas_retriever(config, output_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template = '''#!/usr/bin/env python3
"""
Auto-generated ATLAS Retriever for {INDEX_NAME} (HNSW)
Generated: {now}
Manifest creation: {CREATED}
"""
import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents.base import Document
from backend.retrievers.base_retriever import BaseRetriever

# Configure logging
logger = logging.getLogger(__name__)

# Define corpus options directly (removed SelfQuery prefix)
CORPUS_OPTIONS = [
    {{"value": "all", "label": "All Collections"}},
    {{"value": "1901_au", "label": "Australia (1901)"}},
    {{"value": "1901_nz", "label": "New Zealand (1901)"}},
    {{"value": "1901_uk", "label": "United Kingdom (1901)"}}
]


class HansardRetriever(BaseRetriever):
    """Hansard-specific retriever implementation for ATLAS."""
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {{}}
        
        config["CORPUS_OPTIONS"] = CORPUS_OPTIONS
        super().__init__(config)
        self.index_name = "{INDEX_NAME}"
        self.chunk_size = int("{CHUNK_SIZE}")
        self.chunk_overlap = int("{CHUNK_OVERLAP}")
        self.embedding_model = "{EMBEDDING_MODEL}"
        self._supports_corpus_filtering = True

        # Location of the persisted Chroma DB
        self.persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./create/txt/output/chroma_db")
        
        # Initialize LLM instance (required by retriever_call_model.py)
        self._initialize_llm()
        self._initialize_vector_store()

    def _initialize_llm(self):
        \"\"\"Initialize the LLM instance required by the system.\"\"\"
        from backend.modules.llm import create_llm
        self.llm = create_llm()
    
    def _initialize_vector_store(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        self.vector_store = Chroma(
            collection_name=self.index_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )
        self._retriever = self.vector_store.as_retriever(search_type="similarity", search_kwargs={{\"k\": 10}})

    def get_retriever(self):
        return self._retriever

    def get_config(self) -> Dict[str, Any]:
        return {{
            "index_name": self.index_name,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "persist_directory": self.persist_directory,
            "supports_corpus_filtering": self._supports_corpus_filtering,
            "algorithm": "HNSW",
            "search_type": "similarity",
            "search_kwargs": {{"k": 10}}
        }}

    @property
    def supports_corpus_filtering(self) -> bool:
        return self._supports_corpus_filtering

    def get_corpus_options(self) -> List[Dict[str, str]]:
        return CORPUS_OPTIONS

    def similar_search(self, query: str, k: int = 10, corpus_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info(f"similar_search: k={{k}}, corpus_filter={{corpus_filter}}")
        filter_dict = None
        if corpus_filter and corpus_filter != "all":
            filter_dict = {{"corpus": corpus_filter}}
        
        # Use standard similarity search
        docs = self.vector_store.similarity_search(query=query, k=k, filter=filter_dict)
        return [{{
            "id": doc.metadata.get("id", "unknown"),
            "content": doc.page_content,
            "date": doc.metadata.get("date", "unknown"),
            "url": doc.metadata.get("url", "unknown"),
            "loc": doc.metadata.get("loc", "unknown"),
            "page": doc.metadata.get("page", "unknown"),
            "corpus": doc.metadata.get("corpus", "unknown")
        }} for doc in docs]
    
    # LangChain-compatible async implementation
    async def _get_relevant_documents(self, query: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Internal implementation method called by invoke/ainvoke"""
        k = kwargs.get("k", 10)
        corpus_filter = None
        
        # Extract corpus filter from config if present
        if config and isinstance(config, dict):
            corpus_filter = config.get("corpus_filter")
        
        filter_dict = None
        if corpus_filter and corpus_filter != "all":
            filter_dict = {{"corpus": corpus_filter}}
        
        # Use standard similarity search
        return self.vector_store.similarity_search(query=query, k=k, filter=filter_dict)
    
    # Public API methods required by LangChain
    def invoke(self, input: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Synchronous invoke method required by LangChain."""
        import asyncio
        return asyncio.run(self._get_relevant_documents(input, config, **kwargs))
    
    async def ainvoke(self, input: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Asynchronous invoke method required by LangChain."""
        return await self._get_relevant_documents(input, config, **kwargs)
    
    def format_document_for_citation(self, document: Document, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
        \"\"\"Instance method version for compatibility with retriever_call_model.py.\"\"\"
        return format_document_for_citation(document, idx)

# Compatibility helper for citation formatting (imported by streaming.py)
def format_document_for_citation(document: Document, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Convert a Document into the citation structure expected by the frontend."""
    if not document:
        return None

    meta = getattr(document, 'metadata', {{}}) or {{}}
    text = getattr(document, 'page_content', str(document))

    preview = text[:300] + ("..." if len(text) > 300 else "")
    doc_id = meta.get("id") or (f"doc_{{idx}}" if idx is not None else "unknown")

    return {{
        "id": doc_id,
        "source_id": doc_id,
        "title": meta.get("title", f"Document {{doc_id}}"),
        "url": meta.get("url", ""),
        "date": meta.get("date", ""),
        "page": meta.get("page", ""),
        "corpus": meta.get("corpus", ""),
        "text": preview,
        "quote": preview,
        "content": text,
        "full_content": text,
        "loc": meta.get("loc", ""),
        "weight": 1.0,
        "has_more": len(text) > 300,
    }}

# Required functions for compatibility with retriever_call_model.py
def enhance_document_relevance(documents: List[Document], query: str) -> List[Document]:
    \"\"\"Enhance document relevance using the centralized reranking module.\"\"\"
    from backend.modules.document_reranking import enhance_document_relevance as _enhance
    return _enhance(documents, query, create_span=False)

def format_citations(documents: List[Document], **kwargs) -> List[Dict[str, Any]]:
    \"\"\"Format documents as citations for the frontend.\"\"\"
    return [format_document_for_citation(doc, i) for i, doc in enumerate(documents)]
'''
    cfg = config.copy()
    cfg['now'] = now
    with open(output_path, 'w') as f:
        f.write(template.format(**cfg))
    os.chmod(output_path, 0o755)
    print(f"Generated ATLAS retriever: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate an ATLAS-compatible Hansard HNSW Retriever script')
    parser.add_argument('--manifest', required=False, help='Path to the vector store manifest file (.txt)')
    parser.add_argument('--output', required=False, help='Path for the output retriever script (.py)')
    args = parser.parse_args()
    if not args.manifest:
        # Default to the script's own output/ directory rather than CWD
        script_dir = Path(__file__).resolve().parent
        default_manifest_dir = script_dir / 'output'
        if os.path.exists(default_manifest_dir):
            txt_files = [f for f in os.listdir(default_manifest_dir) if f.endswith('.txt')]
            if txt_files:
                args.manifest = str(Path(default_manifest_dir) / txt_files[0])
                print(f"Using manifest file: {args.manifest}")
            else:
                print("No .txt manifest files found in ./output/")
                sys.exit(1)
        else:
            print("No manifest file specified and ./output/ directory not found")
            sys.exit(1)
    if not os.path.exists(args.manifest):
        print(f"Manifest file not found: {args.manifest}")
        sys.exit(1)
    config = parse_manifest_file(args.manifest)
    # Always output to ./output directory, regardless of manifest location
    output_dir = str(script_dir / 'output')
    os.makedirs(output_dir, exist_ok=True)
    index_name = config['INDEX_NAME']
    output_path = os.path.join(output_dir, "hansard_retriever.py")
    generate_atlas_retriever(config, output_path)
    print(f"\nRetriever script generation complete!\nLocation: {output_path}\nYou can use it in ATLAS backend or run it standalone.")

if __name__ == "__main__":
    main()
