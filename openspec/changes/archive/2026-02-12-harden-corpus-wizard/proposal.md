# Harden Corpus Wizard Security, Complexity, and Performance

## Summary
Address critical security vulnerabilities, reduce code complexity, and fix performance bottlenecks in the corpus wizard feature branch before production deployment.

## Problem
A comprehensive assessment of the `feature/add-corpus-wizard` branch identified:

**Security (2 Critical, 3 High, 4 Medium):**
- Missing authentication on all configuration/build endpoints
- Path traversal vulnerabilities in source paths, target IDs, and GitHub URLs
- Environment file injection via unsanitized display names
- Sensitive error information leakage

**Complexity (4 Critical, 3 High):**
- 3,144 line monolithic Vue component (`CorpusWizard.vue`)
- 1,787 line router with 36 endpoints (`corpus_wizard.py`)
- Bare `except:` clauses and inconsistent error handling
- ~150 lines of duplicated target config generation
- Global state without encapsulation

**Performance (5 High, 2 Medium):**
- Blocking I/O operations in async contexts
- Unbounded memory accumulation for documents/chunks
- Fixed sleep delays wasting build time

## Solution
Implement a phased hardening approach prioritizing security fixes, then complexity reduction, then performance optimization.

### Phase 1: Critical Security Fixes (Must Have)
1. Add authentication dependency to configuration and corpus_wizard routers
2. Implement path validation utilities to prevent traversal attacks
3. Sanitize user input before writing to environment files
4. Replace detailed error messages with generic responses

### Phase 2: Code Quality Improvements (Should Have)
1. Extract `BuildProgressManager` class to encapsulate global state
2. Create shared validation utilities (regex, paths, target configs)
3. Fix bare `except:` clause and standardize error handling patterns
4. Extract target config generation to shared utility function

### Phase 3: Router Refactoring (Could Have)
1. Split `corpus_wizard.py` into domain-focused routers
2. Extract target management endpoints to separate router

### Phase 4: Performance Optimization (Future)
1. Use `asyncio.to_thread()` for blocking file operations
2. Implement streaming document processing
3. Replace fixed sleep delays with event-driven signaling

## Capabilities
- `api-security`: Authentication and authorization for wizard endpoints
- `input-validation`: Path traversal prevention and input sanitization
- `code-quality`: Error handling standardization and shared utilities

## Dependencies
- Existing authentication system (if any)
- `backend/routers/corpus_wizard.py`
- `backend/routers/configuration.py`
- `backend/modules/corpus_builder.py`
- `backend/modules/configuration_import.py`

## Risks & Mitigations
- **Risk**: Authentication breaks existing workflows
  - **Mitigation**: Add auth as optional dependency, enable via config flag
- **Risk**: Validation too strict, rejects valid inputs
  - **Mitigation**: Test with existing corpus configurations before deployment
- **Risk**: Refactoring introduces regressions
  - **Mitigation**: Extract utilities without changing behavior, add tests

## Technical Design

### Authentication (Using Existing Cognito)
Uses the existing `backend/modules/auth.py` which provides Cognito JWT validation:
- Toggle: `VITE_USE_COGNITO_AUTH=true` in environment
- Dependency: `get_current_user` from `backend.modules.auth`
- When disabled: returns anonymous user (allows local development)
- When enabled: validates JWT against AWS Cognito JWKS

```python
# Usage in routers
from backend.modules.auth import get_current_user

@router.post("/build")
async def build_corpus(user: dict = Depends(get_current_user)):
    logger.info(f"Build initiated by user: {user.get('username')}")
    ...
```

### Path Validation Utility
```python
# backend/modules/path_validator.py
from pathlib import Path
from urllib.parse import unquote

def validate_safe_path(user_path: str, allowed_base: Path) -> Path:
    """Validate path is within allowed directory."""
    # Decode URL encoding
    decoded = unquote(user_path)
    # Resolve to absolute, following symlinks
    resolved = Path(decoded).resolve()
    # Verify within bounds
    resolved.relative_to(allowed_base.resolve())
    return resolved

def validate_identifier(value: str, pattern: str = r'^[a-zA-Z0-9_-]+$') -> str:
    """Validate identifier matches safe pattern."""
    if not re.match(pattern, value):
        raise ValueError(f"Invalid identifier: {value}")
    return value
```

### Build Progress Manager
```python
# backend/modules/build_progress.py (refactored)
class BuildProgressManager:
    """Encapsulates build progress state."""

    def __init__(self):
        self._builds: Dict[str, BuildProgress] = {}
        self._lock = asyncio.Lock()

    async def start_build(self, build_id: str, config: dict) -> None: ...
    async def update_progress(self, build_id: str, data: dict) -> None: ...
    async def get_progress(self, build_id: str) -> Optional[BuildProgress]: ...
    async def mark_complete(self, build_id: str, success: bool) -> None: ...
```

### Standard Error Handler
```python
# backend/modules/error_handler.py
import logging

logger = logging.getLogger(__name__)

def safe_http_error(e: Exception, user_message: str, status_code: int = 400):
    """Log detailed error, return generic message."""
    logger.error(f"{user_message}: {e}", exc_info=True)
    raise HTTPException(status_code=status_code, detail=user_message)
```

## Validation
- Security: Penetration testing for path traversal, auth bypass
- Code quality: Static analysis for exception handling patterns
- Performance: Load testing with large corpus builds
- Regression: Existing corpus wizard workflow tests pass

## Implementation Order
1. Create path validation utility module
2. Add authentication dependency (configurable)
3. Apply path validation to all user-controlled paths
4. Sanitize environment file writes
5. Extract BuildProgressManager class
6. Create shared target config generator
7. Fix bare except and standardize error handling
8. Add unit tests for new utilities
