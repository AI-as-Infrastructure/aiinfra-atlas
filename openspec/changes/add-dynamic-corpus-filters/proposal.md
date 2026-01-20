# Proposal: Add Dynamic Corpus Filters from Manifest

## Change ID
`add-dynamic-corpus-filters`

## Summary
Replace hardcoded corpus filter options with dynamic generation from `manifest.json`, making it easier to add new corpora without code changes.

## Motivation
Currently, corpus options are hardcoded in three locations:
1. `backend/retrievers/hansard_retriever.py` (lines 19-24) - `CORPUS_OPTIONS` constant
2. `backend/modules/config.py` (lines 85-102) - `corpus_options` in default config
3. `backend/app.py` (line 531) - hardcoded validation list

This means adding a new corpus requires:
1. Updating the vector store with new documents
2. Regenerating `manifest.json` (which already contains corpus info)
3. Manually editing three Python files to add the new corpus

With dynamic corpus filters, steps 2 and 3 are eliminated - the system automatically reads available corpora from the manifest.

## Scope

### In Scope
- Create utility to read corpus options from `manifest.json`
- Update `hansard_retriever.py` to use dynamic corpus options
- Update `config.py` to load corpus options from manifest
- Update `app.py` to validate corpus filter against dynamic options
- Support configurable corpus labels (via manifest or convention)
- Maintain "all" option as the default

### Out of Scope
- Changes to manifest.json schema (already has required data)
- Changes to vector store creation process
- Frontend changes (API response format unchanged)
- Redis configuration fixes (separate concern)

## Current State Analysis

### Hardcoded Corpus Options

**Location 1: `backend/retrievers/hansard_retriever.py:19-24`**
```python
CORPUS_OPTIONS = [
    {"value": "all", "label": "All Collections"},
    {"value": "1901_au", "label": "Australia (1901)"},
    {"value": "1901_nz", "label": "New Zealand (1901)"},
    {"value": "1901_uk", "label": "United Kingdom (1901)"}
]
```

**Location 2: `backend/modules/config.py:85-102`**
```python
"corpus_options": [
    {"value": "all", "label": "All Collections"},
    {"value": "1901_au", "label": "Australia (1901)", ...},
    {"value": "1901_nz", "label": "New Zealand (1901)", ...},
    {"value": "1901_uk", "label": "United Kingdom (1901)", ...}
]
```

**Location 3: `backend/app.py:531`**
```python
if corpus_filter not in ["all", "1901_au", "1901_nz", "1901_uk"]:
    corpus_filter = "all"
```

### Available Data in `manifest.json`
```json
{
  "fields": {
    "corpus": {
      "type": "enum",
      "values": ["1901_au", "1901_nz", "1901_uk"]
    }
  },
  "stats": {
    "corpora": {
      "1901_au": {"files": 113, "chunks": 40756, ...},
      "1901_nz": {"files": 62, "chunks": 23503, ...},
      "1901_uk": {"files": 31, "chunks": 30677, ...}
    }
  }
}
```

## Proposed Solution

### New Module: `backend/modules/manifest_loader.py`
```python
def load_manifest() -> Dict[str, Any]:
    """Load and cache manifest.json."""

def get_corpus_values() -> List[str]:
    """Get list of valid corpus IDs from manifest."""

def get_corpus_options() -> List[Dict[str, str]]:
    """Generate corpus options with labels from manifest."""

def generate_corpus_label(corpus_id: str) -> str:
    """Generate human-readable label from corpus ID."""
    # e.g., "1901_au" -> "Australia (1901)"
```

### Label Generation Strategy
1. **Convention-based**: Parse corpus ID pattern (e.g., `{year}_{country_code}`)
2. **Manifest-based**: Optional `labels` field in manifest.json
3. **Fallback**: Use corpus ID as label if no pattern matches

### Updated Flow
```
manifest.json
     │
     ▼
manifest_loader.py
     │
     ├──► config.py (corpus_options loaded dynamically)
     │
     ├──► hansard_retriever.py (get_corpus_options() uses manifest)
     │
     └──► app.py (validation uses get_corpus_options())
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missing manifest.json | Low | High | Graceful fallback to empty list with warning |
| Invalid manifest format | Low | Medium | Validate schema on load, fallback to defaults |
| Performance (file reads) | Low | Low | Cache manifest after first load |
| Label generation errors | Medium | Low | Fallback to corpus ID as label |

## Related Issues
- GitHub Issue #44: Cherry-pick composite config improvements from Darwin fork
- Darwin fork v0.2.0 improvements

## Acceptance Criteria
- [ ] Corpus options loaded dynamically from `manifest.json`
- [ ] No hardcoded corpus lists in Python files
- [ ] Adding new corpus requires only manifest.json update
- [ ] API response format unchanged (backward compatible)
- [ ] Labels generated correctly for existing corpora
- [ ] Graceful handling of missing/invalid manifest
