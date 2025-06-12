"""
Telemetry constants for Phoenix Arize integration.

This module centralizes all constants used in telemetry to ensure consistency
across the application.
"""

from enum import Enum, auto

# OpenInference span kinds for Phoenix Arize
class OpenInferenceSpanKind:
    """Phoenix Arize OpenInference span kinds for proper categorization"""
    CHAIN = "CHAIN"           # General logic operations
    LLM = "LLM"               # LLM calls
    TOOL = "TOOL"             # Tool calls
    RETRIEVER = "RETRIEVER"   # Document retrieval operations 
    EMBEDDING = "EMBEDDING"   # Embedding generation
    AGENT = "AGENT"           # Agent invocations (top-level spans)
    RERANKER = "RERANKER"     # Reranking operations
    GUARDRAIL = "GUARDRAIL"   # Guardrail checks
    EVALUATOR = "EVALUATOR"   # Evaluation operations
    HUMAN = "HUMAN"           # Human interactions (queries, feedback)
    PROCESSOR = "CHAIN"       # Data processing operations -> use CHAIN (general logic)
    UNKNOWN = "UNKNOWN"       # Default/unknown operations
    REFERENCES = "CHAIN"      # Document references/citations -> use CHAIN (general logic)

# Span attribute constants
class SpanAttributes:
    """Constants for span attribute names to ensure consistency."""
    # Session and request identifiers
    SESSION_ID = "session.id"  # Standard Phoenix attribute name for session tracking
    QA_ID = "qa_id"
    INPUT_VALUE = "input.value"
    CHAT_HISTORY_LENGTH = "chat_history_length"
    
    # Model and configuration
    LLM_MODEL = "llm_model"
    EMBEDDING_MODEL = "embedding.model"
    
    # Token count attributes (OpenInference standard for Phoenix UI)
    LLM_TOKEN_COUNT_PROMPT = "llm.token_count.prompt"
    LLM_TOKEN_COUNT_COMPLETION = "llm.token_count.completion"
    LLM_TOKEN_COUNT_TOTAL = "llm.token_count.total"
    RETRIEVAL_SEARCH_TYPE = "retrieval.search_type"
    RETRIEVAL_ALGORITHM = "retrieval.algorithm"
    RETRIEVAL_K = "retrieval.k"
    RETRIEVAL_SCORE_THRESHOLD = "retrieval.score_threshold"
    RETRIEVAL_FETCH_K = "retrieval.fetch_k"
    RETRIEVAL_CITATION_LIMIT = "retrieval.citation_limit"
    CHUNKING_SIZE = "chunking.size"
    CHUNKING_OVERLAP = "chunking.overlap"
    INDEX_NAME = "index.name"
    DATABASE_TYPE = "database.type"
    
    # Target configuration
    TEST_TARGET = "test_target"
    SYSTEM_PROMPT = "system_prompt"
    TEST_TARGET_PREFIX = "test_target."
    TARGET_ID = "target.id"
    TARGET_COMPOSITE = "test_target.is_composite"
    TARGET_COMPOSITE_LIST = "test_target.composite_targets"
    TARGET_MODEL = "test_target.model"
    TARGET_EMBEDDING_MODEL = "test_target.embedding_model"
    TARGET_SEARCH_TYPE = "test_target.search_type"
    TARGET_SEARCH_K = "test_target.search_k"
    TARGET_FETCH_K = "test_target.fetch_k"
    TARGET_CITATION_LIMIT = "test_target.citation_limit"
    TARGET_CHUNK_SIZE = "test_target.chunk_size"
    TARGET_CHUNK_OVERLAP = "test_target.chunk_overlap"
    TARGET_INDEX_NAME = "test_target.index_name"
    TARGET_DATABASE = "test_target.database"
    TARGET_ALGORITHM = "test_target.algorithm"
    TARGET_TEMPERATURE = "test_target.temperature"
    TARGET_MAX_TOKENS = "test_target.max_tokens"
    TARGET_FREQUENCY_PENALTY = "test_target.frequency_penalty"
    TARGET_PRESENCE_PENALTY = "test_target.presence_penalty"
    
    # Response metrics
    TIMESTAMP = "timestamp"
    RESPONSE_LENGTH = "response_length"
    DOCUMENT_COUNT = "document_count"
    FETCH_K = "fetch_k"
    CITATION_COUNT = "citation_count"
    CITATION_LIMIT = "citation_limit"
    CHUNK_COUNT = "chunk_count"
    OUTPUT = "output"  # Output for Phoenix UI display
    
    # Span kind attributes (for Phoenix compatibility)
    SPAN_KIND = "span_kind"          # General span kind attribute
    SPAN_TYPE = "type"               # Type indicator for Phoenix  
    OTEL_KIND = "otel.kind"          # OpenTelemetry kind attribute
    OPENINFERENCE_SPAN_KIND = "openinference.span.kind"  # OpenInference specific kind
    
    # Query analysis
    QUERY_FOCUS = "query_focus"
    DETECTED_CONTEXTS = "detected_contexts"
    METADATA_CONSTRAINTS = "metadata_constraints"
    IS_STREAMING = "is_streaming"
    REQUEST_STRUCTURED_CITATIONS = "request_structured_citations"
    
    # Environment
    PROJECT = "project"
    ENVIRONMENT = "environment"
    SERVICE = "service"
    TEST_TYPE = "test_type"
    
    # Feedback attributes
    FEEDBACK_ANSWER_RATING = "feedback.answer_rating"
    FEEDBACK_CITATIONS_RATING = "feedback.citations_rating"
    FEEDBACK_TEXT = "feedback_text"
    TARGET_SPAN_ID = "target_span_id"
    DOCUMENTS_BEFORE = "documents.before_processing"
    DOCUMENTS_AFTER = "documents.after_processing"

# Enhanced span operation names with proper namespacing
class SpanNames:
    """Constants for span names in the ATLAS application."""
    
    # Pipeline spans
    RAG_PIPELINE = "com.atlas.rag.pipeline"  # Root span for RAG process
    
    # Retrieval spans
    CONTEXT_RETRIEVAL = "com.atlas.rag.retrieval"  # Document retrieval operation
    DOCUMENT_REFERENCES = "com.atlas.rag.references"  # Citation/references formatting
    DOCUMENT_RERANKING = "com.atlas.rag.reranking"  # Document reranking operation
    DOCUMENT_FILTERING = "com.atlas.rag.filtering"  # Document filtering operation
    DOCUMENT_RANKING = "com.atlas.rag.ranking"  # Document ranking operation
    
    # Generation spans
    LLM_GENERATION = "com.atlas.rag.generation"  # LLM response generation
    STREAMING_RESPONSE = "com.atlas.rag.streaming"  # Text chunk streaming
    
    # User interaction spans
    HUMAN_QUERY = "com.atlas.user.query"  # Human query input
    FEEDBACK_ANNOTATION = "com.atlas.user.feedback"  # User feedback
    FEEDBACK_ANNOTATOR = "com.atlas.user.feedback.annotator"  # Feedback annotation span
    USER_FEEDBACK = "com.atlas.user.feedback"  # User feedback (alias)
    GENERATION = "com.atlas.rag.generation"
    STREAMING = "com.atlas.rag.streaming"
    CITATIONS = "com.atlas.rag.citations"  # Keep for backwards compatibility

# Test target configuration schema
TEST_TARGET_SCHEMA = {
    "id": {"type": str, "required": True},
    "model": {"type": str, "required": True},
    "embedding_model": {"type": str, "required": False},
    "retrieval": {
        "type": dict,
        "required": True,
        "schema": {
            "k": {"type": int, "required": True},
            "fetch_k": {"type": int, "required": True},
            "score_threshold": {"type": float, "required": False},
            "citation_limit": {"type": int, "required": False}
        }
    },
    "chunking": {
        "type": dict,
        "required": False,
        "schema": {
            "size": {"type": int, "required": False},
            "overlap": {"type": int, "required": False}
        }
    },
    "database": {
        "type": dict,
        "required": False,
        "schema": {
            "name": {"type": str, "required": False},
            "type": {"type": str, "required": False}
        }
    },
    "system_prompt": {"type": str, "required": False},
    "composite_id": {"type": str, "required": False}
}
