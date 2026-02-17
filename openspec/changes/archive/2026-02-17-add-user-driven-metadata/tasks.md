# Implementation Tasks: User-Driven Metadata Extraction

## Phase 1: Backend Pattern Matching (Priority: High)

### Task 1.1: Create Metadata Extraction Module
- [ ] Create `backend/modules/metadata_extraction.py`
- [ ] Implement `PatternMatcher` class
- [ ] Add pattern syntax parser (`{field}`, `{field:d}`, `{field:w}`)
- [ ] Compile patterns to regex
- [ ] Add timeout protection for regex matching

### Task 1.2: Pattern Validation
- [ ] Create `validate_pattern()` function
- [ ] Check for valid field names
- [ ] Detect pattern conflicts
- [ ] Validate against sample files
- [ ] Return helpful error messages

### Task 1.3: Metadata Extractor
- [ ] Implement `MetadataExtractor` class
- [ ] Extract from folder hierarchy
- [ ] Extract from filenames
- [ ] Handle missing/partial matches
- [ ] Type conversion (string to number/date)

### Task 1.4: Unit Tests
- [ ] Test pattern compilation
- [ ] Test various filename formats
- [ ] Test edge cases (special characters, Unicode)
- [ ] Test performance with many patterns
- [ ] Test timeout protection

## Phase 2: Frontend UI Components (Priority: High)

### Task 2.1: Create Metadata Pattern Step
- [ ] Create `frontend/src/components/wizard/MetadataPatternStep.vue`
- [ ] Add to wizard flow (between Filters and Model)
- [ ] Make step optional/skippable
- [ ] Add state management for patterns
- [ ] Connect to backend API

### Task 2.2: Pattern Template Selector
- [ ] Create `PatternTemplateSelector.vue`
- [ ] Define 4 default templates (Parliamentary, Academic, Legal, Correspondence)
- [ ] Template preview functionality
- [ ] Custom pattern option
- [ ] Load/save custom templates

### Task 2.3: Folder Mapping Builder
- [ ] Create `FolderMappingBuilder.vue`
- [ ] Display folder hierarchy
- [ ] Dropdown for field names
- [ ] Field type selection (category/number/date)
- [ ] Live preview of extracted values
- [ ] Validation for field names

### Task 2.4: Filename Pattern Builder
- [ ] Create `FilenamePatternBuilder.vue`
- [ ] Visual pattern builder with drag-drop
- [ ] Highlight pattern matches on sample filename
- [ ] Support for multiple filename patterns
- [ ] Pattern syntax help/documentation
- [ ] Real-time validation

### Task 2.5: Pattern Tester
- [ ] Create `PatternTester.vue`
- [ ] Load sample files from corpus
- [ ] Test patterns against multiple files
- [ ] Show success/failure rate
- [ ] Display extracted metadata
- [ ] Export test results

### Task 2.6: Derived Filter Builder
- [ ] Create `DerivedFilterBuilder.vue`
- [ ] List available metadata fields
- [ ] Quick filter templates (by day, month, year)
- [ ] Custom filter condition builder
- [ ] Preview matched document count
- [ ] Filter validation

## Phase 3: Integration (Priority: High)

### Task 3.1: Update Corpus Analyzer
- [ ] Modify `backend/modules/corpus_analyzer.py`
- [ ] Add `extract_metadata_from_path()` method
- [ ] Integrate with filter suggestion
- [ ] Update analysis results structure
- [ ] Pass patterns to corpus builder

### Task 3.2: Update Document Loading
- [ ] Modify `create/create_corpus_store.py`
- [ ] Call metadata extraction during load
- [ ] Add extracted fields to document metadata
- [ ] Handle extraction errors gracefully
- [ ] Log extraction statistics

### Task 3.3: Update Configuration Schema
- [ ] Add `metadata_extraction` to `CorpusConfig`
- [ ] Define `FolderMapping` model
- [ ] Define `FilenamePattern` model
- [ ] Define `DerivedFilter` model
- [ ] Update YAML serialization

### Task 3.4: API Endpoints
- [ ] Create `/api/corpus-wizard/test-pattern` endpoint
- [ ] Create `/api/corpus-wizard/validate-patterns` endpoint
- [ ] Update `/api/corpus-wizard/suggest-filters` to include derived filters
- [ ] Add pattern templates endpoint
- [ ] Update configuration save/load

### Task 3.5: Update Vector Store
- [ ] Ensure metadata fields are indexed
- [ ] Update ChromaDB collection schema
- [ ] Test filtering on extracted metadata
- [ ] Performance optimization for metadata queries
- [ ] Document metadata field limits

## Phase 4: Testing & Polish (Priority: Medium)

### Task 4.1: Integration Tests
- [ ] Test full wizard flow with patterns
- [ ] Test various corpus structures
- [ ] Test pattern template application
- [ ] Test derived filter creation
- [ ] Test corpus building with metadata

### Task 4.2: Performance Testing
- [ ] Benchmark pattern matching speed
- [ ] Test with 1000+ documents
- [ ] Optimize regex compilation
- [ ] Cache compiled patterns
- [ ] Memory usage profiling

### Task 4.3: UI/UX Polish
- [ ] Add loading states
- [ ] Improve error messages
- [ ] Add tooltips and help text
- [ ] Keyboard shortcuts
- [ ] Accessibility (ARIA labels)

### Task 4.4: Documentation
- [ ] Update corpus wizard user guide
- [ ] Create pattern syntax reference
- [ ] Document common patterns cookbook
- [ ] Add video tutorial
- [ ] Update API documentation

## Phase 5: Templates & Examples (Priority: Low)

### Task 5.1: Expand Template Library
- [ ] News articles template
- [ ] Medical records template
- [ ] Financial documents template
- [ ] Government documents template
- [ ] Social media posts template

### Task 5.2: Example Patterns
- [ ] ISO date extraction (YYYY-MM-DD)
- [ ] US date extraction (MM/DD/YYYY)
- [ ] Author extraction from citations
- [ ] Version numbers (v1.2.3)
- [ ] Document IDs with prefixes

### Task 5.3: Pattern Sharing
- [ ] Export patterns to file
- [ ] Import patterns from file
- [ ] Pattern validation on import
- [ ] Share patterns via GitHub gists
- [ ] Community pattern library (future)

## Testing Checklist

### Unit Tests
- [ ] Pattern compilation
- [ ] Metadata extraction
- [ ] Filter derivation
- [ ] Type conversion
- [ ] Error handling

### Integration Tests
- [ ] Wizard flow
- [ ] Corpus building
- [ ] Filter application
- [ ] Search with metadata
- [ ] Configuration persistence

### UI Tests
- [ ] Pattern builder interaction
- [ ] Template selection
- [ ] Live preview
- [ ] Error states
- [ ] Accessibility

### Performance Tests
- [ ] Pattern matching speed
- [ ] Large corpus handling
- [ ] Memory usage
- [ ] Vector store queries
- [ ] UI responsiveness

## Risk Mitigation Tasks

### Task R.1: Fallback Mechanisms
- [ ] Skip pattern step if too complex
- [ ] Default to no metadata extraction
- [ ] Manual metadata entry option
- [ ] Pattern debugging mode
- [ ] Recovery from bad patterns

### Task R.2: User Education
- [ ] In-app pattern tutorial
- [ ] Example patterns gallery
- [ ] Pattern validation feedback
- [ ] Common mistakes guide
- [ ] Support documentation

## Definition of Done

Each task is complete when:
1. Code is implemented and reviewed
2. Unit tests pass
3. Integration tests pass
4. Documentation is updated
5. No regression in existing features
6. Accessibility standards met
7. Performance benchmarks met

## Estimated Timeline

- **Phase 1**: 3 days (Backend pattern matching)
- **Phase 2**: 3 days (Frontend UI components)
- **Phase 3**: 2 days (Integration)
- **Phase 4**: 2 days (Testing & polish)
- **Phase 5**: 2 days (Templates & examples)

**Total**: 12 days

## Dependencies

- No external library dependencies
- Requires Python 3.10+ (for match statements)
- Frontend requires Vue 3.3+ (for typed props)
- ChromaDB must support arbitrary metadata fields