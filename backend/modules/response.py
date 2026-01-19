"""
Response generation utilities for ATLAS.

This module provides functions for generating LLM responses with streaming
and telemetry instrumentation.
"""

import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Generator, Tuple
from datetime import datetime

from langchain_core.documents.base import Document
from langchain_core.messages import HumanMessage, AIMessage

from backend.telemetry import create_span, SpanAttributes, SpanNames, OpenInferenceSpanKind, set_span_outputs
from backend.telemetry.spans import register_span
from opentelemetry.trace import SpanKind, Status, StatusCode
from backend.modules.config import get_system_prompt, get_llm_config
from backend.modules.prompt_cache import optimize_prompt_for_provider
from backend.modules.streaming import create_error_message, format_sse_message
from backend.modules.llm import format_documents, format_chat_history, create_llm

logger = logging.getLogger(__name__)


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

            # Get model information for caching
            model_name = getattr(llm, "model_name", getattr(llm, "model", "unknown"))
            provider_name = provider or "unknown"

            # Format chat history (ensure it's not None)
            chat_history_list = chat_history or []
            formatted_history = format_chat_history(chat_history_list)
            chat_history_str = "\n".join([f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                                       for msg in formatted_history])

            # Get system prompt for caching
            effective_system_prompt = system_prompt or get_system_prompt()

            # Use universal prompt caching for all providers
            optimized_prompt, cache_info = optimize_prompt_for_provider(
                system_prompt=effective_system_prompt,
                context=context,
                provider=provider_name,
                model=model_name
            )

            # Build complete prompt with chat history and question
            if chat_history_list:
                final_prompt = f"{optimized_prompt}Previous conversation:\n{chat_history_str}\n\nUser question: {question}\n\nAnswer:"
            else:
                final_prompt = f"{optimized_prompt}User question: {question}\n\nAnswer:"

            # Log cache performance
            if cache_info.get("cache_hit"):
                logger.info(f"Prompt cache hit for {provider_name}/{model_name} "
                           f"(hit #{cache_info.get('hit_count', 0)}, "
                           f"estimated {cache_info.get('token_savings_estimated', 0)} tokens saved)")
            else:
                logger.debug(f"Prompt cached for future use: {provider_name}/{model_name}")

            # Generate response
            full_response = ""

            try:
                # Process the streaming response using optimized prompt
                for chunk in llm.stream(final_prompt):
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
                    error_data = create_error_message("streaming_error", "An error occurred during response generation")
                    full_response = format_sse_message(error_data)
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
                model_name = getattr(llm, "model_name", getattr(llm, "model", str(llm)))
                provider_name = provider or "unknown"
                llm_span.set_attribute("model", model_name)
                llm_span.set_attribute("provider", provider_name)

                # Format chat history (ensure it's not None)
                chat_history_list = chat_history or []
                formatted_history = format_chat_history(chat_history_list)
                chat_history_str = "\n".join([f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                                           for msg in formatted_history])

                llm_span.set_attribute("chat_history_turns", len(formatted_history))

                # Get system prompt for caching
                effective_system_prompt = system_prompt or get_system_prompt()

                # Use universal prompt caching for all providers
                optimized_prompt, cache_info = optimize_prompt_for_provider(
                    system_prompt=effective_system_prompt,
                    context=context,
                    provider=provider_name,
                    model=model_name
                )

                # Add cache information to telemetry
                llm_span.set_attribute("cache_hit", cache_info.get("cache_hit", False))
                llm_span.set_attribute("cache_optimization", cache_info.get("optimization", "none"))
                if cache_info.get("cache_hit"):
                    llm_span.set_attribute("cache_hit_count", cache_info.get("hit_count", 0))
                    llm_span.set_attribute("token_savings_estimated", cache_info.get("token_savings_estimated", 0))

                # Build complete prompt with chat history and question
                if chat_history_list:
                    formatted_prompt = f"{optimized_prompt}Previous conversation:\n{chat_history_str}\n\nUser question: {question}\n\nAnswer:"
                else:
                    formatted_prompt = f"{optimized_prompt}User question: {question}\n\nAnswer:"

                # Log cache performance and prompt details
                if cache_info.get("cache_hit"):
                    logger.info(f"Prompt cache hit for {provider_name}/{model_name} "
                               f"(hit #{cache_info.get('hit_count', 0)}, "
                               f"estimated {cache_info.get('token_savings_estimated', 0)} tokens saved)")
                else:
                    logger.debug(f"Prompt cached for future use: {provider_name}/{model_name}")

                logger.debug(f"Built optimized prompt with {len(formatted_history)} chat history turns, "
                           f"cache: {cache_info.get('optimization', 'none')}")

                # Stream response
                full_response = ""
                chunk_count = 0

                # Generate response
                logger.debug(f"Starting stream with {llm.__class__.__name__}")

                try:
                    # Use the optimized formatted prompt
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

                    # Set output attributes efficiently using Phoenix standards only
                    llm_span.set_attribute("output", full_response)  # Primary Phoenix UI field
                    llm_span.set_attribute("openinference.llm.output", full_response)  # OpenInference standard

                    # Set response metrics
                    llm_span.set_attribute(SpanAttributes.RESPONSE_LENGTH, len(full_response))

                    # Set response preview for quick viewing
                    sentences = full_response.split('. ')
                    preview = '. '.join(sentences[:3]) + ('...' if len(sentences) > 3 else '')
                    llm_span.set_attribute("response_preview", preview)

                    # Add output.value for Phoenix high-level overview
                    llm_span.set_attribute("output.value", preview)

                    # NEW: propagate preview to the parent/root RAG pipeline span so that it shows in Phoenix overview
                    try:
                        from backend.telemetry.spans import find_session_root_span_id, update_span_attributes
                        root_span_id = find_session_root_span_id(session_id)
                        # Only update if we found a distinct root span (i.e., not the same as this LLM span)
                        if root_span_id and root_span_id != span_id:
                            update_span_attributes(
                                root_span_id,
                                {
                                    "output.value": preview,
                                    "output": full_response,
                                    "response_length": len(full_response),
                                },
                            )
                    except Exception as root_update_error:
                        logger.debug(
                            f"Could not propagate output.value to root span: {root_update_error}",
                            exc_info=True,
                        )

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

                    # Set output attributes efficiently using Phoenix standards only
                    llm_span.set_attribute("output", full_response)  # Primary Phoenix UI field
                    llm_span.set_attribute("openinference.llm.output", full_response)  # OpenInference standard

                    # Set response metrics
                    llm_span.set_attribute(SpanAttributes.RESPONSE_LENGTH, len(full_response))

                    # Set response preview for quick viewing
                    sentences = full_response.split('. ')
                    preview = '. '.join(sentences[:3]) + ('...' if len(sentences) > 3 else '')
                    llm_span.set_attribute("response_preview", preview)

                    # Add output.value for Phoenix high-level overview
                    llm_span.set_attribute("output.value", preview)

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

                # Set output attributes efficiently using Phoenix standards only
                llm_span.set_attribute("output", full_response)  # Primary Phoenix UI field
                llm_span.set_attribute("openinference.llm.output", full_response)  # OpenInference standard

                # Set response metrics
                llm_span.set_attribute(SpanAttributes.RESPONSE_LENGTH, len(full_response))

                # Set response preview for quick viewing
                sentences = full_response.split('. ')
                preview = '. '.join(sentences[:3]) + ('...' if len(sentences) > 3 else '')
                llm_span.set_attribute("response_preview", preview)

                # Add output.value for Phoenix high-level overview
                llm_span.set_attribute("output.value", preview)

                # Yield the final response
                yield full_response

    except Exception as e:
        # Handle any exceptions outside of span context
        logger.error(f"Error creating LLM span: {e}", exc_info=True)

        # Yield generic error message
        error_data = create_error_message("span_creation_error", "An error occurred while processing your request")
        yield format_sse_message(error_data)


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

        # Define generator that owns the telemetry span lifetime
        def telemetry_wrapped_generator():
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
                session_id=session_id,
                kind=OpenInferenceSpanKind.LLM,
                otel_kind=SpanKind.INTERNAL
            ) as llm_span:
                from backend.telemetry.spans import register_span
                span_id = str(llm_span.get_span_context().span_id)
                register_span(session_id, qa_id, span_id)
                logger.info(f"Registered main LLM span with session_id={session_id}, qa_id={qa_id}, span_id={span_id}")

                # Add cache statistics to span
                from backend.modules.prompt_cache import get_cache_statistics
                cache_stats = get_cache_statistics()
                llm_span.set_attribute("cache_enabled", cache_stats.get("enabled", False))
                llm_span.set_attribute("cache_total_entries", cache_stats.get("total_entries", 0))
                llm_span.set_attribute("cache_total_hits", cache_stats.get("total_hits", 0))

                # Generate response without nested span
                response_gen = generate_response(
                    question=question,
                    documents=documents,
                    chat_history=chat_history,
                    system_prompt=get_system_prompt(),
                    temperature=0.7,
                    provider=provider,
                    span=llm_span,
                    create_llm_span=False
                )

                # Begin streaming
                full_response = ""
                chunk_count = 0
                generation_start_time = datetime.now()

                try:
                    for chunk in response_gen:
                        full_response += chunk
                        chunk_count += 1
                        if chunk_count % 5 == 0:
                            llm_span.set_attribute("chunk_count", chunk_count)
                            llm_span.set_attribute("response_length", len(full_response))
                        yield chunk

                    # Final metrics
                    generation_time = (datetime.now() - generation_start_time).total_seconds()
                    llm_span.set_attribute("final_chunk_count", chunk_count)
                    llm_span.set_attribute("final_response_length", len(full_response))
                    llm_span.set_attribute("generation_time_seconds", generation_time)
                    llm_span.set_attribute("generation_complete", True)

                    llm_span.set_attribute("output", full_response)
                    llm_span.set_attribute("openinference.llm.output", full_response)
                    llm_span.set_attribute(SpanAttributes.RESPONSE_LENGTH, len(full_response))

                    sentences = full_response.split('. ')
                    preview = '. '.join(sentences[:3]) + ('...' if len(sentences) > 3 else '')
                    llm_span.set_attribute("response_preview", preview)

                    # Add output.value for Phoenix high-level overview
                    llm_span.set_attribute("output.value", preview)

                    # Add token counts
                    try:
                        from backend.telemetry.token_counting import add_token_counts_to_span
                        add_token_counts_to_span(
                            span=llm_span,
                            prompt_text=question,
                            completion_text=full_response,
                            response_obj=None,
                            provider=provider
                        )
                    except Exception as token_error:
                        logger.debug(f"Could not calculate token counts: {token_error}")

                    # Create response span
                    response_span_name = f"{SpanNames.LLM_GENERATION}.response"
                    with create_span(
                        response_span_name,
                        attributes={
                            SpanAttributes.SESSION_ID: session_id,
                            SpanAttributes.QA_ID: qa_id,
                            "input.value": question,
                            "output.value": f"Generated response ({len(full_response.split())} words, {generation_time:.2f}s)",
                            "output": full_response,
                            "response_length": len(full_response),
                            "word_count": len(full_response.split()),
                            "generation_time_seconds": generation_time,
                            "description": "LLM Response Output",
                            "openinference.span.kind": OpenInferenceSpanKind.LLM,
                        },
                        session_id=session_id,
                        kind=OpenInferenceSpanKind.LLM
                    ) as response_span:
                        response_key = f"{qa_id}_response"
                        register_span(session_id, response_key, str(response_span.get_span_context().span_id))

                except Exception as generation_error:
                    llm_span.record_exception(generation_error)
                    llm_span.set_attribute("generation_error", str(generation_error))
                    llm_span.set_attribute("generation_complete", False)
                    logger.error(f"Error generating response: {generation_error}")
                    error_data = create_error_message("generation_error", "An error occurred while generating the response")
                    yield format_sse_message(error_data)

        # Return the generator and qa_id
        return telemetry_wrapped_generator(), qa_id

    except Exception as span_error:
        # Handle the case where create_span itself fails
        logger.error(f"Error creating LLM span: {span_error}", exc_info=True)

        # Generate QA ID if not provided
        if not qa_id:
            qa_id = str(uuid.uuid4())

        # Return an error generator with generic message
        def error_generator():
            error_data = create_error_message("span_error", "An error occurred while processing your request")
            yield format_sse_message(error_data)

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
            "openinference.span.kind": OpenInferenceSpanKind.LLM,
            "content": str(error),
            "output": str(error),
            "error_message": str(error),
            "partial_response": partial_response,
            "error_type": error.__class__.__name__,
        },
        session_id=session_id,
        kind=OpenInferenceSpanKind.LLM,
        otel_kind=SpanKind.INTERNAL
    )
