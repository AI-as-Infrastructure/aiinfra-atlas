# ATLAS Telemetry System

This document provides an overview of the telemetry system used in ATLAS, which is built on top of OpenTelemetry and integrates with Phoenix Arize for observability.

## Core Telemetry Files

### `backend/telemetry/core.py`

The foundation of all telemetry operations in ATLAS:

- Initializes the telemetry system with Phoenix Arize
- Provides the `create_span` function which is the basis for all span creation
- Manages trace context propagation and extraction
- Handles session management via the `using_session` context manager
- Contains utilities for span lookup and validation

### `backend/telemetry/spans.py`

Specialized span creation for different parts of the application:

- Provides context managers for creating spans for specific operations
- Implements `register_span` and `find_qa_span_id` for feedback association
- Manages span registry to associate feedback with the correct spans
- Contains helper functions to add test target attributes to spans
- Provides specialized span kinds for LLM, retriever, reranker operations

### `backend/telemetry/feedback.py`

Handles user feedback collection and association:

- Defines `UserFeedback` Pydantic model for validation
- Implements `log_user_feedback` function to record feedback
- Contains `submit_span_annotation` for sending feedback to Phoenix
- Converts numeric ratings to descriptive labels
- Associates feedback with the appropriate span via span registry

### `backend/telemetry/constants.py`

Centralizes constants used in telemetry:

- Defines `OpenInferenceSpanKind` for proper span categorization
- Contains `SpanAttributes` constants for consistent attribute naming
- Defines `SpanNames` for consistent operation naming
- Includes schema definitions for test target configuration

### `backend/telemetry/config_attrs.py`

Helps gather and format test target configuration:

- Extracts configuration from test target modules
- Formats attributes in a way compatible with OpenTelemetry
- Provides a flattened attribute structure for better visibility

## Telemetry Integration

### In Document Operations

The document retrieval and reranking modules demonstrate proper telemetry integration:

- `backend/modules/document_retrieval.py` provides telemetry for retrieval operations
- `backend/modules/document_reranking.py` demonstrates telemetry for reranking
- Both use a standardized structure with description, input/output counts, etc.

### In Application Endpoints

The main application endpoints integrate telemetry:

- `backend/app.py` creates parent spans for the RAG pipeline
- Properly links child spans (retrieval, reranking, generation) to parent
- Ensures consistent attribute structure across all spans
- Associates feedback with the root span for complete observability

## Telemetry Best Practices

When implementing telemetry in ATLAS components:

1. **Use meaningful span names**: Follow the naming patterns in `SpanNames`.
2. **Standardize attributes**: Include these in each span:
   - Description field for clarity
   - Input/output document counts
   - Session and QA IDs
   - Structured attributes in nested format
3. **Ensure span linkage**: Properly link child spans to parents.
4. **Handle errors**: Record exceptions in spans when they occur.
5. **Add contextual information**: Include relevant operation-specific details.

## Viewing Telemetry Data

Telemetry data is sent to Phoenix Arize, where you can:

- View RAG pipeline traces
- See document operations in detail
- Analyze LLM generation details
- Review user feedback
- Identify performance bottlenecks

For access to the Phoenix dashboard, contact the team administrator.
