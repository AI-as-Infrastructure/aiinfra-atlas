# ATLAS Key Modules

The ATLAS backend is organized into modular components that handle different aspects of the RAG (Retrieval Augmented Generation) pipeline. This document explains the significance and functionality of the key modules that form the core architecture.

## Core Configuration Modules

### `backend/modules/config.py`

**Purpose**: Centralized configuration management system that provides strongly-typed, validated configuration loading from multiple sources.

**Key Responsibilities**:
- **Hierarchical Configuration Loading**: Loads configuration in order of precedence:
  1. Default configuration values
  2. Environment variables from `.env.{environment}` files
  3. Target-specific configuration files (`backend/targets/{target}.txt`)
- **Configuration Validation**: Type checking and schema validation for all configuration parameters
- **Retriever Initialization**: Manages the initialization and lifecycle of retriever instances
- **Typed Access Methods**: Provides strongly-typed getter methods for different configuration sections

**Key Functions**:
```python
initialize_config()           # Initialize configuration system
get_config()                 # Get complete configuration dictionary
get_retriever_config()       # Get retriever-specific configuration
get_llm_config()            # Get LLM provider and model configuration
get_system_prompt()         # Get the system prompt text
get_corpus_options()        # Get available corpus filtering options
get_citation_limit()        # Get citation display limit
```

**Integration Points**:
- Called by `app.py` during application startup
- Used by all modules that need configuration parameters
- Integrates with `base_target.py` for test target configuration
- Provides configuration to retriever and LLM modules

### `backend/modules/system_prompts.py`

**Purpose**: Manages system prompts and prompt templates for LLM interactions, providing modular prompt construction and conversation handling.

**Key Responsibilities**:
- **Modular Prompt Construction**: Builds system prompts from reusable components
- **Role and Task Definition**: Defines the AI assistant's expertise in 1901 parliamentary records
- **Citation Guidelines**: Provides instructions for evidence-based responses without manual citation markers
- **Template Generation**: Creates LangChain-compatible prompt templates for different conversation contexts
- **Multi-turn Conversation Support**: Handles context preservation across conversation turns

**Key Components**:
```python
# Prompt Components
ROLE_DEFINITION          # Defines AI expertise in parliamentary records
CORPUS_SELECTION        # Instructions for country-specific targeting
TASK_DEFINITION         # Response format and evidence requirements
CITATION_GUIDELINES     # Automatic citation handling instructions
EVIDENCE_HANDLING       # Rules for insufficient evidence scenarios
UNCERTAINTY_HANDLING    # Guidelines for expressing limitations

# Template Functions
get_qa_prompt_template()      # Standard prompt template for Q&A
get_qa_chat_prompt_template() # Chat-based template with message history
build_system_prompt()         # Customizable prompt builder
```

**Prompt Strategy**:
- **Evidence-Based Responses**: Requires grounding in provided source documents
- **Automatic Citation**: System handles citation generation without manual markers
- **Scope Limitation**: Restricts responses to 1901 parliamentary proceedings
- **Historical-Contemporary Comparisons**: Guidelines for making relevant modern connections
- **Direct Presentation**: Authoritative tone without unnecessary document access references

## LLM Integration Module

### `backend/modules/llm.py`

**Purpose**: Provides unified LLM integration with comprehensive telemetry instrumentation, supporting multiple providers and streaming responses.

**Key Responsibilities**:
- **Multi-Provider Support**: Unified interface for OpenAI, Anthropic, Google, AWS Bedrock, and Ollama
- **Streaming Response Generation**: Real-time response generation with chunk-by-chunk processing
- **Telemetry Integration**: Comprehensive tracking of LLM interactions, performance metrics, and caching
- **Prompt Optimization**: Integration with prompt caching for improved performance
- **Error Handling**: Robust error management with graceful degradation
- **Chat History Management**: Conversion between application and LangChain message formats

**Key Functions**:
```python
create_llm()                    # Create LLM instance for any provider
generate_response()             # Core response generation with streaming
generate_response_with_telemetry() # Full telemetry-instrumented response generation
format_documents()              # Convert document objects to context strings
format_chat_history()          # Convert chat history to LangChain messages
```

**Provider Support**:
- **OpenAI**: GPT-4, GPT-4o, GPT-4o-mini models
- **Anthropic**: Claude 3.7, Claude 4 models with prompt caching
- **Google**: Gemini 1.5, Gemini 2.0 models
- **AWS Bedrock**: Claude models via AWS infrastructure
- **Ollama**: Local LLM hosting support

**Telemetry Features**:
- **Performance Tracking**: Response time, chunk count, token usage
- **Cache Monitoring**: Prompt cache hit rates and efficiency metrics
- **Error Tracking**: Detailed error capture and recovery patterns
- **Session Linking**: Integration with Phoenix monitoring for end-to-end tracing

## Supporting Modules

### `backend/modules/document_retrieval.py`

**Purpose**: Handles document retrieval from vector stores with corpus filtering and telemetry.

**Key Features**:
- Vector similarity search with configurable parameters
- Corpus-specific filtering (Australia, New Zealand, UK, or all)
- Large retrieval operations for comprehensive document gathering
- Integration with telemetry for search performance tracking

### `backend/modules/corpus_filtering.py`

**Purpose**: Manages filtering of retrieved documents based on corpus metadata.

**Key Features**:
- Post-retrieval filtering based on corpus tags
- Support for single corpus or multi-corpus queries
- Metadata preservation during filtering operations
- Integration with citation generation systems

### `backend/modules/streaming.py`

**Purpose**: Provides utilities for Server-Sent Events (SSE) streaming responses.

**Key Features**:
- SSE message formatting for real-time communication
- Error message generation and transmission
- Response chunk processing and delivery
- WebSocket and HTTP streaming support

### `backend/modules/prompt_cache.py`

**Purpose**: Implements intelligent prompt caching to reduce API costs and improve response times.

**Key Features**:
- Provider-specific cache optimization (especially for Anthropic Claude)
- Token usage estimation and savings tracking
- Cache hit rate monitoring and statistics
- Universal caching strategy across all LLM providers

### `backend/modules/embeddings.py`

**Purpose**: Manages embedding model loading and document embedding operations.

**Key Features**:
- Sentence Transformer model management
- Embedding pooling strategies (mean, cls, mean+max)
- Model fine-tuning integration
- Vector dimension handling for different models

## Module Interactions and Architecture

### Configuration Flow
```
app.py → config.py → base_target.py → {target}.txt files
                  ↓
               retriever initialization
                  ↓
            system_prompts.py → llm.py
```

### Request Processing Flow
```
User Question → document_retrieval.py → corpus_filtering.py
                                     ↓
            system_prompts.py → llm.py → streaming.py → User Response
                              ↑
                         prompt_cache.py
```

### Telemetry Integration
All modules integrate with the telemetry system to provide:
- **Performance Metrics**: Response times, token usage, cache efficiency
- **Error Tracking**: Detailed error capture and recovery patterns
- **Usage Analytics**: Question patterns, corpus preferences, model performance
- **System Health**: Memory usage, concurrent user handling, rate limiting

## Development Guidelines

### Adding New Modules
1. **Follow the Pattern**: Use similar structure to existing modules with clear separation of concerns
2. **Configuration Integration**: Use `config.py` for any configurable parameters
3. **Telemetry Support**: Add appropriate telemetry instrumentation for monitoring
4. **Error Handling**: Implement comprehensive error handling with graceful degradation
5. **Type Hints**: Use comprehensive type hints for better IDE support and documentation

### Module Dependencies
- **Minimize Coupling**: Modules should depend on configuration and interfaces, not implementations
- **Avoid Circular Imports**: Use lazy imports or dependency injection when needed
- **Testing Support**: Design modules to be easily testable in isolation
- **Documentation**: Maintain clear docstrings and type annotations

### Performance Considerations
- **Caching**: Use appropriate caching strategies for expensive operations
- **Lazy Loading**: Initialize expensive resources only when needed
- **Memory Management**: Clean up resources properly, especially LLM instances
- **Async Support**: Consider async patterns for I/O bound operations

## Configuration Examples

### Environment-Specific Module Configuration
```bash
# Development - focus on debugging
BACKEND_LOG_LEVEL=debug
TELEMETRY_ENABLED=true
LLM_REQUEST_DELAY_MS=500

# Production - focus on performance
BACKEND_LOG_LEVEL=warn
PROMPT_CACHING_ENABLED=true
LLM_MAX_CONCURRENT=20
```

### Module-Specific Settings
```bash
# LLM module configuration
LLM_PROVIDER=ANTHROPIC
LLM_MODEL=claude-3-7-sonnet-20250219
LLM_REQUEST_DELAY_MS=1000

# System prompts configuration
SYSTEM_PROMPT_COMPONENTS=role,task,citations,evidence

# Caching configuration
PROMPT_CACHING_ENABLED=true
PROMPT_CACHE_TTL=5m
```

## Troubleshooting Common Issues

### Configuration Loading Problems
- **Missing Config Files**: Ensure target configuration files exist in `backend/targets/`
- **Environment Variables**: Verify environment variables are loaded correctly
- **Type Conversion**: Check for type conversion errors in configuration values

### LLM Integration Issues
- **API Keys**: Verify API keys are set and valid for the configured provider
- **Model Names**: Ensure model names match provider specifications
- **Rate Limiting**: Check for rate limit errors and adjust delay settings

### Module Import Errors
- **Circular Imports**: Use lazy imports or refactor dependencies
- **Missing Dependencies**: Ensure all required packages are installed
- **Path Issues**: Verify module paths are correct in import statements

---

The modular architecture of ATLAS provides flexibility for customization while maintaining clear separation of concerns. Each module has a specific role in the RAG pipeline, and their interactions are designed to be observable, configurable, and maintainable.