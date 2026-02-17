# Tasks: Refactor Corpus Wizard Workflow

## Phase 1: Frontend Restructuring

- [x] Update wizard steps array to new workflow
- [x] Add workflow type selection component (Text/XML toggle)
- [x] Simplify metadata form to essential fields only
- [x] Create unified source configuration component
- [x] Implement directory browser with filter integration
- [x] Add checkbox for inline URL extraction
- [x] Add date pattern configuration for filename parsing

## Phase 2: Document Preview

- [x] Create document preview component
- [x] Implement sample document loader
- [x] Display extracted metadata (URLs, dates)
- [x] Add validation indicators
- [x] Create filter adjustment controls
- [x] Implement document count estimator

## Phase 3: Model Selection

- [x] Simplify model selection to dropdown
- [x] Add default model (sentence-transformers/all-MiniLM-L6-v2)
- [x] Create custom model input (Hugging Face model ID)
- [x] Add chunk size and overlap settings with defaults
- [x] Display model characteristics (dimensions, size)
- [x] Add model availability checker

## Phase 4: Build Progress

- [x] Implement WebSocket or SSE for real-time updates
- [x] Create progress bar component
- [x] Add document processing counter
- [x] Implement estimated time remaining
- [x] Add error reporting display
- [x] Create build log viewer

## Phase 5: Activation Checks

- [x] Create pre-activation validation component
- [x] Implement test query functionality
- [x] Display build statistics summary
- [x] Add corpus comparison view
- [x] Create activation confirmation dialog
- [x] Implement rollback mechanism

## Phase 6: Backend Integration

- [x] Update corpus_builder.py for new workflow
- [x] Enhance metadata_extractor.py for date patterns
- [x] Update url_builder.py for inline extraction
- [x] Create preview endpoint for document sampling
- [x] Implement progress streaming endpoint
- [x] Add pre-activation validation endpoint

## Phase 7: Configuration Updates

- [x] Update CorpusConfig schema for new fields
- [x] Migrate existing configurations
- [x] Update default configuration templates
- [x] Create configuration validator
- [x] Document configuration changes

## Phase 8: Testing

- [x] Unit tests for each wizard step component
- [x] Integration tests for complete workflow
- [x] Test with text corpus workflow
- [x] Test with various document formats
- [x] Performance testing with large corpora
- [x] Error handling tests

## Phase 9: Documentation

- [x] Update user documentation
- [x] Create migration guide
- [x] Document new configuration options
- [x] Add troubleshooting guide
- [x] Create video walkthrough (deferred - not required for release)