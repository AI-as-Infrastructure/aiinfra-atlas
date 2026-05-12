# Proposal: Refactor app.py into Endpoint Modules

## Change ID
`refactor-app-endpoints`

## Summary
Split the monolithic `backend/app.py` (1565 lines) into focused endpoint modules using FastAPI routers, following the same pattern as the existing `telemetry_router`.

## Motivation
The current `app.py` file combines:
1. **Application initialization** - Environment loading, telemetry, middleware
2. **Resource management** - LLMResourceManager class
3. **20+ API endpoints** - Mixed concerns across Q&A, feedback, validation, admin, etc.

This separation improves:
- **Maintainability**: Each router handles a single domain
- **Testability**: Endpoints can be tested in isolation
- **Readability**: Smaller, focused files are easier to navigate
- **Collaboration**: Multiple developers can work on different routers

## Scope

### In Scope
- Create `backend/routers/` directory with focused router modules
- Move endpoint handlers from `app.py` to appropriate routers
- Keep `app.py` as the application entry point (initialization, middleware, router includes)
- Move `LLMResourceManager` to a dedicated module
- Address hardcoded corpus filter values (externalize to config)

### Out of Scope
- Functional changes to endpoint logic
- Changes to request/response schemas
- Changes to middleware behavior
- API versioning (future enhancement)

## Current State Analysis

### File Structure (app.py - 1565 lines)
```
Lines 1-200:    Initialization (env, telemetry, imports, middleware)
Lines 205-339:  LLMResourceManager class
Lines 345-349:  GET / (health check)
Lines 352-396:  GET /api/config
Lines 400-444:  GET /api/retriever/filters
Lines 448-503:  GET /api/debug/user-id
Lines 507-767:  POST /api/ask/stream (261 lines - largest endpoint!)
Lines 770-773:  GET /api/telemetry
Lines 776-830:  GET /api/diagnostics
Lines 832-880:  GET /api/cache/stats
Lines 882-931:  POST /api/cache/clear
Lines 936-1094: POST /api/feedback (159 lines)
Lines 1097-1183: POST /api/validate_session
Lines 1186-1191: GET /api/validate_config
Lines 1193-1230: Security middleware (HTTPS, TrustedHost)
Lines 1233-1240: GET /api/health, uvicorn entrypoint
Lines 1244-1281: POST /api/ask/async
Lines 1283-1307: GET /api/ask/async/{request_id}
Lines 1309-1332: GET /api/queue/stats
Lines 1337-1373: GET /api/inter-rater/sessions
Lines 1375-1411: GET /api/inter-rater/stats
Lines 1413-1458: POST /api/inter-rater/refresh-cache
Lines 1460-1565: GET /api/vector-store-info
```

### Hardcoded Values Identified
- Line 531: `if corpus_filter not in ["all", "1901_au", "1901_nz", "1901_uk"]:` - should use `get_corpus_options()`

## Proposed Solution

### New Module Structure
```
backend/
├── app.py                    # Entry point (~200 lines)
│   ├── Environment loading
│   ├── Telemetry initialization
│   ├── FastAPI app creation
│   ├── Middleware configuration
│   └── Router includes
│
├── routers/
│   ├── __init__.py
│   ├── core.py              # Health, config, diagnostics (~150 lines)
│   ├── query.py             # /api/ask/* endpoints (~350 lines)
│   ├── feedback.py          # /api/feedback endpoint (~180 lines)
│   ├── validation.py        # /api/validate_* endpoints (~120 lines)
│   ├── cache.py             # /api/cache/* endpoints (~120 lines)
│   ├── queue.py             # /api/queue/* endpoints (~50 lines)
│   ├── inter_rater.py       # /api/inter-rater/* endpoints (~150 lines)
│   └── retriever.py         # /api/retriever/*, vector-store-info (~150 lines)
│
└── services/
    └── llm_resource_manager.py  # LLMResourceManager class (~150 lines)
```

### Router Groupings

| Router | Endpoints | Purpose |
|--------|-----------|---------|
| `core` | `/`, `/api/health`, `/api/config`, `/api/diagnostics`, `/api/telemetry`, `/api/debug/user-id` | Core app health and configuration |
| `query` | `/api/ask/stream`, `/api/ask/async`, `/api/ask/async/{id}` | Q&A functionality |
| `feedback` | `/api/feedback` | User feedback submission |
| `validation` | `/api/validate_session`, `/api/validate_config` | Session validation |
| `cache` | `/api/cache/stats`, `/api/cache/clear` | Prompt cache management |
| `queue` | `/api/queue/stats` | Async queue statistics |
| `inter_rater` | `/api/inter-rater/*` | Inter-rater reliability |
| `retriever` | `/api/retriever/filters`, `/api/vector-store-info` | Retriever configuration |

### Shared Dependencies
The `llm_resource_manager` will be moved to `backend/services/llm_resource_manager.py` and imported by routers that need it (primarily `query.py`).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports | Medium | High | Careful dependency ordering, shared modules |
| Missed endpoint moves | Low | Medium | Grep for all @app decorators, test all routes |
| Broken imports | Medium | Medium | Test startup after each router extraction |
| Runtime errors | Low | High | Test all endpoints after refactor |

## Related Issues
- GitHub Issue #57: Refactor app.py

## Acceptance Criteria
- [ ] `app.py` reduced to ~200 lines (initialization and router includes only)
- [ ] All endpoints accessible via same paths as before
- [ ] `LLMResourceManager` moved to dedicated service module
- [ ] Hardcoded corpus filter replaced with `get_corpus_options()`
- [ ] Backend starts without import errors
- [ ] All existing API functionality unchanged
