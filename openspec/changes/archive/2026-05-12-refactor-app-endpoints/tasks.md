# Tasks: Refactor app.py into Endpoint Modules

## Prerequisites
- [x] Review current app.py structure and endpoint groupings
- [x] Identify all shared dependencies between endpoints
- [x] Verify existing telemetry_router pattern for reference

## Implementation Tasks

### Phase 1: Setup Infrastructure
- [x] **Task 1.1**: Create `backend/routers/__init__.py`
- [x] **Task 1.2**: Create `backend/services/llm_resource_manager.py` with LLMResourceManager class
- [x] **Task 1.3**: Update imports in app.py to use new LLMResourceManager location

### Phase 2: Extract Core Router
- [x] **Task 2.1**: Create `backend/routers/core.py` with router setup
- [x] **Task 2.2**: Move `GET /` (root health check) to core router
- [x] **Task 2.3**: Move `GET /api/health` to core router
- [x] **Task 2.4**: Move `GET /api/config` to core router
- [x] **Task 2.5**: Move `GET /api/telemetry` to core router
- [x] **Task 2.6**: Move `GET /api/diagnostics` to core router
- [x] **Task 2.7**: Move `GET /api/debug/user-id` to core router
- [x] **Task 2.8**: Include core router in app.py

### Phase 3: Extract Query Router
- [x] **Task 3.1**: Create `backend/routers/query.py` with router setup
- [x] **Task 3.2**: Move `POST /api/ask/stream` to query router
- [x] **Task 3.3**: Move `POST /api/ask/async` to query router
- [x] **Task 3.4**: Move `GET /api/ask/async/{request_id}` to query router
- [x] **Task 3.5**: Include query router in app.py
- [x] **Task 3.6**: Fix hardcoded corpus filter - use `get_corpus_options()` instead

### Phase 4: Extract Feedback Router
- [x] **Task 4.1**: Create `backend/routers/feedback.py` with router setup
- [x] **Task 4.2**: Move `POST /api/feedback` to feedback router
- [x] **Task 4.3**: Include feedback router in app.py

### Phase 5: Extract Validation Router
- [x] **Task 5.1**: Create `backend/routers/validation.py` with router setup
- [x] **Task 5.2**: Move `POST /api/validate_session` to validation router
- [x] **Task 5.3**: Move `GET /api/validate_config` to validation router
- [x] **Task 5.4**: Move ValidationRequest/ValidationResponse models to validation router
- [x] **Task 5.5**: Include validation router in app.py

### Phase 6: Extract Cache Router
- [x] **Task 6.1**: Create `backend/routers/cache.py` with router setup
- [x] **Task 6.2**: Move `GET /api/cache/stats` to cache router
- [x] **Task 6.3**: Move `POST /api/cache/clear` to cache router
- [x] **Task 6.4**: Include cache router in app.py

### Phase 7: Extract Queue Router
- [x] **Task 7.1**: Create `backend/routers/queue.py` with router setup
- [x] **Task 7.2**: Move `GET /api/queue/stats` to queue router
- [x] **Task 7.3**: Include queue router in app.py

### Phase 8: Extract Inter-Rater Router
- [x] **Task 8.1**: Create `backend/routers/inter_rater.py` with router setup
- [x] **Task 8.2**: Move `GET /api/inter-rater/sessions` to inter_rater router
- [x] **Task 8.3**: Move `GET /api/inter-rater/stats` to inter_rater router
- [x] **Task 8.4**: Move `POST /api/inter-rater/refresh-cache` to inter_rater router
- [x] **Task 8.5**: Include inter_rater router in app.py

### Phase 9: Extract Retriever Router
- [x] **Task 9.1**: Create `backend/routers/retriever.py` with router setup
- [x] **Task 9.2**: Move `GET /api/retriever/filters` to retriever router
- [x] **Task 9.3**: Move `GET /api/vector-store-info` to retriever router
- [x] **Task 9.4**: Include retriever router in app.py

### Phase 10: Clean Up app.py
- [x] **Task 10.1**: Remove all moved endpoint functions from app.py
- [x] **Task 10.2**: Remove unused imports from app.py
- [x] **Task 10.3**: Update module docstring to reflect new structure
- [x] **Task 10.4**: Verify app.py is ~200 lines or less

### Phase 11: Validation
- [x] **Task 11.1**: Run Python import check on all router files
- [x] **Task 11.2**: Start backend server and verify no import errors
- [x] **Task 11.3**: Test each endpoint category:
  - [x] Core endpoints (health, config, diagnostics)
  - [x] Query endpoints (ask/stream, ask/async)
  - [x] Feedback endpoint
  - [x] Validation endpoints
  - [x] Cache endpoints
  - [x] Queue endpoints
  - [x] Inter-rater endpoints
  - [x] Retriever endpoints
- [x] **Task 11.4**: Verify all API paths remain unchanged

## Verification Commands
```bash
# Check for syntax errors
python -m py_compile backend/app.py
python -m py_compile backend/routers/core.py
python -m py_compile backend/routers/query.py
python -m py_compile backend/routers/feedback.py
python -m py_compile backend/routers/validation.py
python -m py_compile backend/routers/cache.py
python -m py_compile backend/routers/queue.py
python -m py_compile backend/routers/inter_rater.py
python -m py_compile backend/routers/retriever.py
python -m py_compile backend/services/llm_resource_manager.py

# Check for import errors
python -c "from backend.app import app"

# Verify all routes are registered
python -c "from backend.app import app; print([r.path for r in app.routes])"
```

## Rollback Plan
If issues arise:
1. Revert all router files
2. Restore original app.py from git
3. Revert llm_resource_manager.py changes
