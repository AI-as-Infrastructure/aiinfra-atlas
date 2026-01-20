# Endpoint Modules Structure

## MODIFIED Requirements

### Requirement: Router-Based Endpoint Organization
The API endpoints MUST be organized into focused router modules under `backend/routers/`.

#### Scenario: Core Router Import
Given a file needs core API functionality
When it imports from the core router
Then `from backend.routers.core import router as core_router` provides the router

#### Scenario: Query Router Import
Given a file needs Q&A streaming functionality
When it imports from the query router
Then `from backend.routers.query import router as query_router` provides the router

#### Scenario: All Routers Included
Given the FastAPI application starts
When all routers are included
Then all API paths remain accessible at their original URLs

#### Scenario: No Circular Imports
Given all router modules are loaded
When the backend application starts
Then no circular import errors occur

### Requirement: LLM Resource Manager Extraction
The LLMResourceManager class MUST be moved to a dedicated service module.

#### Scenario: LLM Resource Manager Import
Given a router needs LLM resource management
When it imports from the service module
Then `from backend.services.llm_resource_manager import llm_resource_manager` provides the singleton

### Requirement: Dynamic Corpus Filter Validation
The corpus filter validation MUST use dynamic configuration instead of hardcoded values.

#### Scenario: Corpus Filter Validation
Given a query request includes a corpus_filter value
When the filter is validated
Then the validation uses `get_corpus_options()` from config instead of hardcoded list

### Requirement: Backward Compatibility
All existing API paths MUST continue to work with identical request/response formats.

#### Scenario: API Path Preservation
Given a client makes a request to `/api/ask/stream`
When the request is processed
Then the response format is identical to the pre-refactor behavior

#### Scenario: API Path Preservation for All Endpoints
Given any existing API endpoint is called
When the request is processed
Then the endpoint path, method, and response format are unchanged
