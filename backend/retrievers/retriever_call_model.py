"""
Core Retriever Module for ATLAS

This module contains the call_model function used by backend/app.py for RAG operations.
It works with the retriever implementations in this directory.
"""

import os
import re
import uuid
import logging
import datetime
from typing import Sequence, List, Dict, Any, Optional, AsyncGenerator
from typing_extensions import TypedDict
import asyncio

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.documents.base import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from centralized configuration
from backend.modules.config import get_config, get_retriever, get_retriever_instance
from backend.modules.system_prompts import system_prompt, contextualize_q_system_prompt

# Import telemetry
from backend.telemetry import (
    create_span, SpanAttributes, OpenInferenceSpanKind,
    trace_document_retrieval, trace_llm_generation, trace_document_filtering,
    trace_citation_formatting, OpenInferenceOpenInferenceSpanKind, SpanNames
)

# Get retriever instance and config
retriever = get_retriever()
retriever_instance = get_retriever_instance()
config = get_config()
retriever_config = config.get("retriever_config", {})

# Try to get LLM from retriever instance
LLM = getattr(retriever_instance, "llm", None)
if LLM is None:
    # We need an LLM from the retriever - no fallback available
    logger.error("No LLM available from retriever instance")
    raise ValueError("No LLM available from the retriever instance. The retriever must provide an LLM.")

# Extract configuration values for telemetry
EMBEDDING_MODEL = retriever_config.get("embedding_model", "unknown")
DATABASE_URL = retriever_config.get("database_url", "unknown")
SEARCH_TYPE = retriever_config.get("search_type", "similarity")
SEARCH_KWARGS = retriever_config.get("search_kwargs", {"k": 3})
INDEX_NAME = retriever_config.get("index_name", "unknown")
ALGORITHM = retriever_config.get("algorithm", "unknown")
CHUNK_SIZE = retriever_config.get("chunk_size", 1000)
CHUNK_OVERLAP = retriever_config.get("chunk_overlap", 0)

# Define a state schema
class State(TypedDict):
    input: str
    chat_history: Sequence[BaseMessage]
    context: str
    answer: str
    question: str
    session_id: str
    qa_id: str
    request_structured_citations: Optional[bool]
    corpus_filter: Optional[str]
    previous_corpus_filter: Optional[str]
    trace_context: Optional[Dict]

# Retrieve the format_document_for_citation function from the retriever implementation
format_document_for_citation = getattr(retriever_instance, "format_document_for_citation", None)
if format_document_for_citation is None:
    # Fallback implementation if not available from the retriever
    def format_document_for_citation(document: Document, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if not document:
            return None
            
        metadata = document.metadata if hasattr(document, 'metadata') else {}
        text = document.page_content if hasattr(document, 'page_content') else str(document)
        
        processed_metadata = {}
        for key, value in metadata.items():
            processed_metadata[key] = str(value) if value is not None else ""
            
        citation = {
            "text": text,
            "metadata": processed_metadata,
            "id": metadata.get("id") or (f"doc_{idx}" if idx is not None else f"doc_{uuid.uuid4()}")
        }
        
        return citation

async def call_model(
    question: str,
    chat_history: List[Dict[str, str]] = None,
    session_id: str = None,
    qa_id: str = None,
    corpus_filter: str = "all",
    request_structured_citations: bool = True
) -> AsyncGenerator[str, None]:
    """
    Call the model with proper tracing of all operations.
    """
    try:
        # Create parent span for the entire operation
        with create_span(
            SpanNames.RAG_PIPELINE,
            attributes={
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.QA_ID: qa_id,
                SpanAttributes.INPUT_VALUE: question,
                "corpus_filter": corpus_filter,
                "openinference.span.kind": OpenInferenceSpanKind.AGENT
            },
            session_id=session_id
        ) as parent_span:
            # Get test target attributes from the unified configuration
            from backend.telemetry.config_attrs import get_test_target_attributes
            test_target_attrs = get_test_target_attributes()
            # Attach the full session configuration as attributes to the root span
            for key, value in test_target_attrs.items():
                parent_span.set_attribute(key, value)

            
            # Document retrieval span
            with trace_document_retrieval(session_id=session_id, qa_id=qa_id) as retrieval_span:
                # Get relevant documents using the interface method
                retrieval_config = {"session_id": session_id, "qa_id": qa_id}
                if corpus_filter:
                    retrieval_config["corpus_filter"] = corpus_filter
                # Use get_relevant_documents for consistency with the rollback
                filtered_docs = await retriever.aget_relevant_documents(question, **retrieval_config)
                retrieval_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(filtered_docs))
            
            # Document filtering and ranking span
            with trace_document_filtering(session_id=session_id, qa_id=qa_id) as filtering_span:
                # Enhance document relevance using the standalone function
                from backend.retrievers.hansard_retriever import enhance_document_relevance
                filtered_docs = enhance_document_relevance(filtered_docs, question)
                filtering_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(filtered_docs))
            
            # Skip citation formatting here since it's handled in app.py
            # This prevents duplicate spans in the telemetry hierarchy
            # Get citations format function for reference only
            from backend.retrievers.hansard_retriever import format_citations
            # Limit documents to search_k to prevent token limit errors
            search_k = test_target_attrs.get("search_k", 15)
            context_docs = filtered_docs[:search_k] if len(filtered_docs) > search_k else filtered_docs
            logger.debug(f"Limited context from {len(filtered_docs)} to {len(context_docs)} documents (search_k={search_k})")
            
            # LLM generation span
            response_text = ""
            with trace_llm_generation(
                query=question,
                model_name=test_target_attrs.get("llm_model", "unknown"),
                session_id=session_id,
                qa_id=qa_id,
                prompt=system_prompt,
                context_document_count=len(context_docs),
                output=response_text  # Will update after response generation
            ) as llm_span:
                # Attach the full session configuration as a span attribute
                llm_span.set_attribute("session.configuration", test_target_attrs)

                # Generate the response using the LLM from the unified configuration
                from backend.targets.base_target import ModelProviders
                from backend.modules.config import get_config
                
                # Get configuration
                config = get_config()
                
                # Using context_docs already limited above
                
                # Format documents for context
                context = "\n\n".join([doc.page_content for doc in context_docs if hasattr(doc, 'page_content')])
                
                # Use the model_provider and model_name from test_target_attrs
                model_provider = test_target_attrs.get("llm_provider", "OPENAI").upper()
                model_name = test_target_attrs.get("llm_model", "gpt-4o")
                
                # Convert chat history to a string format for the prompt
                chat_history_text = ""
                if chat_history and len(chat_history) > 0:
                    # Format chat history as a conversation
                    history_entries = []
                    for entry in chat_history:
                        # Format user question and assistant answer
                        if 'question' in entry and entry['question'].strip():
                            history_entries.append(f"User: {entry['question']}")
                        if 'answer' in entry and entry['answer'].strip():
                            history_entries.append(f"Assistant: {entry['answer']}")
                    
                    if history_entries:
                        chat_history_text = "\nPrevious conversation:\n" + "\n".join(history_entries) + "\n"
                
                # Create prompt with context and chat history
                prompt = f"""Using the following context, please answer the question. Maintain continuity with any previous conversation.
                
Context:
{context}
{chat_history_text}
Question: {question}

Answer:"""
                
                # Restore LangChain abstraction with better debugging
                try:
                    # Use a single import for HumanMessage
                    from langchain_core.messages import HumanMessage
                    
                    # Use the centralized llm module instead of ModelProviders
                    from backend.modules.llm import create_llm
                    
                    try:
                        # Get the LLM instance through the unified config
                        llm = create_llm(provider=model_provider, model_name=model_name)
                        logger.debug(f"Using LangChain for {model_provider} with model: {model_name}")
                        
                        # Create the message
                        message = HumanMessage(content=prompt)
                        logger.debug(f"Created message for {model_provider}, content length: {len(prompt)}")
                        
                        # Track if any chunks were received
                        chunks_received = False
                        
                        # Use proper async iteration through the generator
                        # Add extensive logging to diagnose the issue
                        async for chunk in llm.astream_events([message], {'include_reasoning': False}):

                            # Handle the new LangChain streaming format
                            if 'event' in chunk and chunk['event'] == 'on_chat_model_stream':
                                # Check if data and message content are available
                                if 'data' in chunk and 'chunk' in chunk['data']:
                                    content = chunk['data']['chunk'].content
                                    chunks_received = True

                                    
                                    if content and content.strip():
                                        # Append to response text and yield to app.py
                                        response_text += content
                                        # Debug exactly what we're yielding

                                        yield content
                                    else:
                                        logger.debug(f"Received empty content in LangChain chunk")
                            # Support legacy format as fallback
                            elif 'chunk' in chunk:
                                content = chunk['chunk'].content
                                chunks_received = True

                                
                                if content and content.strip():
                                    # Append to response text and yield to app.py
                                    response_text += content
                                    # Debug exactly what we're yielding
                                    logger.info(f"Yielding content to app.py: '{content}'")
                                    yield content
                                else:
                                    logger.debug(f"Received empty content in legacy chunk")
                        
                        if not chunks_received:
                            logger.error("No chunks received from LLM stream - check LangChain configuration")
                            yield "Warning: No response chunks received from LLM"
                            
                        logger.info(f"Completed LangChain streaming, total response length: {len(response_text)}")
                            
                    except Exception as e:
                        # Handle any errors during LLM initialization or streaming
                        error_msg = f"Error with LLM ({model_provider}/{model_name}): {str(e)}"
                        logger.error(error_msg)
                        yield error_msg
                    
                    # Add the complete response to the span at the end
                    llm_span.set_attribute("role", "assistant")
                except Exception as e:
                    error_msg = f"Error generating LLM response: {str(e)}"
                    logger.error(error_msg)
                    llm_span.record_exception(e)
                    yield error_msg
                
            # Update parent span with final metrics
            parent_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(filtered_docs))
            # We skip setting citation count here as citations are now handled in app.py
            
    except Exception as e:
        logger.error(f"Error in call_model: {e}")
        raise
