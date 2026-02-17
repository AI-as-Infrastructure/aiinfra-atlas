# Tasks for fix-corpus-wizard-integration

## Phase 1: Fix Retriever Manifest Reading

- [ ] Analyze the current manifest structure and identify the correct paths for filter data
- [ ] Update the retriever template in corpus_builder.py to read from `manifest.fields.corpus.values`
- [ ] Fix the `get_corpus_options()` method to properly extract filter values
- [ ] Test that filters appear correctly in the UI after corpus activation

## Phase 2: Add Target Configuration UI to Wizard

- [ ] Create a new wizard step/page for target configuration
- [ ] Add form fields for LLM provider, model, and search parameters
- [ ] Pre-populate with k20_claude4 defaults as suggestions
- [ ] Create API endpoint to save target configuration
- [ ] Generate target file based on user selections
- [ ] Display unified configuration combining corpus and target settings
- [ ] Add configuration review before activation
- [ ] Clean up any obsolete target files from backend/targets/

## Phase 3: Update Environment Variables

- [ ] Create utility function to safely update .env files
- [ ] Add environment update logic to the activation endpoint
- [ ] Update VITE_SITE_TITLE with the corpus display name
- [ ] Regenerate frontend config files using generate_vue_files.sh
- [ ] Test that the title updates correctly in the UI

## Phase 4: Integration Testing

- [ ] Build a complete test corpus through the wizard
- [ ] Verify all filters appear and function correctly
- [ ] Verify queries execute without errors
- [ ] Verify the site title displays correctly
- [ ] Test creating custom target configurations
- [ ] Verify backward compatibility with existing corpora
- [ ] Verify unified configuration is complete:
  - Check /api/config endpoint returns all fields
  - Verify TestTargetBox displays complete configuration
  - Ensure composite_target is correctly generated
- [ ] Verify telemetry tracking:
  - Check all config fields appear in Phoenix telemetry
  - Verify composite_target and component fields are tracked
  - Ensure no missing attributes in telemetry data

## Phase 5: Environment Migration

- [ ] Create migration script to clean obsolete environment variables
- [ ] Script should remove HANSARD_SOURCES_ROOT, MULTI_CORPUS_* variables
- [ ] Script should remove CHROMA_*, BM25_CORPUS, RETRIEVER_MODULE variables
- [ ] Create timestamped backups before modifying .env files
- [ ] Provide dry-run mode for testing
- [ ] Apply migration to all .env files (development, staging, production)

## Phase 6: Documentation and Cleanup

- [ ] Document the target configuration format and options
- [ ] Add user guide for customizing target configurations
- [ ] Update corpus wizard documentation with new features
- [ ] Document the environment migration process
- [ ] Clean up any temporary files or debug code
- [ ] Add validation tests for the integration