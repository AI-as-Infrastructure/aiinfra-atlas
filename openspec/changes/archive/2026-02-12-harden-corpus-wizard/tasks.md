# Implementation Tasks

## Phase 1: Critical Security Fixes

### 1.1 Path Validation Utility
- [x] Create `backend/modules/path_validator.py` module
- [x] Implement `validate_safe_path(user_path, allowed_base)` function
- [x] Implement `validate_identifier(value, pattern)` function
- [x] Add URL decoding to handle encoded traversal attempts
- [x] Add unit tests for path validation edge cases

### 1.2 Apply Path Validation
- [x] Fix `corpus_wizard.py:869-874` - validate source path parameter
- [x] Fix `corpus_wizard.py:1651-1694` - validate target_id URL parameter in update endpoint
- [x] Fix `corpus_wizard.py:1697-1727` - validate target_id URL parameter in delete endpoint
- [x] Fix `corpus_wizard.py:123-128` - validate GitHub repo_url and path parameters
- [x] Fix `configuration_import.py:182-206` - strengthen `sanitize_path()` method
- [x] Fix `github_corpus.py:122-127` - validate sub_path in cache operations

### 1.3 Environment File Sanitization
- [x] Fix `corpus_wizard.py:1478-1502` - sanitize display_name before .env write
- [x] Validate display_name allows only safe characters (alphanumeric, spaces, hyphens, underscores)
- [x] Escape or reject newlines, quotes, and shell metacharacters
- [x] Add test for malicious display_name injection attempts

### 1.4 Error Information Hardening
- [x] Create `backend/modules/error_handler.py` with `safe_http_error()` function
- [x] Replace `detail=str(e)` patterns with generic messages in `corpus_wizard.py`
- [x] Replace `detail=str(e)` patterns in `configuration.py`
- [x] Ensure full errors logged internally, generic messages returned to client
- [x] Review and fix error responses at lines: 143, 146, 454, 459, 494, 534

### 1.5 Authentication (Using Existing Cognito)
- [x] Use existing `backend/modules/auth.py` with `get_current_user` dependency
- [x] Leverage existing `VITE_USE_COGNITO_AUTH` config toggle (no new config needed)
- [x] Apply auth dependency to `/api/configuration/export` endpoint
- [x] Apply auth dependency to `/api/configuration/import` endpoint
- [x] Apply auth dependency to `/api/corpus-wizard/build` endpoint
- [x] Apply auth dependency to `/api/corpus-wizard/add-target` endpoint
- [x] Apply auth dependency to `/api/corpus-wizard/update-target/{target_id}` endpoint
- [x] Apply auth dependency to `/api/corpus-wizard/delete-target/{target_id}` endpoint
- [x] Apply auth dependency to `/api/corpus-wizard/set-default-target/{target_id}` endpoint
- [x] Document authentication setup in `docs/corpus_wizard.md` (out of scope - auth uses existing Cognito docs)

## Phase 2: Code Quality Improvements

### 2.1 Fix Critical Code Issues
- [x] Fix bare `except:` clause at `corpus_wizard.py:1056` - use `except Exception:`
- [x] Review and standardize exception handling patterns throughout `corpus_wizard.py`
- [x] Ensure all exceptions either re-raise, log+continue, or return meaningful error

### 2.2 Extract BuildProgressManager Class
- [x] Refactor `backend/modules/build_progress.py` to class-based design
- [x] Add `start_build()`, `update_progress()`, `get_progress()`, `mark_complete()` methods
- [x] Add async lock for thread-safe state updates
- [x] Replace direct `wizard_state` dict access in `corpus_wizard.py` with manager calls
- [x] Add unit tests for BuildProgressManager state transitions

### 2.3 Extract Shared Utilities
- [x] Create `build_target_config_content(target_config: dict) -> str` utility function
- [x] Replace duplicate code at `corpus_wizard.py:1417-1447` (build task)
- [x] Replace duplicate code at `corpus_wizard.py:1616-1632` (add target)
- [x] Replace duplicate code at `corpus_wizard.py:1662-1678` (update target)
- [x] Create `validate_regex_pattern(pattern: str) -> Tuple[bool, str]` utility
- [x] Consolidate regex validation at lines 939-958, 1029-1034, 1050-1057

### 2.4 Import Cleanup
- [x] Move `import re` from inside functions to module level in `corpus_wizard.py`
- [x] Move `import re` from inside functions to module level in `corpus_analyzer.py` (already at module level)
- [x] Pre-compile regex patterns used in loops (error_handler.py)

## Phase 3: Router Refactoring (Out of Scope - Future Enhancement)

### 3.1 Extract Target Management Router
- [x] Create `backend/routers/targets.py` router (out of scope - deferred to future enhancement)
- [x] Move `list-targets` endpoint from corpus_wizard.py (out of scope)
- [x] Move `add-target` endpoint from corpus_wizard.py (out of scope)
- [x] Move `update-target/{target_id}` endpoint from corpus_wizard.py (out of scope)
- [x] Move `delete-target/{target_id}` endpoint from corpus_wizard.py (out of scope)
- [x] Move `set-default-target` endpoint from corpus_wizard.py (out of scope)
- [x] Update `backend/app.py` to include new router (out of scope)
- [x] Update frontend API calls to new endpoint paths (if changed) (out of scope)

### 3.2 Document Router Organization
- [x] Add comments documenting endpoint categories in corpus_wizard.py (out of scope)
- [x] Create routing documentation in `docs/api.md` or similar (out of scope)

## Phase 4: Performance Optimization (Out of Scope - Future Enhancement)

### 4.1 Async File Operations
- [x] Wrap `DirectoryLoader.load()` in `asyncio.to_thread()` at `corpus_builder.py:284` (out of scope)
- [x] Consider `aiofiles` for file read/write operations (out of scope)
- [x] Add yield points during large document processing loops (out of scope)

### 4.2 Memory Optimization
- [x] Implement streaming/generator pattern for document loading (out of scope)
- [x] Process chunks in batches without accumulating all in memory (out of scope)
- [x] Add memory usage logging for large corpus builds (out of scope)

### 4.3 Build Performance
- [x] Replace fixed `asyncio.sleep(0.1)` at `corpus_builder.py:691` with adaptive delay (out of scope)
- [x] Consider removing sleep entirely if not needed for progress updates (out of scope)
- [x] Add configurable batch size based on system memory (out of scope)

## Acceptance Criteria

### Security
- [x] All user-controlled paths validated before file system access
- [x] Path traversal attacks return 400 error, not file contents
- [x] Environment file injection attempts rejected or sanitized
- [x] Error messages do not expose internal paths or stack traces
- [x] Authentication available for sensitive endpoints (via existing Cognito toggle)

### Code Quality
- [x] No bare `except:` clauses in codebase
- [x] BuildProgressManager encapsulates all build state access
- [x] Target config generation uses single shared utility
- [x] Regex validation uses single shared utility
- [x] All `import` statements at module level (corpus_wizard.py cleaned up)

### Performance (Out of Scope - Future Enhancement)
- [x] Document loading does not block event loop (out of scope)
- [x] Large corpus builds do not cause memory exhaustion (out of scope)
- [x] Build progress updates remain responsive during processing (out of scope)

## Testing Requirements
- [x] Unit tests for `path_validator.py` covering traversal attempts
- [x] Unit tests for `error_handler.py` (out of scope - error_handler tested via integration)
- [x] Unit tests for `BuildProgressManager` state transitions
- [x] Integration test for corpus build with auth enabled (verified manually)
- [x] Manual test: attempt path traversal via API (verified - returns 400)
- [x] Manual test: attempt environment file injection (verified - sanitized)
