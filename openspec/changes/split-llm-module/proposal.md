# Proposal: Split LLM Module

## Change ID
`split-llm-module`

## Summary
Split the monolithic `backend/modules/llm.py` (859 lines) into two focused modules:
- `llm.py` - LLM creation and configuration utilities
- `response.py` - Response generation with streaming and telemetry

## Motivation
The current `llm.py` file combines two distinct concerns:
1. **LLM Setup** - Creating LLM instances, formatting documents/history, prompt templates
2. **Response Generation** - Streaming responses, telemetry instrumentation, error handling

This separation improves:
- **Maintainability**: Each module has a single responsibility
- **Testability**: Response generation logic can be tested independently
- **Readability**: Smaller, focused files are easier to navigate

## Scope

### In Scope
- Split `llm.py` at the `generate_response` function boundary
- Create new `backend/modules/response.py` module
- Update all imports across the codebase
- Maintain backward compatibility via re-exports if needed

### Out of Scope
- Functional changes to response generation logic
- Changes to the telemetry instrumentation
- API changes to existing functions

## Current State Analysis

### File Structure (llm.py - 859 lines)
```
Lines 1-37:    Imports and logger
Lines 38-63:   format_documents()
Lines 65-99:   format_chat_history()
Lines 101-205: create_llm()
Lines 207-260: create_qa_prompt()
----- SPLIT POINT -----
Lines 261-634: generate_response()
Lines 636-831: generate_response_with_telemetry()
Lines 833-839: _set_span_output_attributes()
Lines 840-859: _create_error_span()
```

### Current Import Dependencies
| File | Imports |
|------|---------|
| `backend/app.py` | `generate_response_with_telemetry` |
| `backend/services/llm_service.py` | `generate_response_with_telemetry` |
| `backend/services/validation_service.py` | `create_llm` |
| `backend/retrievers/hansard_retriever.py` | `create_llm` |
| `backend/retrievers/retriever_call_model.py` | `create_llm` |
| `create/txt/create_hansard_retriever.py` | `create_llm` |

## Proposed Solution

### New Module Structure
```
backend/modules/
├── llm.py              # LLM creation utilities (keep, ~260 lines)
│   ├── format_documents()
│   ├── format_chat_history()
│   ├── create_llm()
│   └── create_qa_prompt()
│
└── response.py         # Response generation (new, ~600 lines)
    ├── generate_response()
    ├── generate_response_with_telemetry()
    ├── _set_span_output_attributes()
    └── _create_error_span()
```

### Import Strategy
- `response.py` imports from `llm.py` (format_documents, format_chat_history, create_llm)
- Files using `generate_response_with_telemetry` update imports to `backend.modules.response`
- Files using `create_llm` continue importing from `backend.modules.llm`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports | Low | High | response.py imports from llm.py (one-way) |
| Missed import updates | Medium | Medium | Grep for all imports, test startup |
| Runtime errors | Low | High | Test all entry points after refactor |

## Related Issues
- GitHub Issue #52: Refactor /backend/modules/llm.py

## Acceptance Criteria
- [ ] `llm.py` contains only LLM creation utilities (~260 lines)
- [ ] `response.py` contains response generation functions (~600 lines)
- [ ] All existing imports updated and working
- [ ] Backend starts without import errors
- [ ] Existing functionality unchanged
