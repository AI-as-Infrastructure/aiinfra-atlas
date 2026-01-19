# Tasks: Split LLM Module

## Prerequisites
- [ ] Review current llm.py structure and dependencies
- [ ] Identify all files importing from llm.py

## Implementation Tasks

### Phase 1: Create New Module
- [ ] **Task 1.1**: Create `backend/modules/response.py` with module docstring and imports
- [ ] **Task 1.2**: Move `generate_response()` function to response.py
- [ ] **Task 1.3**: Move `generate_response_with_telemetry()` function to response.py
- [ ] **Task 1.4**: Move `_set_span_output_attributes()` helper to response.py
- [ ] **Task 1.5**: Move `_create_error_span()` helper to response.py

### Phase 2: Update Imports in response.py
- [ ] **Task 2.1**: Add imports from llm.py (format_documents, format_chat_history, create_llm)
- [ ] **Task 2.2**: Add remaining required imports (telemetry, langchain, etc.)
- [ ] **Task 2.3**: Verify no circular import issues

### Phase 3: Clean Up llm.py
- [ ] **Task 3.1**: Remove moved functions from llm.py
- [ ] **Task 3.2**: Remove unused imports from llm.py
- [ ] **Task 3.3**: Update module docstring to reflect new scope

### Phase 4: Update Consumer Imports
- [ ] **Task 4.1**: Update `backend/app.py` - change import to `from backend.modules.response import generate_response_with_telemetry`
- [ ] **Task 4.2**: Update `backend/services/llm_service.py` - change import to `from backend.modules.response import generate_response_with_telemetry`

### Phase 5: Validation
- [ ] **Task 5.1**: Run Python import check on all modified files
- [ ] **Task 5.2**: Start backend server and verify no import errors
- [ ] **Task 5.3**: Test a basic query to verify response generation works
- [ ] **Task 5.4**: Verify telemetry spans are still created correctly

## Verification Commands
```bash
# Check for syntax errors
python -m py_compile backend/modules/llm.py
python -m py_compile backend/modules/response.py

# Check for import errors
python -c "from backend.modules.llm import create_llm, format_documents"
python -c "from backend.modules.response import generate_response_with_telemetry"

# Verify no circular imports
python -c "from backend.app import app"
```

## Rollback Plan
If issues arise:
1. Revert response.py creation
2. Restore original llm.py from git
3. Revert import changes in app.py and llm_service.py
