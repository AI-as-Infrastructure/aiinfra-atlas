# Tasks: Add Dynamic Corpus Filters from Manifest

## Prerequisites
- [x] Review current manifest.json structure
- [x] Identify all hardcoded corpus references in codebase
- [x] Review Darwin fork implementation for reference patterns

## Implementation Tasks

### Phase 1: Create Manifest Loader Module
- [x] **Task 1.1**: Create `backend/modules/manifest_loader.py` with module docstring
- [x] **Task 1.2**: Implement `load_manifest()` function with caching
- [x] **Task 1.3**: Implement `get_corpus_values()` to extract corpus IDs from manifest
- [x] **Task 1.4**: Implement `generate_corpus_label()` for label generation
- [x] **Task 1.5**: Implement `get_corpus_options()` to return formatted options list
- [x] **Task 1.6**: Add graceful fallback for missing/invalid manifest

### Phase 2: Update Retriever
- [x] **Task 2.1**: Update `backend/retrievers/hansard_retriever.py` imports
- [x] **Task 2.2**: Remove hardcoded `CORPUS_OPTIONS` constant
- [x] **Task 2.3**: Update `get_corpus_options()` method to use manifest_loader
- [x] **Task 2.4**: Update all hardcoded corpus ID lists in retrieval logic

### Phase 3: Update Config Module
- [x] **Task 3.1**: Update `backend/modules/config.py` imports
- [x] **Task 3.2**: Modify `_get_default_config()` to load corpus_options dynamically
- [x] **Task 3.3**: Remove hardcoded corpus_options from default config

### Phase 4: Update App Validation
- [x] **Task 4.1**: Already uses dynamic validation via `get_corpus_options()` in query.py router
- [x] **Task 4.2**: No additional changes needed (refactored in #57)

### Phase 5: Label Configuration
- [x] **Task 5.1**: Define label mapping for known corpus patterns (COUNTRY_CODES in manifest_loader.py)
- [x] **Task 5.2**: Support optional `labels` field in manifest.json (deferred - not needed for current use case)
- [x] **Task 5.3**: Label generation documented in manifest_loader.py docstrings

### Phase 6: Validation
- [x] **Task 6.1**: Run Python import check on all modified files
- [x] **Task 6.2**: Verify manifest loading works correctly (verified in production)
- [x] **Task 6.3**: Test API /api/config endpoint returns correct corpus options (verified in production)
- [x] **Task 6.4**: Test API /api/retriever/filters endpoint returns correct filters (verified in production)
- [x] **Task 6.5**: Test query with each corpus filter value (verified in production)
- [x] **Task 6.6**: Test behavior with missing manifest (verified - returns defaults)

## Verification Commands
```bash
# Check for syntax errors
python -m py_compile backend/modules/manifest_loader.py
python -m py_compile backend/modules/config.py
python -m py_compile backend/retrievers/hansard_retriever.py
python -m py_compile backend/app.py

# Check for import errors
python -c "from backend.modules.manifest_loader import get_corpus_options; print(get_corpus_options())"

# Verify manifest loading
python -c "from backend.modules.manifest_loader import load_manifest; import json; print(json.dumps(load_manifest().get('fields', {}).get('corpus', {}), indent=2))"

# Check no hardcoded corpus lists remain
grep -rn "1901_au.*1901_nz.*1901_uk" backend/ --include="*.py"
```

## Corpus Label Mapping Reference
```python
# Known country code mappings for label generation
COUNTRY_CODES = {
    "au": "Australia",
    "nz": "New Zealand",
    "uk": "United Kingdom",
    "ca": "Canada",
    "ie": "Ireland",
    "us": "United States"
}

# Pattern: {year}_{country_code} -> "{Country} ({year})"
# Example: "1901_au" -> "Australia (1901)"
```

## Rollback Plan
If issues arise:
1. Revert manifest_loader.py creation
2. Restore hardcoded CORPUS_OPTIONS in hansard_retriever.py
3. Restore hardcoded corpus_options in config.py
4. Restore hardcoded validation in app.py
