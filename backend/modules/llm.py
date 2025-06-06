"""
LLM utilities for ATLAS.

This module provides functions for interacting with Language Models,
with built-in telemetry instrumentation.
"""

import logging
import time
import json
import os
import uuid
from typing import List, Dict, Any, Optional, Generator, Union, Callable, Tuple
from datetime import datetime

from langchain_core.documents.base import Document
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.language_models.chat_models import BaseChatModel

from backend.telemetry import create_span, SpanAttributes, SpanNames, OpenInferenceSpanKind, set_span_outputs
from opentelemetry.trace import SpanKind
from opentelemetry.trace import SpanKind, Status, StatusCode
from backend.modules.config import get_system_prompt, get_llm_config
from backend.modules.system_prompts import get_qa_prompt_template, system_prompt

logger = logging.getLogger(__name__)

def format_documents(documents: List[Document]) -> str:
    """
    Format documents as a string for inclusion in prompts.
    
    Args:
        documents: List of documents
        
    Returns:
        Formatted string representation of documents
    """
    formatted_docs = []
    for i, doc in enumerate(documents):
        # Extract metadata
        metadata = doc.metadata.copy() if hasattr(doc, 'metadata') else {}
        
        # Format metadata fields
        metadata_str = ", ".join(f"{k}: {v}" for k, v in metadata.items() 
                               if k in ["date", "title", "source", "corpus", "page"])
        
        # Extract text content
        text = doc.page_content if hasattr(doc, 'page_content') else str(doc)
        
        # Format document
        formatted_docs.append(f"Document {i+1} [{metadata_str}]:\n{text}\n")
        
    return "\n".join(formatted_docs)

def format_chat_history(chat_history: List[Dict[str, str]]) -> List[Union[HumanMessage, AIMessage]]:
    """
    Format chat history as LangChain messages.
    
    Converts chat history from the application format to the format expected by LangChain.
    Works with all supported LLM providers (OpenAI, Anthropic, Ollama).
    
    Args:
        chat_history: List of chat history entries with 'role' and 'content' keys
        
    Returns:
        List of LangChain message objects
    """
    if not chat_history:
        return []
        
    messages = []
    for entry in chat_history:
        # Handle different formats of chat history
        if isinstance(entry, dict):
            role = entry.get("role", "")
            content = entry.get("content", "")
            
            # Map chat history roles to message types
            if role.lower() == "user" or role.lower() == "human":
                messages.append(HumanMessage(content=content))
            elif role.lower() == "assistant" or role.lower() == "ai":
                messages.append(AIMessage(content=content))
            elif role.lower() == "system":
                messages.append(SystemMessage(content=content))
        elif isinstance(entry, (HumanMessage, AIMessage, SystemMessage)):
            # If already a LangChain message, use it directly
            messages.append(entry)
            
    return messages

def create_llm(
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = True
) -> BaseChatModel:
    """
    Create an LLM instance for any supported provider.
    
    This function is the centralized implementation for creating LLM instances
    in the ATLAS system, supporting OpenAI, Anthropic, and Ollama providers.
    
    Args:
        model_name: Name of the model
        provider: LLM provider (openai, anthropic, ollama)
        temperature: Temperature for generation
        streaming: Whether to use streaming mode
        
    Returns:
        LLM instance of the appropriate type
    """
    # Get LLM configuration
    llm_config = get_llm_config()
    
    # Use provided values or fall back to config
    model = model_name or llm_config.get("model") or "gpt-4o-mini"
    provider = provider or llm_config.get("provider") or "openai"
    
    # Normalize provider name to uppercase
    provider = provider.upper()
    
    # Create LLM based on provider
    if provider == 'OLLAMA':
        ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
        logger.debug(f"Using Ollama endpoint: {ollama_endpoint}")
        return ChatOllama(
            model=model or "llama3.2",
            base_url=ollama_endpoint,
            temperature=temperature,
            streaming=streaming
        )
    elif provider == 'ANTHROPIC':
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            logger.error("ANTHROPIC_API_KEY not found in environment - check environment variable loading")
            raise ValueError("ANTHROPIC_API_KEY not found. Please set the environment variable.")
            
        logger.debug("Using Anthropic with API key")
        return ChatAnthropic(
            api_key=anthropic_api_key,
            model_name=model or "claude-3-5-sonnet-20240620",
            temperature=temperature,
            streaming=streaming
        )
    elif provider == 'OPENAI':
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment - check environment variable loading")
            raise ValueError("OPENAI_API_KEY not found. Please set the environment variable.")
            
        logger.debug("Using OpenAI with API key")
        return ChatOpenAI(
            api_key=openai_api_key,
            model=model or "gpt-4o",
            temperature=temperature,
            streaming=streaming
        )
    else:
        logger.warning(f"Unknown provider '{provider}', falling back to OpenAI")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found. Please set the environment variable.")
            
        return ChatOpenAI(
            api_key=openai_api_key,
            model=model or "gpt-4o",
            temperature=temperature,
            streaming=streaming
        )

def create_qa_prompt(
    system_prompt: Optional[str] = None,
    include_chat_history: bool = True
) -> PromptTemplate:
    """
    Create a prompt template for Q&A.
    
    Args:
        system_prompt: System prompt (overrides default if provided)
        include_chat_history: Whether to include chat history
        
    Returns:
        Prompt template
    """
    # If a custom system prompt is provided, create a template with it
    if system_prompt:
        # Create a template with the custom system prompt
        if include_chat_history:
            template = f"""
{system_prompt}

Context information is below.
{{context}}

Previous conversation:
{{chat_history}}

User question: {{question}}

Answer:"""
            
            return PromptTemplate(
                template=template,
                input_variables=["context", "chat_history", "question"]
            )
        else:
            template = f"""
{system_prompt}

Context information is below.
{{context}}

User question: {{question}}

Answer:"""
            
            return PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )
    else:
        # Use the standard template from system_prompts.py
        return get_qa_prompt_template(include_chat_history)

def generate_response(
    question: str,
    documents: List[Document],
    chat_history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    span: Optional[Any] = None,
    provider: Optional[str] = None,
    create_llm_span: bool = True
) -> Generator[str, None, None]:
    """
    Generate a response using an LLM with the provided documents as context.
    
    Args:
        question: User question
        documents: Retrieved documents
        chat_history: Optional chat history
        system_prompt: Optional system prompt
        temperature: LLM temperature
        span: Optional parent span
        provider: Optional LLM provider override
        create_llm_span: Whether to create an LLM generation span (set to False to prevent redundant spans)
        
    Yields:
        Response chunks
    """
    try:
        # Skip creating a span if not needed (to prevent redundant spans)
        if not create_llm_span:
            # Format documents for context
            context = format_documents(documents)
            
            # Create LLM with the specified provider (or from config)
            llm = create_llm(temperature=temperature, provider=provider)
            
            # Format chat history (ensure it's not None)
            chat_history_list = chat_history or []
            formatted_history = format_chat_history(chat_history_list)
            chat_history_str = "\n".join([f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}" 
                                       for msg in formatted_history])
            
            # Create the prompt template using the standard approach
            prompt = create_qa_prompt(system_prompt, bool(chat_history_list))
            
            # Prepare input data
            input_data = {
                "context": context,
                "question": question
            }
            
            # Add chat history if available
            if chat_history_list:
                input_data["chat_history"] = chat_history_str
            
            # Create the chain using proper LangChain constructs
            chain = prompt | llm
            
            # Format the prompt
            formatted_prompt = prompt.format(**input_data)
            
            # Generate response
            full_response = ""
            
            try:
                # Process the streaming response
                for chunk in llm.stream(formatted_prompt):
                    # Extract content from chunk based on provider and format
                    content = None
                    
                    # Handle different chunk formats
                    if hasattr(chunk, 'content'):
                        # Standard LangChain format
                        content = chunk.content
                    elif isinstance(chunk, dict):
                        # Dictionary format (e.g., from events stream)
                        if 'content' in chunk:
                            content = chunk['content']
                        elif 'delta' in chunk and 'content' in chunk['delta']:
                            content = chunk['delta']['content']
                        elif 'chunk' in chunk and hasattr(chunk['chunk'], 'content'):
                            content = chunk['chunk'].content
                    
                    # Skip if no content
                    if not content:
                        continue
                    
                    # Detect and handle placeholder text if somehow still present
                    placeholder_pattern = "{answer}"
                    if placeholder_pattern in content:
                        logger.warning(f"Detected placeholder '{placeholder_pattern}' in content")
                        content = content.replace(placeholder_pattern, 
                            "I need more specific information to answer this question based on the provided context.")
                    
                    # Update tracking variables
                    full_response += content
                    
                    # Yield the content
                    yield content
                
            except Exception as e:
                logger.error(f"Error during streaming: {e}")
                if not full_response:
                    full_response = f"Error generating response: {str(e)}"
                    yield full_response
                
            return
        
        # Create span for telemetry using trace_operation which properly handles span kind
        from backend.telemetry.spans import trace_operation
        
        with trace_operation(
            SpanNames.LLM_GENERATION,
            attributes={
                # Essential input information
                SpanAttributes.INPUT_VALUE: question,
                SpanAttributes.DOCUMENT_COUNT: len(documents),
                
                # Input characteristics
                "has_chat_history": bool(chat_history),
                "temperature": temperature,
            },
            session_id=session_id,
            qa_id=qa_id,
            openinference_kind=OpenInferenceSpanKind.LLM,
            input_data=question
        ) as llm_span:
            try:
                start_time = time.time()
                
                # Format documents for context
                context = format_documents(documents)
                llm_span.set_attribute("context_length", len(context))
                
                # Create LLM with the specified provider (or from config)
                llm = create_llm(temperature=temperature, provider=provider)
                model_name = getattr(llm, "model_name", str(llm))
                llm_span.set_attribute("model", model_name)
                
                # Format chat history (ensure it's not None)
                chat_history_list = chat_history or []
                formatted_history = format_chat_history(chat_history_list)
                chat_history_str = "\n".join([f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}" 
                                           for msg in formatted_history])
                
                llm_span.set_attribute("chat_history_turns", len(formatted_history))
                
                # Create the prompt template using the standard approach
                prompt = create_qa_prompt(system_prompt, bool(chat_history_list))
                
                # Log the prompt for debugging
                logger.debug(f"Created prompt template with system_prompt: {system_prompt[:50] if system_prompt else 'default'}... and {len(formatted_history)} chat history turns")
                
                # Prepare input data
                input_data = {
                    "context": context,
                    "question": question
                }
                
                # Add chat history if available
                if chat_history_list:
                    input_data["chat_history"] = chat_history_str
                
                # Create the chain using proper LangChain constructs
                chain = prompt | llm

                # Stream response
                full_response = ""
                chunk_count = 0
                
                # Generate response
                logger.debug(f"Starting stream with {llm.__class__.__name__}")
                
                try:
                    # Check the formatted prompt
                    formatted_prompt = prompt.format(**input_data)
                    prompt_length = len(formatted_prompt)
                    llm_span.set_attribute("prompt_length", prompt_length)
                    
                    # Set initial state using direct span attributes
                    summary = f"Generating response with {model_name}"
                    llm_span.set_attribute("summary", summary)
                    llm_span.set_attribute("model", model_name)
                    llm_span.set_attribute("temperature", temperature)
                    llm_span.set_attribute("prompt_length", prompt_length)
                    llm_span.set_attribute("context_length", len(context))
                    llm_span.set_attribute("chat_history_turns", len(formatted_history))
                    llm_span.set_attribute("document_count", len(documents))
                    llm_span.set_attribute("status", "generating")
                    
                    # Process the streaming response from the LLM
                    for chunk in llm.stream(formatted_prompt):
                        # Update chunk count for telemetry
                        chunk_count += 1
                        
                        # Extract content from chunk
                        content = None
                        
                        # Handle different chunk formats from different providers
                        if hasattr(chunk, 'content'):
                            # Standard LangChain format
                            content = chunk.content
                        elif isinstance(chunk, dict):
                            # Dictionary format (e.g., from events stream)
                            if 'content' in chunk:
                                content = chunk['content']
                            elif 'delta' in chunk and 'content' in chunk['delta']:
                                content = chunk['delta']['content']
                            elif 'chunk' in chunk and hasattr(chunk['chunk'], 'content'):
                                content = chunk['chunk'].content
                        
                        # Skip if no content extracted
                        if not content:
                            continue
                            
                        # Detect and handle placeholder text if somehow still present
                        placeholder_pattern = "{answer}"
                        if placeholder_pattern in content:
                            logger.warning(f"Detected placeholder '{placeholder_pattern}' in content")
                            content = content.replace(placeholder_pattern, 
                                "I need more specific information to answer this question based on the provided context.")
                        
                        # Update tracking variables
                        full_response += content
                        
                        # Track chunk information
                        if chunk_count % 10 == 0:  # Update only periodically to avoid excessive spans
                            llm_span.set_attribute("chunk_count", chunk_count)
                            llm_span.set_attribute("response_length", len(full_response))
                        
                        # Yield content to the caller
                        yield content
                    
                    # Calculate generation time
                    generation_time = time.time() - start_time
                    
                    # Set final response information using direct span attributes
                    final_summary = f"Generated response ({len(full_response)} chars) with {model_name}"
                    llm_span.set_attribute("final_summary", final_summary)
                    llm_span.set_attribute("generation_time_seconds", generation_time)
                    llm_span.set_attribute("final_chunk_count", chunk_count)
                    llm_span.set_attribute("final_response_length", len(full_response))
                    
                    # Add a truncated output preview for review
                    if full_response:
                        preview_length = min(500, len(full_response))
                        preview = full_response[:preview_length] + ("..." if len(full_response) > preview_length else "")
                        llm_span.set_attribute("response_preview", preview)
                    
                except Exception as e:
                    # Handle streaming errors
                    logger.error(f"Error during streaming: {e}", exc_info=True)
                    
                    # Set error information using direct span attributes
                    error_summary = f"Error generating response: {str(e)}"
                    llm_span.set_attribute("final_summary", error_summary)
                    llm_span.set_attribute("generation_error", str(e))
                    llm_span.set_attribute("generation_complete", False)
                    llm_span.set_attribute("generation_time_seconds", generation_time)
                    llm_span.set_attribute("final_chunk_count", chunk_count)
                    llm_span.set_attribute("final_response_length", len(full_response))
                    
                    # Add a truncated output preview for review
                    if full_response:
                        preview_length = min(500, len(full_response))
                        preview = full_response[:preview_length] + ("..." if len(full_response) > preview_length else "")
                        llm_span.set_attribute("response_preview", preview)
                    
                # Yield the final response
                yield full_response
                
            except Exception as e:
                # Handle any other errors
                logger.error(f"Error in LLM processing: {e}", exc_info=True)
                
                # Set error information using direct span attributes
                error_summary = f"Error in LLM processing: {str(e)}"
                llm_span.set_attribute("final_summary", error_summary)
                llm_span.set_attribute("generation_error", str(e))
                llm_span.set_attribute("generation_complete", False)
                llm_span.set_attribute("generation_time_seconds", generation_time)
                llm_span.set_attribute("final_chunk_count", chunk_count)
                llm_span.set_attribute("final_response_length", len(full_response))
                
                # Add a truncated output preview for review
                if full_response:
                    preview_length = min(500, len(full_response))
                    preview = full_response[:preview_length] + ("..." if len(full_response) > preview_length else "")
                    llm_span.set_attribute("response_preview", preview)
                
                # Yield the final response
                yield full_response
                
    except Exception as e:
        # Handle any exceptions outside of span context
        logger.error(f"Error creating LLM span: {e}", exc_info=True)
        
        # Yield error message
        error_msg = f"Error generating response: {str(e)}"
        yield error_msg

def generate_response_with_telemetry(
    question: str,
    documents: List[Document],
    session_id: Optional[str] = None,
    qa_id: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    corpus_filter: Optional[str] = None,
    provider: Optional[str] = None
) -> Tuple[Generator[str, None, None], str]:
    """
    Generate a response with telemetry instrumentation.
    
    This function creates an LLM span directly linked to the parent pipeline span
    and tracks various metrics during generation.
    
    Args:
        question: User question
        documents: Retrieved documents
        session_id: Session ID for telemetry
        qa_id: QA ID for telemetry
        chat_history: Optional chat history
        corpus_filter: Optional corpus filter
        provider: Optional LLM provider override
        
    Returns:
        Tuple of (response generator, QA ID)
    """
    # Get LLM configuration if not explicitly provided
    if not provider:
        llm_config = get_llm_config()
        provider = llm_config.get("provider")
    
    start_time = datetime.now()
    
    try:
        # Generate QA ID if not provided
        if not qa_id:
            qa_id = str(uuid.uuid4())
            
        logger.info(f"Starting LLM generation with qa_id={qa_id}, session_id={session_id}")
        
        # Create telemetry span directly linked to the parent pipeline span
        with create_span(
            SpanNames.LLM_GENERATION,
            attributes={
                # Session and question identifiers
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.QA_ID: qa_id,
                
                # Input information
                "input.value": question,
                "input.documents_count": len(documents),
                "input.chat_history_turns": len(chat_history) if chat_history else 0,
                "input.has_chat_history": bool(chat_history),
                
                # Detailed operation information
                "description": f"Generating answer to: {question[:100]}{'...' if len(question) > 100 else ''}",
                "operation": "llm_generation",
                "question_text": question[:500],  # Truncate if very long
                
                # Span classification - use explicit kind string for Phoenix UI
                "kind": "LLM",  # Direct kind attribute
                "span.kind": "LLM",  # Alternative format
                
                # Standard openinference format with flat attributes (compatible with OpenTelemetry)
                "openinference.span.kind": OpenInferenceSpanKind.LLM,
                
                # Model information
                "llm.provider": provider,
                "llm.description": "Generates text response based on retrieved documents and user query",
                
                # Context information
                "corpus_filter": corpus_filter or "all",
                SpanAttributes.DOCUMENT_COUNT: len(documents)
            },
            kind=SpanKind.INTERNAL
        ) as llm_span:
            try:
                # Register the main LLM span - critical for feedback association
                from backend.telemetry.spans import register_span
                span_id = str(llm_span.get_span_context().span_id)
                register_span(session_id, qa_id, span_id)
                logger.info(f"Registered main LLM span with session_id={session_id}, qa_id={qa_id}, span_id={span_id}")
                
                # Generate response directly without creating an additional nested LLM span
                # by passing create_llm_span=False to avoid redundancy
                response_gen = generate_response(
                    question=question,
                    documents=documents,
                    chat_history=chat_history,
                    system_prompt=get_system_prompt(),
                    temperature=0.7,
                    provider=provider,
                    span=llm_span,
                    create_llm_span=False  # Prevent creating redundant nested span
                )
                
                # Define generator to track results
                def telemetry_wrapped_generator():
                    full_response = ""
                    chunk_count = 0
                    generation_start_time = datetime.now()
                    
                    try:
                        # Stream response from the generator
                        for chunk in response_gen:
                            # Update tracking variables
                            full_response += chunk
                            chunk_count += 1
                            
                            # Periodically update span with progress
                            if chunk_count % 5 == 0:
                                llm_span.set_attribute("chunk_count", chunk_count)
                                llm_span.set_attribute("response_length", len(full_response))
                            
                            # Yield the content
                            yield chunk
                            
                        # Record final metrics
                        generation_time = (datetime.now() - generation_start_time).total_seconds()
                        llm_span.set_attribute("final_chunk_count", chunk_count)
                        llm_span.set_attribute("final_response_length", len(full_response))
                        llm_span.set_attribute("generation_time_seconds", generation_time)
                        llm_span.set_attribute("generation_complete", True)
                        
                        # Update summary information on parent span
                        summary = f"Generated {len(full_response.split())} words in {generation_time:.2f} seconds"
                        llm_span.set_attribute("generation_summary", summary)
                        
                        # Add summary of first few sentences for quick reference
                        sentences = full_response.split('. ')
                        preview = '. '.join(sentences[:3]) + ('...' if len(sentences) > 3 else '')
                        llm_span.set_attribute("response_preview", preview)
                        
                        # Set all output attributes directly on the LLM span for Phoenix UI
                        # Primary content field - most important for Phoenix display
                        llm_span.set_attribute("content", full_response)
                        
                        # Set using the output method if available
                        if hasattr(llm_span, "set_output"):
                            llm_span.set_output(full_response)
                        
                        # Also set standard output attributes for maximum compatibility
                        llm_span.set_attribute("output", full_response)
                        llm_span.set_attribute("output.value", full_response)
                        llm_span.set_attribute(SpanAttributes.OUTPUT, full_response)
                        llm_span.set_attribute("openinference.llm.output", full_response)
                        llm_span.set_attribute("llm.output", full_response)
                        
                        # Create a specific response output span for feedback association
                        response_span_name = f"{SpanNames.LLM_GENERATION}.response"
                        logger.info(f"Creating response span {response_span_name} for qa_id={qa_id}")
                        
                        with create_span(
                            response_span_name,
                            attributes={
                                # Critical metadata for identification
                                SpanAttributes.SESSION_ID: session_id,
                                SpanAttributes.QA_ID: qa_id,
                                
                                # Response content - use standard output.value attribute
                                "output.value": full_response,
                                
                                # Metadata with flat names (no info. prefix)
                                "response_length": len(full_response),
                                "word_count": len(full_response.split()),
                                "generation_time_seconds": generation_time,
                                "description": "LLM Response Output",
                                
                                # Span categorization
                                "kind": "LLM",
                                "span.kind": "LLM",
                                "openinference.span.kind": OpenInferenceSpanKind.LLM,
                            }
                        ) as output_span:
                            # Register the output span with a predictable key for feedback association
                            # This is the key pattern that log_user_feedback will look for
                            response_key = f"{qa_id}_response"
                            response_span_id = str(output_span.get_span_context().span_id)
                            register_span(session_id, response_key, response_span_id)
                            logger.info(f"Registered response span with session_id={session_id}, key={response_key}, span_id={response_span_id}")
                            
                            # Set the output using the method for double insurance
                            if hasattr(output_span, "set_output"):
                                output_span.set_output(full_response)
                        
                    except Exception as generation_error:
                        # Record error in telemetry
                        llm_span.record_exception(generation_error)
                        llm_span.set_attribute("generation_error", str(generation_error))
                        llm_span.set_attribute("generation_complete", False)
                        logger.error(f"Error generating response: {generation_error}")
                        
                        # Set partial output directly on main span if available
                        if full_response:
                            # Primary content field - most important for Phoenix display
                            llm_span.set_attribute("content", full_response)
                            
                            # Set using the output method if available
                            if hasattr(llm_span, "set_output"):
                                llm_span.set_output(full_response)
                            
                            # Also set standard output attributes for maximum compatibility
                            llm_span.set_attribute("output", full_response)
                            llm_span.set_attribute("output.value", full_response)
                            llm_span.set_attribute(SpanAttributes.OUTPUT, full_response)
                            llm_span.set_attribute("openinference.llm.output", full_response)
                            llm_span.set_attribute("llm.output", full_response)
                            llm_span.set_attribute("error", str(generation_error))
                            
                        # Create a specific error output span for Phoenix compatibility
                        with create_span(
                            SpanNames.LLM_GENERATION + ".error",  # Use error name to distinguish
                            attributes={
                                SpanAttributes.SESSION_ID: session_id,
                                SpanAttributes.QA_ID: qa_id,
                                "description": "LLM Generation Error",
                                "kind": "LLM",  # Direct kind attribute
                                "span.kind": "LLM",  # Alternative format
                                "openinference.span.kind": OpenInferenceSpanKind.LLM,
                                "content": str(generation_error),
                                "output": str(generation_error),
                                "error_message": str(generation_error),
                                "partial_response": full_response,
                                "error_type": generation_error.__class__.__name__,
                            }
                        ) as error_span:
                            # Set the error using the method for double insurance
                            if hasattr(error_span, "set_output"):
                                error_span.set_output(str(generation_error))
                                
                        # Re-raise
                        error_msg = f"Error generating response: {str(generation_error)}"
                        yield error_msg
                
                # Return the telemetry-wrapped generator
                return telemetry_wrapped_generator(), qa_id
                
            except Exception as setup_error:
                # Log the error
                logger.error(f"Error setting up response generation: {setup_error}", exc_info=True)
                
                # Record error in span
                llm_span.record_exception(setup_error)
                llm_span.set_attribute("setup_error", str(setup_error))
                
                # Return an error generator
                def error_generator():
                    error_msg = f"Error generating response: {str(setup_error)}"
                    yield error_msg
                
                return error_generator(), qa_id
                
    except Exception as span_error:
        # Handle the case where create_span itself fails
        logger.error(f"Error creating LLM span: {span_error}", exc_info=True)
        
        # Generate QA ID if not provided
        if not qa_id:
            qa_id = str(uuid.uuid4())
        
        # Capture error message before defining nested function
        error_message = f"Error generating response: {str(span_error)}"
        
        # Return an error generator
        def error_generator():
            yield error_message
        
        return error_generator(), qa_id

def _set_span_output_attributes(span, content: str, error: str = None):
    """Helper function to set output attributes on a span consistently"""
    # Set only the Phoenix-recognized content field
    span.set_attribute("content", content)
    if error:
        span.set_attribute("error", error)

def _create_error_span(session_id: str, qa_id: str, error: Exception, partial_response: str = ""):
    """Helper function to create error spans consistently"""
    return create_span(
        SpanNames.LLM_GENERATION + ".error",
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            "description": "LLM Generation Error",
            "kind": "LLM",
            "span.kind": "LLM",
            "openinference.span.kind": "LLM",
            "content": str(error),
            "output": str(error),
            "error_message": str(error),
            "partial_response": partial_response,
            "error_type": error.__class__.__name__,
        },
        kind="LLM", otel_kind=SpanKind.INTERNAL
    )