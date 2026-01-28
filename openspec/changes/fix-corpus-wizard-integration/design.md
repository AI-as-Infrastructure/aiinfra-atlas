# Design Document: Fix Corpus Wizard Integration

## Architecture Overview

This design addresses three critical integration gaps between the corpus wizard and the ATLAS system:

1. **Retriever-Manifest Alignment**: Ensuring the generated retriever can correctly read the manifest structure
2. **Target Configuration Generation**: Creating necessary target files for query execution
3. **Environment Synchronization**: Updating UI configuration to reflect the activated corpus

## Component Interactions

```
Corpus Wizard Build Process
    ↓
Manifest Generation (corpus_builder.py)
    ↓
Retriever Generation (from template)
    ↓
Validation Phase
    ├─→ Target Configuration Generation (NEW)
    └─→ Test Queries
    ↓
Activation Phase
    ├─→ File Movement (existing)
    ├─→ Environment Update (NEW)
    └─→ Config Regeneration (NEW)
```

## Implementation Details

### 1. Retriever-Manifest Alignment

**Problem**: The retriever template expects filter data at one location, but the manifest stores it elsewhere.

**Solution**:
- Modify the retriever template to read from `manifest.fields.corpus.values`
- Add fallback logic for backward compatibility
- Ensure the template generator and manifest generator use consistent paths

**Implementation Location**: `backend/modules/corpus_builder.py`, line ~700 in `_generate_retriever()`

### 2. Target Configuration Generation

**Problem**: No target configuration file exists, causing queries to fail with "Unknown error".

**Solution**:
- Generate a default `k20_claude4.txt` file during validation
- Use sensible defaults that work with most LLM providers
- Allow customization through environment variables

**Target File Format**:
```
# Auto-generated target configuration
LLM_PROVIDER=ANTHROPIC
LLM_MODEL=claude-3-sonnet-20240229
SEARCH_TYPE=similarity
SEARCH_K=20
SCORE_THRESHOLD=0.5
RETRIEVER_CLASS=TestRetriever
VECTOR_STORE=chroma
COLLECTION_NAME=test_collection
```

**Implementation Location**: New method in `backend/routers/corpus_wizard.py`

### 3. Environment Variable Updates

**Problem**: VITE_SITE_TITLE and other corpus metadata not reflected in UI.

**Solution**:
- Create utility function to safely update .env files
- Update variables during activation
- Trigger frontend config regeneration

**Update Process**:
1. Read current .env file
2. Create backup
3. Parse and update specific variables
4. Validate syntax
5. Write updated file
6. Run `generate_vue_files.sh`

**Implementation Location**: New utility in `backend/modules/env_manager.py`

## Data Flow

### Filter Data Flow
```
manifest.json → fields.corpus.values → retriever.get_corpus_options() → UI filters
```

### Target Configuration Flow
```
Validation → Generate target → Save to backend/targets/ → Load on query
```

### Environment Update Flow
```
Activation → Update .env → Regenerate Vue config → Reload UI
```

## Error Handling

### Retriever Errors
- If manifest structure is unexpected, log warning and use defaults
- Provide clear error messages about missing filter data

### Target Generation Errors
- If generation fails, provide manual configuration instructions
- Include template in error message for user reference

### Environment Update Errors
- Always create backup before modification
- Rollback on validation failure
- Provide manual update instructions if automated update fails

## Testing Strategy

### Unit Tests
- Test manifest reading with various structures
- Test target file generation with different settings
- Test environment file updates with edge cases

### Integration Tests
- Complete wizard flow from build to activation
- Query execution with generated target
- UI title and filter updates

### Manual Testing Checklist
1. Build corpus with wizard
2. Verify filters appear in UI
3. Execute test query successfully
4. Verify title updates in UI
5. Create custom target configuration
6. Switch between multiple corpora

## Migration Path

For existing installations:
1. Existing corpora continue to work (backward compatibility)
2. New corpora use improved integration
3. Optional migration tool for updating old corpora

## Security Considerations

- Environment file updates use atomic writes to prevent corruption
- Backup files are created with restricted permissions
- Target configurations are validated before use
- No sensitive data exposed in generated files

## Performance Impact

- Minimal: File operations during activation only
- Config regeneration adds ~2-3 seconds to activation
- No runtime performance impact on queries

## Migration Strategy

### Environment Variable Cleanup

After implementing the corpus wizard integration, several environment variables become obsolete:

#### Variables to Remove
- **`HANSARD_SOURCES_ROOT`**: Hansard-specific, no longer needed
- **`MULTI_CORPUS_VECTORSTORE`**: Deprecated, handled by wizard
- **`MULTI_CORPUS_METADATA`**: Deprecated, handled by wizard
- **`CHROMA_PERSIST_DIRECTORY`**: Now in target configuration
- **`CHROMA_COLLECTION_NAME`**: Now in target configuration
- **`BM25_CORPUS`**: Now in target configuration
- **`RETRIEVER_MODULE`**: Dynamic based on activated corpus

#### Migration Script Requirements
1. Create timestamped backups before modification
2. Provide dry-run mode for testing changes
3. Process all environment files (development, staging, production)
4. Log all removed variables for audit trail
5. Suggest manual review for borderline variables

#### Script Location
`scripts/migrate_cleanup_env_files.py` - to be run once after implementation

## Future Enhancements

1. **Multiple Target Templates**: Provide various target templates (GPT-4, Claude, Llama, etc.)
2. **Target Configuration UI**: Add UI for customizing target parameters
3. **Environment Profiles**: Support multiple environment profiles (dev, staging, prod)
4. **Hot Reload**: Automatic UI updates without manual refresh