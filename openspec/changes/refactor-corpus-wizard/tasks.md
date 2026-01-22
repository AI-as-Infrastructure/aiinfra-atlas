# Tasks: Refactor and Implement UI-Driven Corpus Configuration Wizard

## Phase 1: Backend Foundation (Parallel Work Possible)

### Configuration Management
- [ ] Create `backend/modules/corpus_config.py` for config schema and validation
- [ ] Create `backend/modules/corpus_metadata.py` for metadata tracking
- [ ] Add YAML config loader with schema validation
- [ ] Create default config templates for Hansard and Darwin
- [ ] Migrate corpus-specific env vars to corpus.yaml structure
- [ ] Update config.py to read from corpus.yaml instead of .env
- [ ] Create migration script for existing .env to corpus.yaml

### Corpus Analysis Engine
- [ ] Create `backend/modules/corpus_analyzer.py` for structure analysis
- [ ] Implement directory pattern detection algorithm
- [ ] Implement XML metadata extraction for filter discovery
- [ ] Add temporal filter generation from date ranges
- [ ] Create filter inference rules engine

### GitHub Integration
- [ ] Create `backend/modules/github_corpus.py` for repo handling
- [ ] Implement sparse checkout for corpus directories
- [ ] Add GitHub API fallback for non-git environments
- [ ] Add local caching for downloaded repos
- [ ] Handle authentication for private repos (optional)

## Phase 2: API Layer

### Wizard Mode Management
- [ ] Add `CORPUS_WIZARD_MODE` environment variable handling
- [ ] Create wizard mode middleware to redirect endpoints
- [ ] Implement corpus backup functionality
- [ ] Add atomic corpus swap with rollback

### API Endpoints
- [ ] Enhance existing `backend/routers/corpus_wizard.py` router
- [ ] Implement `/api/corpus-wizard/analyze` endpoint
- [ ] Implement `/api/corpus-wizard/suggest-filters` endpoint
- [ ] Implement `/api/corpus-wizard/recommend-model` endpoint
- [ ] Implement `/api/corpus-wizard/validate-config` endpoint
- [ ] Implement `/api/corpus-wizard/build` endpoint with background task
- [ ] Add SSE endpoint for build progress streaming
- [ ] Implement `/api/corpus-wizard/test-search` endpoint
- [ ] Implement `/api/corpus-wizard/activate` endpoint
- [ ] Add `/api/corpus-wizard/status` health check

## Phase 3: Corpus Builder Refactoring

### Universal Corpus Builder
- [ ] Refactor existing `backend/modules/corpus_builder.py` to be config-driven
- [ ] Update builder to use new directory structure (corpus/tmp, corpus/sources)
- [ ] Add detailed progress reporting callbacks with metrics
- [ ] Implement CPU/GPU mode detection and switching
- [ ] Add system requirements checker (RAM, disk, GPU)
- [ ] Implement pause/resume functionality for builds
- [ ] Add progress tracking per filter/category
- [ ] Support both TXT and XML in unified pipeline
- [ ] Add metadata injection into manifest.json
- [ ] Generate appropriate test queries per corpus type
- [ ] Add build time estimation based on corpus size and mode

### Model Recommendation System
- [ ] Create embedding model database with characteristics
- [ ] Implement time-period matching logic
- [ ] Add corpus sampling for model testing
- [ ] Create model performance testing utility

## Phase 4: Frontend UI

### Wizard Components
- [ ] Create `frontend/src/views/CorpusWizard.vue` main container
- [ ] Create `frontend/src/components/wizard/WizardSteps.vue` progress indicator
- [ ] Create `frontend/src/components/wizard/CorpusMetadataForm.vue`
- [ ] Add time period picker with validation
- [ ] Add entity extraction fields (people, places, topics)
- [ ] Add copyright and DOI input fields with validation

### Source Selection
- [ ] Create `frontend/src/components/wizard/SourceSelector.vue`
- [ ] Add local directory browser/input
- [ ] Add GitHub URL input with branch selection
- [ ] Implement source validation and testing

### Filter Configuration
- [ ] Create `frontend/src/components/wizard/FilterConfigurator.vue`
- [ ] Display discovered filters with counts
- [ ] Add filter editing capabilities
- [ ] Add custom filter creation
- [ ] Implement filter testing with sample docs

### Model Selection
- [ ] Create `frontend/src/components/wizard/ModelSelector.vue`
- [ ] Display model recommendations with scores
- [ ] Add custom model input option
- [ ] Implement sample text testing
- [ ] Show model characteristics (size, speed, period)

### System Requirements Check
- [ ] Create `frontend/src/components/wizard/RequirementsChecker.vue`
- [ ] Display CPU/GPU capabilities detection
- [ ] Show memory and disk requirements
- [ ] Provide time estimates for CPU vs GPU modes
- [ ] Add warnings for insufficient resources
- [ ] Allow mode selection (CPU/GPU)

### Build Progress
- [ ] Create `frontend/src/components/wizard/BuildProgress.vue`
- [ ] Implement SSE/WebSocket for real-time progress updates
- [ ] Display detailed metrics (docs/sec, memory, GPU usage)
- [ ] Show progress per filter category
- [ ] Add log viewer with filtering and search
- [ ] Show current document and chunk being processed
- [ ] Display estimated time remaining with confidence
- [ ] Add pause/resume/cancel capabilities
- [ ] Show performance graphs (optional advanced view)
- [ ] Add progress persistence for recovery after interruption

### Testing & Activation
- [ ] Create `frontend/src/components/wizard/CorpusTester.vue`
- [ ] Add test search interface
- [ ] Display configuration summary
- [ ] Show storage requirements
- [ ] Add activation confirmation dialog

## Phase 5: Integration

### Makefile Commands
- [ ] Add `make corpus-wizard` command to enter wizard mode
- [ ] Add `make corpus-wizard-exit` for emergency exit
- [ ] Add `make corpus-backup` for manual backup
- [ ] Add `make corpus-restore` for rollback
- [ ] Update help documentation

### State Management
- [ ] Create Vuex store for wizard state
- [ ] Add persistence for wizard progress
- [ ] Handle connection loss gracefully
- [ ] Implement auto-save for configuration

## Phase 6: Testing

### Unit Tests
- [ ] Test filter discovery algorithms
- [ ] Test model recommendation logic
- [ ] Test config validation
- [ ] Test GitHub repo handling
- [ ] Test metadata extraction

### Integration Tests
- [ ] Test full wizard flow with mock data
- [ ] Test corpus swapping mechanism
- [ ] Test progress reporting
- [ ] Test error recovery
- [ ] Test backup and restore

### E2E Tests
- [ ] Test Hansard → Darwin swap
- [ ] Test Darwin → Hansard swap
- [ ] Test custom corpus configuration
- [ ] Test GitHub repo corpus
- [ ] Test cancellation and cleanup

## Phase 7: Environment Variable Migration

### Cleanup Environment Files
- [ ] Remove deprecated corpus-specific variables from .env.template
- [ ] Update .env.development with new wizard variables
- [ ] Update .env.staging and .env.production templates
- [ ] Create corpus.yaml.template with example configuration
- [ ] Update backend/modules/config.py to use corpus.yaml
- [ ] Remove hardcoded "Hansard" references from VITE_SITE_TITLE
- [ ] Keep ATLAS_VERSION in .env (application version, not corpus)
- [ ] Update PHOENIX_PROJECT_NAME to use corpus name dynamically

### Code Updates for Environment Changes
- [ ] Update all code references to deprecated env vars
- [ ] Create backward compatibility layer for gradual migration
- [ ] Update manifest loader to provide corpus metadata
- [ ] Modify frontend to display dynamic corpus name from config
- [ ] Update telemetry to use dynamic project names

### Build Script Updates
- [ ] Enhance config/generate_vue_files.sh to read corpus.yaml
- [ ] Add yq dependency for YAML parsing in build scripts
- [ ] Inject VITE_SITE_TITLE from corpus.yaml at build time
- [ ] Update deployment scripts to handle corpus.yaml
- [ ] Ensure frontend/.env is regenerated on corpus swap

## Phase 8: Documentation

### User Documentation
- [ ] Create wizard user guide with screenshots
- [ ] Document corpus organization best practices
- [ ] Create troubleshooting guide
- [ ] Add corpus sharing instructions
- [ ] Update README.md with corpus wizard overview
- [ ] Add corpus wizard section to docs/configuration.md
- [ ] Create docs/corpus_wizard.md comprehensive guide
- [ ] Add example configurations for common corpus types
- [ ] Document GitHub repository requirements and structure

### Developer Documentation
- [ ] Document configuration schema in docs/corpus_config_schema.md
- [ ] Document filter discovery algorithms
- [ ] Document API endpoints in docs/api/corpus_wizard.md
- [ ] Add extension guide for new corpus types
- [ ] Update docs/development.md with wizard development setup
- [ ] Document corpus builder refactoring in docs/architecture.md
- [ ] Add corpus metadata standards documentation
- [ ] Create migration guide from hardcoded to config-driven approach

### Existing Documentation Updates
- [ ] Update Makefile help text for new commands
- [ ] Update docs/create_store.md with new config-driven process
- [ ] Update .env.template with wizard-related variables
- [ ] Add wizard mode explanation to docs/production.md
- [ ] Update docs/staging.md with corpus testing procedures
- [ ] Add corpus swapping to docs/key_modules.md

## Phase 9: Validation & Polish

### Validation
- [ ] Validate with Hansard corpus
- [ ] Validate with Darwin corpus
- [ ] Test with synthetic test corpus
- [ ] Performance test with large corpus (>100k docs)

### Polish
- [ ] Add input validation and error messages
- [ ] Improve progress estimation accuracy
- [ ] Add corpus configuration export/import
- [ ] Add configuration templates library
- [ ] Optimize GitHub download speed

## Dependencies & Considerations

### Prerequisites
- `add-dynamic-corpus-filters` change must be completed first
- Redis must be available for background tasks

### Parallelizable Work
- Backend foundation components can be developed in parallel
- Frontend components can be mocked and developed independently
- Documentation can begin with design phase

### Critical Path
1. Wizard mode management (blocks everything)
2. Config-driven corpus builder (blocks build functionality)
3. API endpoints (blocks frontend integration)
4. Frontend wizard flow (blocks user testing)

## Estimated Timeline
- Phase 1-2: 2 days (backend foundation)
- Phase 3: 1 day (corpus builder refactoring)
- Phase 4: 2 days (frontend UI)
- Phase 5-6: 1 day (integration and testing)
- Phase 7-8: 1 day (documentation and polish)

Total: ~7 days of focused development