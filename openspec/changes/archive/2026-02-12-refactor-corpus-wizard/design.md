# Design: Corpus Wizard Refactor

## Overview
This document captures the detailed design decisions and implementation notes for the corpus wizard refactor, particularly around the preview functionality and filter discovery.

## Document Preview Functionality

### Purpose
The preview step allows users to validate their corpus configuration before building by:
- Showing sample documents with extracted metadata
- Discovering and displaying directory-based filters
- Providing document counts and statistics
- Validating extraction patterns (URLs, dates)

### Backend Implementation

#### Preview Endpoint (`/api/corpus-wizard/preview`)

**Request Structure:**
```json
{
  "source": {
    "type": "local" | "github",
    "location": "/path/to/corpus",
    "file_extensions": ".txt",
    "include_subdirectories": true,
    "extract_inline_urls": true,
    "date_pattern": "YYYY-MM-DD" | "DD-MM-YYYY" | "custom",
    "custom_date_pattern": "regex_pattern"
  },
  "metadata": {
    "name": "Corpus Name",
    "description": "..."
  }
}
```

**Response Structure:**
```json
{
  "total_documents": 206,
  "total_size": 70603028,
  "docs_with_urls": 5,
  "docs_with_dates": 5,
  "samples": [...],
  "filters": [...],
  "warnings": [...]
}
```

### Filter Discovery Algorithm

The preview endpoint automatically discovers filters from directory structure:

1. **Directory Analysis**: Traverses all documents and builds a tree of directories
2. **Filter Generation**: Creates a filter for each directory with:
   - `id`: Sanitized directory name (lowercase, underscores)
   - `label`: Original directory name
   - `type`: "directory" or "all"
   - `path`: Relative path from corpus root
   - `pattern`: Glob pattern for matching
   - `document_count`: Number of documents in directory

3. **Default Filter**: Always includes an "all" filter for all documents

### Frontend Integration

#### Preview Component Structure

1. **Load Preview Button**: Triggers preview loading
2. **Discovery Summary**: Shows total documents, size, metadata extraction stats
3. **Sample Documents**: Displays first 5 documents with:
   - Filename and path
   - File size
   - Preview text (first 10 lines)
   - Extracted metadata (URLs, dates)

4. **Filter Selection**: Grid of discovered filters with:
   - Checkbox for selection
   - Label and document count
   - Directory path
   - Visual distinction for "all" filter

#### State Management

- `previewData`: Stores preview response
- `selectedFilters`: Array of selected filter IDs
- `loadingPreview`: Loading state flag

### Date Extraction Patterns

For filenames like "Friday, 02 August, 1901.txt":

**Regex Pattern**: `\w+,\s*(\d{1,2}(?:st|nd|rd|th)?\s+\w+,\s*\d{4})`

This captures dates like:
- "02 August, 1901"
- "2nd August, 1901"
- "31st December, 1901"

### URL Extraction

Expects URLs in first line of document with format:
```
<url>https://example.com/path</url>
```

## Common Issues and Solutions

### Issue: Preview Button Not Working

**Symptoms:**
- Clicking "Load Document Preview" does nothing
- No network request visible in browser dev tools
- Console shows no errors

**Potential Causes:**
1. Backend endpoint not registered
2. Frontend not properly bound to button click
3. CORS issues between frontend and backend
4. Source path not properly set

**Debugging Steps:**
1. Check browser console for errors
2. Verify backend is running: `curl http://localhost:8000/api/corpus-wizard/preview`
3. Check network tab in browser dev tools
4. Verify source.location has a value before clicking preview
5. Check that backend has been restarted after changes

**Solution Checklist:**
- [ ] Backend restarted with new endpoints
- [ ] Source location field has value
- [ ] File extensions field populated (defaults to .txt)
- [ ] No JavaScript errors in console
- [ ] Network request reaches backend

### Issue: Filters Not Discovered

**Symptoms:**
- Preview loads but no filters shown
- Only "All Documents" filter appears

**Potential Causes:**
1. Documents not in subdirectories
2. Path resolution issues
3. File extension mismatch

**Solution:**
- Ensure documents are organized in subdirectories
- Check that file_extensions includes actual file types
- Verify include_subdirectories is true

## Implementation Notes

### Key Files Modified

1. **Frontend:**
   - `/frontend/src/pages/CorpusWizard.vue` - Complete UI refactor

2. **Backend:**
   - `/backend/routers/corpus_wizard.py` - New endpoints for preview, validation, etc.

### Dependencies
- Python `pathlib` for path manipulation
- `re` module for regex pattern matching
- Vue 3 composition API for frontend state

### Performance Considerations
- Preview limited to first 5 documents to avoid long load times
- Filter discovery is synchronous but fast for typical corpus sizes
- Document counting could be optimized with caching for large corpora

## Testing Checklist

- [ ] Preview loads with local directory source
- [ ] Preview loads with GitHub source
- [ ] URL extraction works when checkbox enabled
- [ ] Date extraction works with various patterns
- [ ] Filters discovered from directory structure
- [ ] Filter selection persists to build configuration
- [ ] Warning messages appear for missing URLs/dates when expected
- [ ] Error handling for invalid paths
- [ ] Preview refresh works after changing settings