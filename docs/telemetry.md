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

## Privacy Controls

ATLAS provides three levels of telemetry control to balance observability needs with user privacy:

### 1. System-Wide Control (Administrator)

**Environment Variable**: `TELEMETRY_ENABLED`
- **Default**: `true`
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off`
- **Scope**: Affects all users and all telemetry operations
- **Purpose**: Allows system administrators to disable telemetry entirely

```bash
# Disable telemetry system-wide
export TELEMETRY_ENABLED=false

# Enable telemetry system-wide (default)
export TELEMETRY_ENABLED=true
```

When `TELEMETRY_ENABLED=false`, no telemetry data is collected or sent to Phoenix/Arize regardless of user preferences.

### 2. UI Control (Administrator)

**Environment Variable**: `VITE_TELEMETRY_ENABLED`
- **Default**: `true`
- **Values**: `true`, `false`
- **Scope**: Controls whether users can see and use the Privacy toggle
- **Purpose**: Allows administrators to hide privacy controls from users

```bash
# Hide privacy toggle from all users
export VITE_TELEMETRY_ENABLED=false

# Show privacy toggle to all users (default)
export VITE_TELEMETRY_ENABLED=true
```

This setting is copied to `frontend/.env` during build via `config/generate_vue_files.sh`.

### 3. Per-User Control (Individual Users)

**Interface**: Privacy toggle in the application UI
- **Default**: Off (telemetry enabled)
- **Scope**: Affects only the individual user's requests
- **Purpose**: Allows users to control their own data collection

**Privacy Toggle Behavior**:
- **Privacy "Off"**: User's data is collected and sent to Phoenix/Arize
- **Privacy "On"**: User's data is not collected or sent (privacy enabled)

### How Privacy Control Works

#### Frontend Implementation
1. **User Preference Storage**: Privacy setting stored in `localStorage` via Pinia store
2. **Header Control**: When privacy is enabled, no telemetry headers (`X-Trace-Id`, `X-Session-Id`, `X-QA-Id`) are sent
3. **Request Isolation**: Each user's preference only affects their own requests

#### Backend Implementation
1. **Middleware Detection**: Telemetry middleware checks for presence of `X-Trace-Id` header
2. **Context Variable**: Sets per-request context variable based on header presence
3. **Telemetry Gating**: All telemetry operations check context variable before proceeding

#### Technical Flow
```
User toggles Privacy "On"
    ↓
Frontend stops sending telemetry headers
    ↓
Backend middleware detects missing headers
    ↓
Context variable set to "user telemetry disabled"
    ↓
All telemetry operations become no-ops for this user
    ↓
No data sent to Phoenix/Arize for this user
```

### Control Hierarchy

The controls work in this hierarchy (each level can override the one below):

1. **System Admin** (`TELEMETRY_ENABLED=false`) → No telemetry for anyone
2. **UI Admin** (`VITE_TELEMETRY_ENABLED=false`) → Hide privacy controls from users
3. **Individual User** (Privacy toggle) → Personal data collection choice

### Examples

**Scenario 1: Full user control**
```bash
TELEMETRY_ENABLED=true
VITE_TELEMETRY_ENABLED=true
```
- Users see Privacy toggle
- Each user can independently enable/disable their telemetry
- Some users' data goes to Phoenix, others' doesn't

**Scenario 2: Admin wants telemetry for all users**
```bash
TELEMETRY_ENABLED=true
VITE_TELEMETRY_ENABLED=false
```
- Users don't see Privacy toggle
- All users' data goes to Phoenix/Arize
- Telemetry cannot be disabled by individual users

**Scenario 3: No telemetry at all**
```bash
TELEMETRY_ENABLED=false
VITE_TELEMETRY_ENABLED=true  # ignored
```
- No telemetry data collected from anyone
- Privacy toggle may be visible but has no effect
- System-wide override takes precedence

### Implementation Files

**Frontend Privacy Toggle**:
- `frontend/src/components/TelemetryToggle.vue` - Privacy toggle UI component
- `frontend/src/stores/preferences.js` - User preference management
- `frontend/src/stores/telemetry.js` - Telemetry header control

**Backend Privacy Enforcement**:
- `backend/telemetry/core.py` - Core telemetry control logic
- `backend/app.py` - Telemetry middleware implementation
- `backend/telemetry/api.py` - Feedback API privacy checks
