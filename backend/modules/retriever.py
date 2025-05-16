import os
import importlib
import logging
import uuid
import datetime
from dotenv import load_dotenv
from typing import Sequence, List, Dict, Any, Optional
from typing_extensions import TypedDict

# Import centralized telemetry module
from modules.telemetry import (
    create_span, extract_trace_context, inject_trace_context,
    SpanAttributes, record_exception, SpanKind
)

# Keep Status and StatusCode for error handling
from opentelemetry.trace import Status, StatusCode

# LangChain imports
from langchain_huggingface import HuggingFaceEmbeddings  
from langchain_community.vectorstores import Redis
from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.documents.base import Document

# Helper functions and prompts.
from modules.detect_contexts import detect_context_conditions
from modules.system_prompts import system_prompt, contextualize_q_system_prompt

# For document selection (no ranking)
import numpy as np

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment and import target configuration
# Import secrets manager to access configuration
from utils.secrets_manager import get_secret

# Get the test target from the configuration
test_config_module_name = get_secret('TEST_TARGET')
if not test_config_module_name:
    raise ValueError("TEST_TARGET not found in configuration")

# Extract the module name from the full path if it includes 'backend.targets'
if test_config_module_name.startswith('backend.targets.'):
    # Remove the 'backend.' prefix as we're already in the backend directory
    test_config_module_name = test_config_module_name[8:]

# Try to import the module
try:
    test_config_module = importlib.import_module(test_config_module_name)
except ImportError:
    # If that fails, try with just the last part of the path
    try:
        module_parts = test_config_module_name.split('.')
        last_part = module_parts[-1]
        test_config_module = importlib.import_module(f"targets.{last_part}")
    except ImportError:
        try:
            # Try to import the nested module structure (module_name/module_name.py pattern)
            module_parts = test_config_module_name.split('.')
            if len(module_parts) >= 2:
                module_name = module_parts[-1]
                test_config_module = importlib.import_module(f"targets.{module_name}.{module_name}")
            else:
                raise ImportError()
        except ImportError:
            raise ImportError(f"Could not import target configuration module '{test_config_module_name}'. Make sure it exists in the targets directory.")

LLM = test_config_module.LLM
EMBEDDING_MODEL = test_config_module.EMBEDDING_MODEL
DATABASE_URL = test_config_module.DATABASE_URL
SEARCH_TYPE = test_config_module.SEARCH_TYPE
SEARCH_KWARGS = test_config_module.SEARCH_KWARGS
INDEX_NAME = test_config_module.INDEX_NAME
ALGORITHM = test_config_module.ALGORITHM
CHUNK_SIZE = test_config_module.CHUNK_SIZE
CHUNK_OVERLAP = test_config_module.CHUNK_OVERLAP
SYSTEM_PROMPT = system_prompt
index_schema = test_config_module.index_schema
format_docs = test_config_module.format_docs

get_retriever = getattr(test_config_module, 'get_retriever')
retriever = get_retriever()  # Initialize the retriever

# Helper function to get fetch_k from search kwargs
def get_fetch_k():
    """Get the number of documents to retrieve from the search configuration."""
    # Redis only accepts "k" as the parameter name
    return int(SEARCH_KWARGS.get("k", 3))

# Helper function to get citation limit from search kwargs
def get_citation_limit():
    """Get the number of citations to display from the search configuration."""
    if "citation_limit" in SEARCH_KWARGS:
        return int(SEARCH_KWARGS["citation_limit"])
    return get_fetch_k()

# Format citations in a consistent structure
def format_citations(docs_with_weight: List[tuple]) -> List[Dict[str, Any]]:
    """Format documents into a consistent citation structure.
    
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
        quote = full_content[:max_quote_length]
        if len(full_content) > max_quote_length:
            quote = quote.rsplit(' ', 1)[0] + '...'
        citation = {
            "source_id": doc.metadata.get('id', citation_id),
            "quote": quote.strip(),
            "full_content": full_content,
            "text": quote.strip(),  # For backward compatibility
            "content": full_content,  # For backward compatibility
            "title": doc.metadata.get('title', f"Document {doc.metadata.get('id', 'Unknown')}"),
            "url": doc.metadata.get('url'),
            "page": doc.metadata.get('page'),
            "corpus": doc.metadata.get('corpus'),
            "date": doc.metadata.get('date'),
            "weight": float(weight),
            "id": doc.metadata.get('id', citation_id),
            "has_more": len(full_content) > max_quote_length
        }
        citations.append(citation)
    return citations

# Define QA prompt template.
qa_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# Define a prompt for contextualizing questions.
contextualize_q_prompt = ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

history_aware_retriever = create_history_aware_retriever(LLM, retriever, contextualize_q_prompt)
question_answer_chain = create_stuff_documents_chain(LLM, qa_prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

# Define a state schema.
class State(TypedDict):
    input: str
    chat_history: Sequence[BaseMessage]
    context: str
    answer: str
    question: str
    session_id: str
    qa_id: str
    request_structured_citations: Optional[bool]

async def call_model(state: State, socket=None):
    """Process a query using the RAG pipeline and generate a response with citations.
    
    Args:
        state: Dictionary containing query information and chat history
        socket: Optional socket.io instance for streaming responses
        
    Returns:
        Dictionary containing response data with answer and citations
    """
    session_id = state.get("session_id", "unknown")
    qa_id = state.get("qa_id", f"qa_{uuid.uuid4()}")
    request_structured_citations = state.get("request_structured_citations", False)
    trace_context = state.get("trace_context", {})
    
    # Extract trace context
    current_context = extract_trace_context(trace_context)
    
    # Prepare span attributes
    span_attributes = {
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.QA_ID: qa_id,
        SpanAttributes.INPUT_VALUE: state["input"],
        SpanAttributes.CHAT_HISTORY_LENGTH: len(state.get("chat_history", [])),
        SpanAttributes.LLM_MODEL: str(getattr(LLM, 'model_name', getattr(LLM, 'model', str(LLM)))),
        SpanAttributes.TIMESTAMP: datetime.datetime.utcnow().isoformat(),
        SpanAttributes.REQUEST_STRUCTURED_CITATIONS: request_structured_citations,
        "atlas.user.question": state["input"],  # Include user question directly in call_model span
        "span.kind": "SERVER",  # Add span.kind attribute to help Arize identify this as a session
        "openinference.span.kind": "agent",  # Add openinference.span.kind attribute for Arize session recognition
        "session.id": session_id  # Add explicit session.id attribute in the format Arize expects
    }
    
    # Create span with context
    span_cm = create_span("call_model", attributes=span_attributes, context=current_context)
    
    with span_cm as parent_span:
        try:
            # Store span ID in environment variables for later feedback association
            try:
                from opentelemetry.trace import format_span_id
                span_context = parent_span.get_span_context()
                if span_context:
                    span_id = format_span_id(span_context.span_id)
                    # Store the span ID in environment variables keyed by both qa_id and session_id
                    # This will help the feedback system find the right span later
                    os.environ[f"ATLAS_SPAN_ID_{qa_id}"] = span_id
                    os.environ[f"ATLAS_CALL_MODEL_SPAN_ID_{qa_id}"] = span_id
                    logger.info(f"Stored call_model span ID {span_id} for qa_id {qa_id}")
                    
                    # Create a file-based cache as a fallback if environment variables are lost
                    # between requests (which can happen in some deployment environments)
                    cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".span_cache")
                    os.makedirs(cache_dir, exist_ok=True)
                    cache_file = os.path.join(cache_dir, f"{qa_id}.span")
                    with open(cache_file, "w") as f:
                        f.write(span_id)
                    logger.debug(f"Cached span ID to {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to store span ID for later feedback: {e}")
            
            state["question"] = state["input"]
            
            with create_span("detect_contexts", kind=SpanKind.SERVER) as context_span:
                detected_contexts = detect_context_conditions(state["input"])
                
                if len(detected_contexts) == 1 and detected_contexts[0] in ['au', 'nz', 'uk']:
                    metadata_constraints = [f'1901-{detected_contexts[0]}']
                    parent_span.set_attribute(SpanAttributes.QUERY_FOCUS, detected_contexts[0])
                    logger.info(f"Enforcing strict country filter for {detected_contexts[0]}")
                else:
                    metadata_constraints = ['1901-au', '1901-nz', '1901-uk']
                    parent_span.set_attribute(SpanAttributes.QUERY_FOCUS, "balanced")
                
                parent_span.set_attribute(SpanAttributes.DETECTED_CONTEXTS, str(detected_contexts))
                parent_span.set_attribute(SpanAttributes.METADATA_CONSTRAINTS, str(metadata_constraints))
            
            with create_span("document_retrieval", kind=SpanKind.SERVER) as retrieval_span:
                retrieval_kwargs = {}
                if "k" in SEARCH_KWARGS:
                    retrieval_kwargs["k"] = int(SEARCH_KWARGS["k"])
                if "score_threshold" in SEARCH_KWARGS:
                    retrieval_kwargs["score_threshold"] = float(SEARCH_KWARGS["score_threshold"])
                fetch_k = int(SEARCH_KWARGS.get("k", 3))
                if metadata_constraints:
                    documents = retriever.get_relevant_documents(
                        state["input"], 
                        metadata_constraints=metadata_constraints,
                        k=retrieval_kwargs.get("k"),
                        score_threshold=retrieval_kwargs.get("score_threshold")
                    )
                else:
                    documents = retriever.get_relevant_documents(
                        state["input"],
                        k=retrieval_kwargs.get("k"),
                        score_threshold=retrieval_kwargs.get("score_threshold") 
                    )
                parent_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(documents))
                parent_span.set_attribute(SpanAttributes.FETCH_K, fetch_k)
                logger.debug(f"Retrieved {len(documents)} documents with fetch_k={fetch_k}")
            
            if not all(hasattr(doc, 'page_content') and hasattr(doc, 'metadata') for doc in documents):
                logger.error("Retrieved documents do not have the expected structure")
                if parent_span:
                    parent_span.set_status(Status(StatusCode.ERROR, "Invalid document structure"))
                return {"error": "Retrieved documents do not have the expected structure"}
            
            with create_span("format_documents", kind=SpanKind.SERVER) as format_span:
                formatted_docs_with_metadata = [
                    {
                        "serialized": dumpd(doc),
                        "content": doc.page_content,
                        "id": doc.metadata.get('id'),
                        "date": doc.metadata.get('date'),
                        "url": doc.metadata.get('url'),
                        "page": doc.metadata.get('page'),
                        "loc": doc.metadata.get('loc'),
                        "corpus": doc.metadata.get('corpus')
                    }
                    for doc in documents
                ]
                logger.debug(f"Formatted documents with metadata: {formatted_docs_with_metadata}")
            
            chain_input = {
                "input": state["input"],
                "question": state["input"],
                "context": formatted_docs_with_metadata,
                "chat_history": state["chat_history"]
            }
            
            logger.debug(f"Chain input: {chain_input}")
            
            if socket and hasattr(rag_chain, "astream"):
                with create_span(
                    "stream_llm_response", 
                    kind=SpanKind.SERVER,
                    attributes={SpanAttributes.IS_STREAMING: True, SpanAttributes.SESSION_ID: session_id}
                ) as stream_span:
                    answer_chunks = []
                    chunk_count = 0
                    async for chunk in rag_chain.astream(chain_input):
                        chunk_count += 1
                        if isinstance(chunk, dict):
                            chunk_text = chunk.get("answer", " ".join(
                                [str(value) for key, value in chunk.items() if key not in {"input", "question", "chat_history", "context"}]
                            ))
                        else:
                            chunk_text = str(chunk)
                        
                        # Get trace context for the chunk
                        carrier = inject_trace_context()
                        
                        chunk_data = {
                            "message": chunk_text,
                            "session_id": session_id,
                            "qa_id": qa_id,
                            "chunk_number": chunk_count,
                            "trace_context": {
                                "traceparent": carrier.get("traceparent", ""),
                                "tracestate": carrier.get("tracestate", "")
                            }
                        }
                        if chunk_text.strip():
                            socket.emit("response", chunk_data)
                            logger.debug(f"Emitted chunk: {chunk_text} for qa_id: {qa_id}")
                            answer_chunks.append(chunk_text)
                    
                    answer_text = "".join(answer_chunks)
                    parent_span.set_attribute(SpanAttributes.CHUNK_COUNT, chunk_count)
                    parent_span.set_attribute(SpanAttributes.RESPONSE_LENGTH, len(answer_text))
                # After streaming, emit final sources using basic document selection.
                with create_span(
                    "emit_citations",
                    kind=SpanKind.SERVER,
                    attributes={SpanAttributes.SESSION_ID: session_id}
                ) as citations_span:
                    citation_limit = get_citation_limit()
                    logger.debug(f"Using citation_limit: {citation_limit} (from config: {SEARCH_KWARGS})")
                    selected_docs = documents[:citation_limit]
                    docs_with_weight = [(doc, 1.0) for doc in selected_docs]
                    citations = format_citations(docs_with_weight)
                    
                    parent_span.set_attribute(SpanAttributes.CITATION_COUNT, len(citations))
                    parent_span.set_attribute(SpanAttributes.CITATION_LIMIT, citation_limit)
                    
                    # Get trace context for sources payload
                    carrier = inject_trace_context()
                    
                    sources_payload = {
                        "sources": citations,
                        "session_id": session_id,
                        "qa_id": qa_id,
                        "trace_context": {
                            "traceparent": carrier.get("traceparent", ""),
                            "tracestate": carrier.get("tracestate", "")
                        }
                    }
                    socket.emit("response", sources_payload)
                    logger.debug(f"Emitted enhanced citations: {sources_payload}")
                
                if parent_span:
                    parent_span.set_status(Status(StatusCode.OK))
                return {"status": "streaming complete"}
            else:
                with create_span(
                    "invoke_llm_response", 
                    kind=SpanKind.SERVER,
                    attributes={SpanAttributes.IS_STREAMING: False, SpanAttributes.SESSION_ID: session_id}
                ) as invoke_span:
                    result = rag_chain.invoke(chain_input)
                    logger.debug(f"RAG chain raw response: {result}")
                    
                    if hasattr(result, '__iter__') and not isinstance(result, dict):
                        messages = list(result)
                    else:
                        messages = [result]
                    
                    if not messages:
                        fallback = "No response was generated. Please try again."
                        if socket:
                            socket.emit("response", {"message": fallback})
                        logger.warning(fallback)
                        if parent_span:
                            parent_span.set_status(Status(StatusCode.ERROR, "No response generated"))
                        return {"chat_history": state["chat_history"]}
                    
                    if isinstance(messages[0], dict) and "answer" in messages[0]:
                        answer_text = messages[0]["answer"]
                    else:
                        answer_text = messages[0] if isinstance(messages[0], str) else str(messages[0])
                    
                    parent_span.set_attribute(SpanAttributes.RESPONSE_LENGTH, len(answer_text))
            
            with create_span("update_chat_history", kind=SpanKind.SERVER) as history_span:
                citation_limit = get_citation_limit()
                selected_docs = documents[:citation_limit]
                docs_with_weight = [(doc, 1.0) for doc in selected_docs]
                citations = format_citations(docs_with_weight)
                
                chat_history = state["chat_history"] + [
                    {"role": "human", "content": state["input"]},
                    {"role": "ai", "content": answer_text, "sources": citations}
                ]
                
                if parent_span:
                    parent_span.set_status(Status(StatusCode.OK))
                    parent_span.set_attribute(SpanAttributes.CITATION_COUNT, len(citations))
                    parent_span.set_attribute(SpanAttributes.CITATION_LIMIT, citation_limit)
                
                if socket:
                    socket.emit("finalize_qa", {
                        "session_id": session_id,
                        "qa_id": qa_id,
                        "answer": answer_text,
                        "question": state["input"],
                        "citations": citations
                    })
                
                return {
                    "chat_history": chat_history,
                    "context": formatted_docs_with_metadata,
                    "answer": answer_text,
                    "qa_id": qa_id,
                    "sources": citations
                }
            
        except Exception as e:
            if parent_span:
                record_exception(parent_span, e)
            logger.error(f"Error in call_model: {e}", exc_info=True)
            if socket:
                socket.emit("response", {"message": "Internal Server Error"})
            return {"error": "Internal Server Error"}