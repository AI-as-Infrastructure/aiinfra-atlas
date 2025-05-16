"""
LLM utilities for ATLAS.

This module provides functions for interacting with Language Models,
with built-in telemetry instrumentation.
"""

import logging
import time
import json
import os
from typing import List, Dict, Any, Optional, Generator, Union, Callable, Tuple

from langchain_core.documents.base import Document
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.language_models.chat_models import BaseChatModel

from backend.telemetry import create_span, SpanAttributes, SpanNames, OpenInferenceSpanKind
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
    provider: Optional[str] = None
) -> Generator[str, None, None]:
    """
    Generate a response using an LLM.
    
    Args:
        question: User question
        documents: Retrieved documents
        chat_history: Optional chat history
        system_prompt: Optional system prompt
        temperature: LLM temperature
        span: Optional parent span
        provider: Optional LLM provider override
        
    Yields:
        Response chunks
    """
    try:
        # Create span for telemetry, but handle case where spans might not be available
        with create_span(
            SpanNames.LLM_GENERATION,
            attributes={
                "question": question,
                "document_count": len(documents),
                "has_chat_history": bool(chat_history),
                "temperature": temperature,
                "openinference.span.kind": OpenInferenceSpanKind.LLM
            },
            link_to_current=True
        ) as llm_span:
            try:
                # Format documents for context
                context = format_documents(documents)
                if llm_span:
                    llm_span.set_attribute("context_length", len(context))
                
                # Create LLM with the specified provider (or from config)
                llm = create_llm(temperature=temperature, provider=provider)
                if llm_span:
                    llm_span.set_attribute("model", getattr(llm, "model_name", str(llm)))
                
                # Format chat history (ensure it's not None)
                chat_history_list = chat_history or []
                formatted_history = format_chat_history(chat_history_list)
                chat_history_str = "\n".join([f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}" 
                                           for msg in formatted_history])
                
                if llm_span:
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
                
                # Start generation timer
                start_time = time.time()
                
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
                    logger.debug(f"Formatted prompt: {formatted_prompt[:200]}...")
                    
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
                        
                        # Log chunk content for debugging (truncated)
                        logger.debug(f"Raw chunk content: {content[:20]}...")
                            
                        # Detect and handle placeholder text if somehow still present
                        placeholder_pattern = "{answer}"
                        if placeholder_pattern in content:
                            logger.warning(f"Detected placeholder '{placeholder_pattern}' in content")
                            content = content.replace(placeholder_pattern, 
                                "I need more specific information to answer this question based on the provided context.")
                        
                        # Update tracking variables
                        full_response += content
                        chunk_count += 1
                        
                        # Record intermediate metrics
                        if llm_span and chunk_count % 10 == 0:
                            llm_span.set_attribute("chunk_count", chunk_count)
                            llm_span.set_attribute("response_length", len(full_response))
                        
                        # Yield the content
                        yield content
                    
                except Exception as e:
                    logger.error(f"Error during streaming: {e}")
                    if llm_span:
                        llm_span.record_exception(e)
                    if not full_response:
                        full_response = f"Error generating response: {str(e)}"
                        yield full_response
                
                # Calculate generation time
                generation_time = time.time() - start_time
                
                # Record final metrics
                if llm_span:
                    llm_span.set_attribute("final_chunk_count", chunk_count)
                    llm_span.set_attribute("final_response_length", len(full_response))
                    llm_span.set_attribute("generation_time_seconds", generation_time)
                    llm_span.set_attribute("generation_complete", True)
                    llm_span.set_attribute("openinference.llm.output", full_response)
                    if hasattr(SpanAttributes, 'OUTPUT'):
                        llm_span.set_attribute(SpanAttributes.OUTPUT, full_response)
                
            except Exception as e:
                # Record error in telemetry
                if llm_span:
                    llm_span.record_exception(e)
                    llm_span.set_attribute("generation_error", str(e))
                    llm_span.set_attribute("generation_complete", False)
                    llm_span.set_attribute("openinference.llm.output", full_response)
                    if hasattr(SpanAttributes, 'OUTPUT'):
                        llm_span.set_attribute(SpanAttributes.OUTPUT, full_response)
                
                # Log the error
                logger.error(f"Error generating response: {e}", exc_info=True)
                
                # Yield error message and stop
                error_message = f"Error generating response: {str(e)}"
                yield error_message
                
    except Exception as e:
        # Handle the case where create_span itself fails (telemetry not initialized)
        logger.error(f"Telemetry error in response generation: {e}", exc_info=True)
        error_message = f"Error generating response: {str(e)}"
        # No span available, but if you add telemetry later, this is where to set output
        yield error_message

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
    Generate a response with full telemetry instrumentation.
    
    This function creates its own telemetry span and is suitable for use
    in high-level code that doesn't create spans itself.
    
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
    
    try:
        # Create telemetry span, but handle case where telemetry might not be initialized
        with create_span(
            SpanNames.LLM_GENERATION,
            attributes={
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.QA_ID: qa_id,
                SpanAttributes.DOCUMENT_COUNT: len(documents),
                "question": question,
                "has_chat_history": bool(chat_history),
                "chat_history_turns": len(chat_history) if chat_history else 0,
                "corpus_filter": corpus_filter or "all",
                "llm_provider": provider,
                "openinference.span.kind": OpenInferenceSpanKind.LLM,
                "input.value": question  # Set input.value for Phoenix UI
            }
        ) as qa_span:
            try:
                # Generate response
                response_generator = generate_response(
                    question=question,
                    documents=documents,
                    chat_history=chat_history,
                    provider=provider
                )
                
                def telemetry_wrapped_generator():
                    full_response = ""
                    try:
                        for chunk in response_generator:
                            full_response += chunk
                            yield chunk
                    except Exception as e:
                        # Propagate errors so the caller can handle them (and emit error/citation messages)
                        raise
                    finally:
                        # After the generator is exhausted (normal or error), set the output on the span
                        if qa_span:
                            # Set OpenInference semantic output for Phoenix Output field
                            if hasattr(qa_span, "set_output"):
                                qa_span.set_output(full_response)
                            qa_span.set_attribute("output.value", full_response)
                            # Retain legacy attributes for compatibility
                            qa_span.set_attribute("openinference.llm.output", full_response)
                            qa_span.set_attribute("openinference.agent.output", full_response)
                            # Also set input.value again to guarantee both present
                            qa_span.set_attribute("input.value", question)
                return telemetry_wrapped_generator(), qa_id
                
            except Exception as e:
                # Record error in telemetry if span available
                if qa_span:
                    qa_span.record_exception(e)
                    qa_span.set_attribute("generation_error", str(e))
                
                # Log the error
                logger.error(f"Error in response generation with telemetry: {e}", exc_info=True)
                
                # Create an error generator
                def error_generator():
                    yield f"Error generating response: {str(e)}"
                
                # Return the error generator
                return error_generator(), qa_id
    
    except Exception as e:
        # Handle the case where create_span itself fails
        logger.error(f"Telemetry error in response generation: {e}", exc_info=True)
        
        # Create an error generator
        def error_generator():
            yield f"Error generating response: {str(e)}"
        
        # Return the error generator
        return error_generator(), qa_id