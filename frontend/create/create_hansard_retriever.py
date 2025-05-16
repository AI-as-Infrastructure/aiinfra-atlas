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
import argparse
from datetime import datetime
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
            # Extract key parameters
            index_name = re.search(r'INDEX_NAME\s*=\s*"(.+?)"', content)
            embedding_model = re.search(r'EMBEDDING_MODEL\s*=\s*"(.+?)"', content)
            algorithm = re.search(r'ALGORITHM\s*=\s*"(.+?)"', content)
            chunk_size = re.search(r'CHUNK_SIZE\s*=\s*(\d+)', content)
            chunk_overlap = re.search(r'CHUNK_OVERLAP\s*=\s*(\d+)', content)
            created = re.search(r'Created:\s*(.+)', content)
            if index_name: config['INDEX_NAME'] = index_name.group(1)
            if embedding_model: config['EMBEDDING_MODEL'] = embedding_model.group(1)
            if algorithm: config['ALGORITHM'] = algorithm.group(1)
            if chunk_size: config['CHUNK_SIZE'] = chunk_size.group(1)
            if chunk_overlap: config['CHUNK_OVERLAP'] = chunk_overlap.group(1)
            if created: config['CREATED'] = created.group(1)
    except Exception as e:
        print(f"Error parsing manifest: {e}")
        sys.exit(1)
    req = ['INDEX_NAME','EMBEDDING_MODEL','ALGORITHM','CHUNK_SIZE','CHUNK_OVERLAP']
    for k in req:
        if k not in config:
            print(f"Missing {k} in manifest!")
            sys.exit(1)
    return config

def generate_atlas_retriever(config, output_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = f'''#!/usr/bin/env python3
"""
Auto-generated ATLAS Retriever for {config['INDEX_NAME']} (HNSW)
Generated: {now}
Manifest creation: {config.get('CREATED','Unknown')}
"""
import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents.base import Document
from backend.retrievers.base_retriever import BaseRetriever

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
        self.redis_database = "{config['INDEX_NAME']}"
        self.index_name = "{config['INDEX_NAME']}"
        self.algorithm = "{config['ALGORITHM']}"
        self.chunk_size = "{config['CHUNK_SIZE']}"
        self.chunk_overlap = "{config['CHUNK_OVERLAP']}"
        self.embedding_model = "{config['EMBEDDING_MODEL']}"
        self._supports_corpus_filtering = True
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = os.getenv("REDIS_PORT", "6379")
        if self.redis_password:
            self.redis_url = f"redis://default:{{self.redis_password}}@{{self.redis_host}}:{{self.redis_port}}"
        else:
            self.redis_url = f"redis://{{self.redis_host}}:{{self.redis_port}}"
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        self.vector_store = Redis(
            redis_url=self.redis_url,
            index_name=self.index_name,
            embedding=self.embeddings,
            vector_schema={{"algorithm": self.algorithm}},
            index_schema=get_default_index_schema(),
        )
        self._retriever = self.vector_store.as_retriever(search_type="similarity", search_kwargs={{"k": 10}})

    def get_retriever(self):
        return self._retriever

    def get_config(self) -> Dict[str, Any]:
        return {{
            "redis_database": self.redis_database,
            "index_name": self.index_name,
            "algorithm": self.algorithm,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "supports_corpus_filtering": self._supports_corpus_filtering,
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
'''
    with open(output_path, 'w') as f:
        f.write(code)
    os.chmod(output_path, 0o755)
    print(f"Generated ATLAS retriever: {output_path}")
def main():
    parser = argparse.ArgumentParser(description='Generate an ATLAS-compatible Hansard HNSW Retriever script')
    parser.add_argument('--manifest', required=False, help='Path to the vector store manifest file (.txt)')
    parser.add_argument('--output', required=False, help='Path for the output retriever script (.py)')
    args = parser.parse_args()
    if not args.manifest:
        default_manifest_dir = './output/'
        if os.path.exists(default_manifest_dir):
            txt_files = [f for f in os.listdir(default_manifest_dir) if f.endswith('.txt')]
            if txt_files:
                args.manifest = os.path.join(default_manifest_dir, txt_files[0])
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
    output_dir = os.path.abspath('./output')
    os.makedirs(output_dir, exist_ok=True)
    index_name = config['INDEX_NAME']
    output_path = os.path.join(output_dir, f"{index_name}_retriever.py")
    generate_atlas_retriever(config, output_path)
    print(f"\nRetriever script generation complete!\nLocation: {output_path}\nYou can use it in ATLAS backend or run it standalone.")

if __name__ == "__main__":
    main()
