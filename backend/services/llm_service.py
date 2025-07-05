"""
LLM Service for Async Processing

This module provides async wrappers around the existing LLM processing
functionality to enable background processing of queries.
"""

import asyncio
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path
import uuid

# Add project root to path if needed
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the actual processing functions from the modules
try:
    from backend.modules.document_retrieval import retrieve_documents_with_telemetry
    from backend.modules.corpus_filtering import filter_documents_with_telemetry
    from backend.modules.document_reranking import rerank_documents_with_telemetry
    from backend.modules.llm import generate_response_with_telemetry
    from backend.modules.config import get_retriever
    from backend.modules.sensitive_contexts import detect_sensitive_contexts
    print("✅ Successfully imported LLM processing modules")
except ImportError as e:
    print(f"⚠️ Could not import LLM processing functions: {e}")
    print("Please ensure your LLM processing code is available")

# Thread pool for running sync LLM operations
import os
LLM_WORKERS = int(os.getenv("LLM_THREAD_POOL_WORKERS", "2"))
llm_executor = ThreadPoolExecutor(max_workers=LLM_WORKERS, thread_name_prefix="llm-worker")

def process_query_sync(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an LLM query synchronously using the same logic as the main app
    
    This function replicates the processing logic from the /api/ask endpoint
    """
    try:
        # Extract query parameters
        question = query_data.get("query", "")
        corpus_filter = query_data.get("corpus_selection", "all")
        model_selection = query_data.get("model_selection", "claude-3-5-sonnet-20241022")
        chat_history = query_data.get("chat_history", [])
        session_id = str(uuid.uuid4())  # Generate session ID for async processing
        qa_id = str(uuid.uuid4())       # Generate QA ID for async processing
        
        if not question:
            return {
                "type": "error",
                "error": "No question provided",
                "query_data": query_data
            }
        
        print(f"🔄 Processing query: {question[:50]}...")
        
        # Guardrail check: Detect sensitive contexts
        sensitive_contexts = detect_sensitive_contexts(
            query=question,
            session_id=session_id,
            qa_id=qa_id
        )
        
        # Log if any sensitive contexts were detected (for future use)
        if sensitive_contexts:
            print(f"⚠️ Detected sensitive contexts: {sensitive_contexts}")
            # In the future, this could trigger special handling or warnings
        
        # Step 1: Retrieve documents
        documents, qa_id = retrieve_documents_with_telemetry(
            query=question,
            retriever=get_retriever(),
            session_id=session_id,
            qa_id=qa_id,
            corpus_filter=corpus_filter
        )
        
        if not documents:
            return {
                "type": "error",
                "error": "No relevant documents found for your query",
                "query": question
            }
        
        print(f"📄 Retrieved {len(documents)} documents")
        
        # Step 2: Apply corpus filter
        documents = filter_documents_with_telemetry(
            documents=documents,
            corpus_filter=corpus_filter,
            session_id=session_id,
            qa_id=qa_id
        )
        
        # Step 3: Apply document reranking
        documents = rerank_documents_with_telemetry(
            documents=documents,
            query=question,
            session_id=session_id,
            qa_id=qa_id
        )
        
        print(f"🔍 Filtered and reranked to {len(documents)} documents")
        
        # Step 4: Generate response
        response_generator, qa_id = generate_response_with_telemetry(
            question=question,
            documents=documents,
            session_id=session_id,
            qa_id=qa_id,
            chat_history=chat_history,
            corpus_filter=corpus_filter,
            provider=model_selection  # Use model_selection as provider
        )
        
        # Step 5: Collect the entire response
        response_text = ""
        chunk_count = 0
        for chunk in response_generator:
            response_text += chunk
            chunk_count += 1
        
        print(f"✅ Generated response with {chunk_count} chunks, {len(response_text)} characters")
        
        return {
            "type": "ask_response",
            "result": response_text,
            "query": question,
            "corpus_selection": corpus_filter,
            "model_selection": model_selection,
            "document_count": len(documents),
            "session_id": session_id,
            "qa_id": qa_id
        }
        
    except Exception as e:
        print(f"❌ Error in sync processing: {e}")
        import traceback
        traceback.print_exc()
        return {
            "type": "error",
            "error": str(e),
            "query_data": query_data
        }

async def process_query_async(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an LLM query asynchronously
    
    This function wraps the synchronous LLM processing
    to run in a thread pool, making it non-blocking.
    """
    try:
        # Run the synchronous LLM processing in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            llm_executor,
            process_query_sync,
            query_data
        )
        
        return result
            
    except Exception as e:
        print(f"❌ Error processing LLM query: {e}")
        return {
            "type": "error",
            "error": str(e),
            "query_data": query_data
        }

async def process_simple_query_async(query: str, corpus: str = "all", model: str = "claude-3-5-sonnet-20241022") -> Dict[str, Any]:
    """
    Simplified async query processor for basic queries
    """
    query_data = {
        "query": query,
        "corpus_selection": corpus,
        "model_selection": model
    }
    
    return await process_query_async(query_data)

# Health check function for the LLM service
async def health_check() -> Dict[str, Any]:
    """Check if the LLM service is healthy"""
    try:
        # Simple test query
        test_result = await process_simple_query_async(
            "Hello, this is a test query.", 
            corpus="all", 
            model="claude-3-5-sonnet-20241022"
        )
        
        return {
            "status": "healthy",
            "test_query_successful": test_result.get("type") != "error",
            "executor_active": not llm_executor._shutdown
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def shutdown_llm_service():
    """Gracefully shutdown the LLM service"""
    print("🔄 Shutting down LLM service...")
    llm_executor.shutdown(wait=True)
    print("✅ LLM service shutdown complete") 