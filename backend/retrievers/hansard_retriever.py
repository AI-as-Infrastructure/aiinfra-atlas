"""
Hansard Retriever Implementation for ATLAS

This module provides a specialized retriever implementation for the
Hansard corpus using the blert_2000 vector store.
"""

import os
import re
import uuid
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents.base import Document

from backend.retrievers.base_retriever import BaseRetriever
from backend.retrievers.retriever_config_utils import require_config_keys, get_with_default, ConfigError
from backend.modules.embeddings import get_embeddings_model



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define corpus options directly (removed SelfQuery prefix)
CORPUS_OPTIONS = [
    {"value": "all", "label": "All Collections"},
    {"value": "1901_au", "label": "Australia (1901)"},
    {"value": "1901_nz", "label": "New Zealand (1901)"},
    {"value": "1901_uk", "label": "United Kingdom (1901)"}
]

# Utility functions for document formatting
def format_docs(docs: List[Document]) -> List[Dict[str, Any]]:
    """Formats retrieved documents with metadata for structured output.
    
    Args:
        docs: List of Document objects from the retriever
        
    Returns:
        List of formatted document dictionaries
    """
    formatted_docs = []
    for doc in docs:
        metadata = doc.metadata
        formatted_doc = {
            "id": metadata.get("id", "unknown"),
            "content": doc.page_content,
            "date": metadata.get("date", "unknown"),
            "url": metadata.get("url", "unknown"),
            "loc": metadata.get("loc", "unknown"),
            "page": metadata.get("page", "unknown"),
        }
        formatted_docs.append(formatted_doc)
    return formatted_docs

def get_default_index_schema():
    """Get the default index schema for Redis Vector Store specific to Hansard.
    
    Returns:
        A dictionary containing the index schema configuration
    """
    return {
        "text": [
            {"name": "id"},  # Ensure ID is included
            {"name": "content"},
            {"name": "date"},
            {"name": "url"},
            {"name": "page"},
            {"name": "loc"},
            {"name": "corpus", "type": "TAG"},  # Ensure corpus is marked as TAG type
        ]
    }

def enhance_document_relevance(documents: List[Document], query: str, max_docs: int = 10) -> List[Document]:
    """Apply lightweight relevance enhancement to document ordering without changing the core retrieval.
    
    Args:
        documents: List of retrieved documents to re-score
        query: The user query string
        max_docs: Maximum documents to consider
        
    Returns:
        Re-ordered list of documents (same documents, potentially different order)
    """
    # Don't process if we have fewer documents than the limit
    if len(documents) <= max_docs or not query or len(query.strip()) < 3:
        return documents
    
    # Extract important terms from query (very basic approach)
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'of', 'on', 'in', 'to', 'for', 'with'}
    query_terms = set([term.lower() for term in re.findall(r'\b\w+\b', query) 
                     if term.lower() not in stop_words and len(term) > 2])
    
    # No important terms to match, keep original order
    if not query_terms:
        return documents
    
    # Quick re-ranking with minimal processing 
    scores = []
    for idx, doc in enumerate(documents[:max_docs]):
        # Maintain much of the original vector ranking (position importance)
        base_score = 1.0 - (idx * 0.05)  # Gradually decreasing importance by position
        
        # Simple term frequency in document
        content_lower = doc.page_content.lower()
        term_matches = sum(1 for term in query_terms if term in content_lower)        
        relevance_boost = term_matches / len(query_terms) if query_terms else 0
        
        # Combine scores with more weight on original ranking (70%) vs term matching (30%)
        final_score = (base_score * 0.7) + (relevance_boost * 0.3)
        scores.append((idx, final_score))
    
    # Sort by score and maintain original order for documents beyond max_docs
    scores.sort(key=lambda x: x[1], reverse=True)
    reordered = [documents[idx] for idx, _ in scores]
    
    # Return the reordered list plus any remaining documents
    return reordered + documents[max_docs:]

def format_citations(docs_with_weight: List[Tuple[Document, float]]) -> List[Dict[str, Any]]:
    """Format documents into a consistent citation structure with better quotes.
    
    Args:
        docs_with_weight: List of (document, weight) tuples
        
    Returns:
        List of citation dictionaries with standardized fields
    """
    citations = []
    for doc, weight in docs_with_weight:
        citation_id = f"citation_{uuid.uuid4()}"
        full_content = doc.page_content
        max_quote_length = 300
        
        # Get excerpt with improved sentence boundary detection
        quote = full_content[:max_quote_length]
        
        # Try to end at a sentence boundary for cleaner excerpts
        if len(full_content) > max_quote_length:
            # Look for the last sentence ending within our excerpt
            sentence_endings = [match.end() for match in re.finditer(r'[.!?]\s+', quote[:max_quote_length-3])]
            if sentence_endings:
                # Use the last complete sentence
                quote = full_content[:sentence_endings[-1]] + '...'
            else:
                # Fall back to word boundary if no sentence break found
                quote = quote.rsplit(' ', 1)[0] + '...'
        
        # Use the document's existing ID if available, or generate a UUID
        doc_id = doc.metadata.get('id', citation_id)
        
        # Create citation with fields in the exact order and naming the frontend expects
        citation = {
            "id": doc_id,
            "source_id": doc_id,
            "title": doc.metadata.get('title', f"Document {doc_id}"),
            "url": doc.metadata.get('url', ''),
            "date": doc.metadata.get('date', ''),
            "page": doc.metadata.get('page', ''),
            "corpus": doc.metadata.get('corpus', ''),
            "text": quote.strip(),  # The excerpt for display
            "content": full_content,  # Full content for viewing
            "quote": quote.strip(),  # For backward compatibility
            "full_content": full_content,  # For backward compatibility
            "weight": float(weight),
            "has_more": len(full_content) > max_quote_length
        }
        citations.append(citation)
    return citations

def format_document_for_citation(document: Document, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Format a document as a citation for the frontend.
    
    Args:
        document: Document object to format
        idx: Optional index for the document
        
    Returns:
        Formatted citation dictionary or None if document is invalid
    """
    if not document:
        return None
        
    # Process metadata dictionary
    metadata = document.metadata if hasattr(document, 'metadata') else {}
    
    # Get text content
    text = document.page_content if hasattr(document, 'page_content') else str(document)
    
    # Create a preview text (first 300 chars)
    preview_text = text[:300] + ("..." if len(text) > 300 else "")
    
    # Generate a unique ID if not present
    doc_id = metadata.get("id") or (f"doc_{idx}" if idx is not None else f"doc_{uuid.uuid4()}")
    
    # Extract URL from metadata, ensuring it's not None or empty string
    url = metadata.get("url", "")
    if url is None:
        url = ""
    elif isinstance(url, str) and url.lower() == "none":
        url = ""
    
    # Check if URL is embedded in the content
    if not url and isinstance(text, str):
        # Look for URL pattern in the text
        url_match = re.search(r'<url>(https?://[^<]+)</url>', text)
        if url_match:
            url = url_match.group(1)
    
    # Ensure we have the full content
    full_content = text
    
    # Clean up the content by removing URL tags if present
    if isinstance(full_content, str):
        full_content = re.sub(r'<url>.*?</url>', '', full_content)
        
        # Add a note about truncation if the content is near the 1000 character limit
        # This is because the vector store truncates documents to 1000 characters during ingestion
        if len(full_content) >= 990:
            full_content += "\n\n[Note: Citation content may be partial due to vector store chunking strategy. Please refer to the source URL for complete text.]"
    
    # Create citation object with all fields expected by the frontend
    citation = {
        "id": doc_id,
        "text": preview_text,
        "quote": preview_text,  # Frontend uses either text or quote
        "title": metadata.get("title", ""),
        "url": url,  # Use the processed URL value
        "date": metadata.get("date", ""),
        "page": metadata.get("page", ""),
        "corpus": metadata.get("corpus", ""),
        "loc": metadata.get("loc", ""),
        "source": metadata.get("title", ""),  # Frontend uses source for display
        "source_id": doc_id,
        "content": full_content,
        "full_content": full_content,  # Frontend uses this for modal display
        "page_content": full_content,  # Add this for compatibility
        "weight": 1.0
    }
    
    return citation

class HansardRetriever(BaseRetriever):
    """Hansard-specific retriever implementation for ATLAS."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Hansard retriever.
        
        Args:
            config: Configuration dictionary (optional)
        """
        if config is None:
            config = {}
        
        config["CORPUS_OPTIONS"] = CORPUS_OPTIONS

        # Initialize the base class first
        super().__init__(config)

        # Extract Hansard-specific configuration
        try:
            required_keys = [
                "target_id", "target_version", "search_type", "search_k", "search_score_threshold", "citation_limit",
                "algorithm", "chunk_size", "chunk_overlap", "embedding_model", "large_retrieval_size"
            ]
            params = require_config_keys(config, required_keys)
            self.target_id = params["target_id"]
            self.composite_target = get_with_default(config, "composite_target", False)
            self.target_version = params["target_version"]
            self.search_type = params["search_type"]
            self.search_kwargs = {
                "k": params["search_k"],
                "score_threshold": params["search_score_threshold"],
                "citation_limit": params["citation_limit"]
            }

            self.algorithm = params["algorithm"]
            self.chunk_size = params["chunk_size"]
            self.chunk_overlap = params["chunk_overlap"]
            self.embedding_model = params["embedding_model"]
            self.large_retrieval_size = params["large_retrieval_size"]
            self._supports_corpus_filtering = get_with_default(config, "supports_corpus_filtering", True)
        except ConfigError as e:
            logger.error(f"Missing required HansardRetriever config key: {e}")
            raise ValueError(f"Missing required HansardRetriever config key: {e}")
        
        # Log initialization 
        logger.info(f"Initializing HansardRetriever with target_id: {self.target_id}")
        
        # Get Chroma directory from environment with better error handling
        self.chroma_persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY")
        if not self.chroma_persist_directory:
            logger.error("CHROMA_PERSIST_DIRECTORY environment variable is not set")
            raise ValueError("CHROMA_PERSIST_DIRECTORY environment variable is not set")
        # Ensure the directory exists
        os.makedirs(self.chroma_persist_directory, exist_ok=True)
        self.chroma_collection_name = os.getenv("CHROMA_COLLECTION_NAME", self.index_name)
        logger.info(f"Using Chroma with collection '{self.chroma_collection_name}' at '{self.chroma_persist_directory}'")
              
        # Load target configuration for search parameters
        self._load_target_config()
        
        # Initialize LLM for question answering
        try:
            # Get the target ID from environment
            target_id = os.getenv('TEST_TARGET', 'default')
            logger.info(f"Initializing LLM based on TEST_TARGET: {target_id}")
            
            # Load target configuration based on TEST_TARGET
            target_config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'targets', f"{target_id}.txt")
            
            # Default configuration values
            llm_provider = None 
            llm_model = None
            
            # Try to read the configuration file
            if os.path.isfile(target_config_file):
                logger.info(f"Loading target configuration from: {target_config_file}")
                try:
                    with open(target_config_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = [x.strip() for x in line.split('=', 1)]
                                if key == "LLM_PROVIDER":
                                    llm_provider = value.strip('"').strip("'")
                                elif key == "LLM_MODEL":
                                    llm_model = value.strip('"').strip("'")
                except Exception as e:
                    logger.error(f"Error reading target configuration file: {e}")
            else:
                logger.warning(f"Target configuration file not found: {target_config_file}")
                logger.warning("No configuration provided - system will fail as required")
            
            # Import the LLM module instead of ModelProviders
            from backend.modules.llm import create_llm
            
            # Create LLM using the centralized create_llm function
            if not llm_provider:
                logger.error("No LLM provider specified in configuration")
                raise ValueError("LLM provider must be specified in target configuration")
            self.llm = create_llm(
                provider=llm_provider,
                model_name=llm_model
            )
            logger.info(f"Successfully initialized {llm_provider} LLM with model: {llm_model or 'default'}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise ValueError(f"Failed to initialize LLM: {e}")
        
        # Initialize the vector store
        logger.info("Initializing vector store...")
        try:
            # Add retry mechanism for Redis loading state
            max_retries = 20
            retry_delay = 30  # seconds
            last_exception = None
            for attempt in range(max_retries):
                try:
                    self._initialize_vector_store()
                    logger.info("Vector store initialized successfully")
                    break
                except Exception as e:
                    last_exception = e
                    if "Redis is loading the dataset in memory" in str(e):
                        retry_seconds = retry_delay * (attempt + 1)
                        logger.warning(f"Redis is still loading data. Retrying in {retry_seconds} seconds... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(retry_seconds)
                    else:
                        raise
            else:
                logger.error(f"Failed to initialize vector store after {max_retries} attempts: {last_exception}")
                raise ValueError(f"Failed to initialize vector store after {max_retries} attempts: {last_exception}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise ValueError(f"Failed to initialize vector store: {e}")

        # Instantiate a simple HNSW fetch-k retriever (no SelfQueryRetriever)
        self._retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.large_retrieval_size}
        )
        
        # Attach citation formatting methods to the instance
        self.format_document_for_citation = format_document_for_citation
        self.format_citations = format_citations
        self.enhance_document_relevance = enhance_document_relevance

    def get_retriever(self):
        """Get the base retriever instance."""
        return self._retriever
        
    def retrieve(self, query, corpus_filter=None):
        """Retrieve documents based on a query and optional corpus filter.
        
        Args:
            query: The query string to search for
            corpus_filter: Optional corpus name to filter results
            
        Returns:
            List of retrieved documents
        """
        # Get corpus values from environment
        corpus_metadata = os.getenv('MULTI_CORPUS_METADATA', '')
        # Strip quotes if present and split by comma
        corpus_metadata = corpus_metadata.strip('"').strip("'")
        corpus_values = [cv.strip() for cv in corpus_metadata.split(',') if cv.strip()]
        
        if not corpus_values:
            # Fallback only if environment variable is not set or empty
            logger.warning("MULTI_CORPUS_METADATA not set in environment, using defaults")
            corpus_values = ["1901_au", "1901_nz", "1901_uk"]
        
        # If no corpus filter or 'all', get documents from each corpus separately
        if not corpus_filter or corpus_filter.lower() == "all":
            logger.info("No specific corpus filter - retrieving balanced results from all corpora")
            
            # Get 200 documents from each corpus
            all_documents = []
            for corpus in corpus_values:
                try:
                    # Use direct similarity_search with filter parameter for each corpus
                    corpus_docs = self.vector_store.similarity_search(
                        query,
                        k=int(os.getenv('LARGE_RETRIEVAL_SIZE_ALL_CORPUS', 200)),  # configurable per corpus
                        filter={"corpus": corpus}  # Direct metadata filtering
                    )
                    
                    # No need to extract docs as similarity_search already returns documents list
                    logger.info(f"Retrieved {len(corpus_docs)} documents from {corpus} corpus")
                    all_documents.extend(corpus_docs)
                except Exception as e:
                    logger.error(f"Error retrieving documents for {corpus}: {e}")
            
            # Sort all documents by relevance (using enhance_document_relevance)
            all_documents = self.enhance_document_relevance(all_documents, query)
            logger.info(f"Retrieved total of {len(all_documents)} documents from all corpora")
            return all_documents
        else:
            # Specific corpus filter - get 500 documents from just that corpus
            # Ensure corpus_filter is a properly formatted string
            corpus_filter_str = str(corpus_filter).strip()
            logger.info(f"Retrieving documents for specific corpus filter: {corpus_filter_str}")
            
            try:
                # Use direct similarity_search with filter parameter for corpus filtering
                documents = self.vector_store.similarity_search(
                    query,
                    k=int(os.getenv('LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS', getattr(self, 'large_retrieval_size', 500))),  # configurable for single corpus
                    filter={"corpus": corpus_filter_str}  # Direct metadata filtering
                )
                
                # Apply document enhancement to improve relevance
                enhanced_docs = self.enhance_document_relevance(documents, query)
                
                return enhanced_docs
            except Exception as e:
                logger.error(f"Error retrieving documents with corpus filter {corpus_filter_str}: {e}")
                # Return empty list on error
                return []
    
    def _load_target_config(self):
        # All search parameters and metadata must come from config or target config file
        if not hasattr(self, 'search_type') or not hasattr(self, 'search_kwargs'):
            raise ValueError("search_type and search_kwargs must be set by config or target config file")
        if not hasattr(self, 'target_version'):
            raise ValueError("target_version must be set by config or target config file")
        if not hasattr(self, 'large_retrieval_size'):
            raise ValueError("large_retrieval_size must be set by config or target config file")
        if not hasattr(self, 'composite_target'):
            raise ValueError("composite_target must be set by config or target config file")
        # Try to load from target config file if it exists
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_config_file = os.path.join(backend_dir, 'targets', f"{self.target_id}.txt")
        
        if os.path.isfile(target_config_file):
            logger.info(f"Loading target config from: {target_config_file}")
            try:
                with open(target_config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = [x.strip() for x in line.split('=', 1)]
                            value = value.strip('"').strip("'")
                            
                            # Set specific parameters
                            if key == "SEARCH_TYPE":
                                self.search_type = value
                            elif key == "SEARCH_K":
                                self.search_kwargs["k"] = int(value)
                            elif key == "SEARCH_SCORE_THRESHOLD":
                                self.search_kwargs["score_threshold"] = float(value)
                            elif key == "CITATION_LIMIT":
                                self.search_kwargs["citation_limit"] = int(value)
                            elif key == "TARGET_VERSION":
                                self.target_version = value
                            elif key == "LARGE_RETRIEVAL_SIZE":
                                self.large_retrieval_size = int(value)
                
                logger.info(f"Loaded target configuration from {target_config_file}")
            except Exception as e:
                logger.error(f"Error reading target config: {e}")
    
    # _get_index_schema is no longer needed with langchain-redis >=0.2.0
    
    def _initialize_vector_store(self):
        """Initialize the Chroma vector store."""
        # Create the embedding model using the centralized function
        self.embeddings = get_embeddings_model(
            model_name=self.embedding_model,
            config={"embedding_model": self.embedding_model}
        )
        
        # Create the vector store with proper metadata handling
        self.vector_store = Chroma(
            collection_name=self.chroma_collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.chroma_persist_directory
        )
        
        # Log collection info to help with debugging
        try:
            collection = self.vector_store._collection
            count = collection.count()
            logger.info(f"Connected to Chroma collection with {count} documents")
            
            # Test metadata filtering to verify it works
            corpus_values = ["1901_au", "1901_nz", "1901_uk"]
            for corpus in corpus_values:
                try:
                    # Use similarity_search with the embeddings function already configured
                    # instead of using collection.query directly
                    results = self.vector_store.similarity_search(
                        "test", 
                        k=1,
                        filter={"corpus": corpus}
                    )
                    if results and len(results) > 0:
                        logger.info(f"Metadata filtering confirmed working for corpus: {corpus}")
                except Exception as e:
                    logger.warning(f"Could not verify metadata filtering for corpus '{corpus}': {e}")
        except Exception as e:
            logger.warning(f"Could not get collection details: {e}")
        
        # Standard retriever search kwargs (without large_retrieval_size)
        standard_search_kwargs = {k: v for k, v in self.search_kwargs.items() 
                               if k not in ["citation_limit"]}
        
        # Always use similarity search for consistent corpus filtering
        self.search_type = "similarity"
        
        # Remove any parameters specific to other search types
        if "fetch_k" in standard_search_kwargs:
            del standard_search_kwargs["fetch_k"]
            
        if "lambda_mult" in standard_search_kwargs:
            del standard_search_kwargs["lambda_mult"]
        
        # Create the standard retriever (without large_retrieval_size)
        # Extract parameters from search_kwargs and pass them directly
        k = standard_search_kwargs.get("k", 3)
        score_threshold = standard_search_kwargs.get("score_threshold", None)
        fetch_k = standard_search_kwargs.get("fetch_k", None)
        lambda_mult = standard_search_kwargs.get("lambda_mult", None)
        
        # Pass parameters directly instead of using search_kwargs
        self._retriever = self.vector_store.as_retriever(
            search_type=self.search_type,
            k=k,
            score_threshold=score_threshold,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult
        )

    def get_retriever(self):
        """Return the actual retriever implementation.
        
        Returns:
            The internal retriever object that can be used for document retrieval
        """
        return self._retriever

    def similar_search(self, query: str, k: int = 10, corpus_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Perform a similarity search on the vector store with optional corpus filtering.
        
        Args:
            query: The query string to search for
            k: Number of results to return
            corpus_filter: Optional corpus name to filter results
            
        Returns:
            List of citation dictionaries ready for frontend display
        """
        # Create filter dict if corpus filter is provided
        filter_dict = None
        if corpus_filter and corpus_filter.lower() != "all":
            filter_dict = {"corpus": corpus_filter}
        
        # Log the search request
        filter_msg = f" with corpus filter '{corpus_filter}'" if corpus_filter else ""
        logger.info(f"Similar search for: '{query}'{filter_msg} (using similarity search)")
        
        try:
            # Always use similarity search for consistent corpus filtering
            docs = self.vector_store.similarity_search(
                query,
                k=k,
                filter=filter_dict
            )
            
            # Format documents as citations
            citations = []
            for idx, doc in enumerate(docs):
                citation = format_document_for_citation(doc, idx)
                if citation:
                    citations.append(citation)
            
            logger.info(f"Found {len(citations)} results for query: '{query}'")
            return citations
            
        except Exception as e:
            logger.error(f"Error in similar_search: {e}")
            return []
    
    def batch_retrieve_documents(self, ids, batch_size=100):
        """Retrieve documents in batches using Redis pipelining for efficiency.
        
        Args:
            ids: List of document IDs to retrieve
            batch_size: Number of documents to retrieve in each batch
            
        Returns:
            List of Document objects
        """
        import redis
        from langchain_core.documents.base import Document
        
        # Get Redis connection from vector store or create a new one
        redis_client = None
        try:
            # Try to access the Redis client from vector_store
            redis_client = self.vector_store.client
        except AttributeError:
            # If not accessible directly, create a new connection
            redis_client = redis.Redis.from_url(self.redis_url)
        
        if not redis_client:
            logger.error("Failed to get Redis client")
            return []
        
        all_docs = []
        total_batches = (len(ids) + batch_size - 1) // batch_size
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{total_batches}")
            
            # Create pipeline for efficient batch retrieval
            pipeline = redis_client.pipeline()
            for doc_id in batch_ids:
                doc_key = f"doc:{self.index_name}:{doc_id}"
                pipeline.hgetall(doc_key)
            
            # Execute pipeline (single network round trip)
            results = pipeline.execute()
            
            # Process results to Document objects
            for result in results:
                if not result:
                    continue
                    
                # Convert bytes to string in Redis result
                metadata = {}
                content = None
                for key, value in result.items():
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                    
                    if key_str == 'content':
                        content = value_str
                    else:
                        metadata[key_str] = value_str
                
                if content:
                    all_docs.append(Document(page_content=content, metadata=metadata))
        
        logger.info(f"Retrieved {len(all_docs)} documents in {total_batches} batches")
        return all_docs
    
    @property
    def prompt_used(self):
        return getattr(self._retriever, 'prompt_used', None)

    @property
    def metadata_fields_used(self):
        return getattr(self._retriever, 'metadata_fields_used', None)

    def get_config(self) -> Dict[str, Any]:
        """Return the complete configuration of this retriever."""
        return {
            # Target metadata
            "target_id": self.target_id,
            "composite_target": self.composite_target,
            "target_version": self.target_version,
            
            # Search configuration
            "search_type": self.search_type,
            "search_k": self.search_kwargs["k"],
            "search_score_threshold": self.search_kwargs["score_threshold"],
            "citation_limit": self.search_kwargs["citation_limit"],
            
            # Chroma configuration
            "vector_database": "chroma",
            "chroma_persist_directory": self.chroma_persist_directory,
            "chroma_collection": self.chroma_collection_name,
    
            "algorithm": self.algorithm,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "large_retrieval_size": self.large_retrieval_size,
            
            # Feature flags
            "supports_corpus_filtering": self._supports_corpus_filtering,
        }
    
    @property
    def supports_corpus_filtering(self) -> bool:
        """Whether this retriever supports filtering by corpus."""
        return self._supports_corpus_filtering
    
    def get_corpus_options(self) -> List[Dict[str, str]]:
        """Get available corpus options for filtering specific to Hansard."""
        # Use corpus options defined above
        return CORPUS_OPTIONS

    async def _get_relevant_documents(self, query: str, *, run_manager=None, config=None, **kwargs) -> List[Document]:
        """Get relevant documents for a query."""
        try:
            # Extract corpus_filter from config if present
            corpus_filter = None
            if config and isinstance(config, dict) and "corpus_filter" in config:
                corpus_filter = config["corpus_filter"]
                logger.info(f"Retrieving documents with corpus filter: '{corpus_filter}'")
            
            # Check if we need to reset the filter state
            if config and isinstance(config, dict) and config.get("reset_filter_state", False):
                logger.info(f"Resetting filter state for corpus: {corpus_filter}")
                # Force a reset by recreating the vector store connection
                self.vector_store = Chroma(
                    collection_name=self.chroma_collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=self.chroma_persist_directory
                )
                
                # Critical: Also recreate the retriever to ensure it uses the fresh vector store
                self._retriever = self.vector_store.as_retriever(
                    search_type=self.search_type,
                    search_kwargs={
                        "k": self.large_retrieval_size
                    }
                )
            
            # Use the retrieve method with the corpus filter
            documents = self.retrieve(query, corpus_filter=corpus_filter)
            
            # Log basic retrieval stats
            logger.info(f"Retrieved {len(documents)} documents for query")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error in _get_relevant_documents: {e}")
            raise