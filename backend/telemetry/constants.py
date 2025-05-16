"""
Telemetry constants for Phoenix Arize integration.

This module centralizes all constants used in telemetry to ensure consistency
across the application.
"""

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
    PROCESSOR = "PROCESSOR"   # Data processing operations
    UNKNOWN = "UNKNOWN"       # Default/unknown operations

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

# Enhanced span operation names with proper namespacing
class SpanNames:
    """Consistent name constants for span operations"""
    # HTTP method-based names
    HTTP_GET_CONFIG = "http.GET.api.config"
    HTTP_POST_ASK = "http.POST.api.ask"
    HTTP_POST_ASK_STREAM = "http.POST.api.ask.stream"
    HTTP_POST_FEEDBACK = "http.POST.api.feedback"
    
    # Top-level RAG pipeline operation
    RAG_PIPELINE = "com.atlas.rag.pipeline"
    
    # RAG pipeline phases with more specific naming
    QUESTION_REFORMULATION = "com.atlas.rag.question_reformulation"
    CONTEXT_RETRIEVAL = "com.atlas.rag.context_retrieval"
    DOCUMENT_FILTERING = "com.atlas.rag.document_filtering"
    DOCUMENT_RANKING = "com.atlas.rag.document_ranking"
    PROMPT_GENERATION = "com.atlas.rag.prompt_generation"
    LLM_GENERATION = "com.atlas.rag.llm_generation"
    CITATION_FORMATTING = "com.atlas.rag.citation_formatting"
    STREAMING_RESPONSE = "com.atlas.rag.streaming_response"
    DOCUMENT_REFERENCES = "com.atlas.rag.document_references"
    
    # Feedback operations
    FEEDBACK_PROCESSING = "com.atlas.feedback.processing"
    FEEDBACK_ANNOTATION = "com.atlas.feedback.annotation"
    
    # Session operations
    SESSION_CONFIGURATION = "com.atlas.session.configuration"

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
