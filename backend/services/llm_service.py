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

# Add project root to path if needed
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import your existing LLM processing functions
# Note: Adjust these imports based on your actual LLM processing code
try:
    from backend.api.ask import process_ask_request
    from backend.api.models import AskRequest
except ImportError as e:
    print(f"⚠️ Could not import LLM processing functions: {e}")
    print("Please ensure your LLM processing code is available")

# Thread pool for running sync LLM operations
llm_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="llm-worker")

async def process_query_async(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an LLM query asynchronously
    
    This function wraps your existing synchronous LLM processing
    to run in a thread pool, making it non-blocking.
    """
    try:
        # Convert query_data to the format expected by your LLM processor
        # Adjust this based on your actual data models
        
        if "query" in query_data:
            # Handle ask-style queries
            ask_request = AskRequest(
                query=query_data["query"],
                corpus_selection=query_data.get("corpus_selection", "all"),
                model_selection=query_data.get("model_selection", "claude-3-5-sonnet-20241022"),
                user_id=query_data.get("user_id")
            )
            
            # Run the synchronous LLM processing in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                llm_executor,
                process_ask_request,
                ask_request
            )
            
            return {
                "type": "ask_response",
                "result": result,
                "query": query_data["query"],
                "corpus_selection": ask_request.corpus_selection,
                "model_selection": ask_request.model_selection
            }
        
        else:
            # Handle other query types or return error
            return {
                "type": "error",
                "error": "Unsupported query type",
                "query_data": query_data
            }
            
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