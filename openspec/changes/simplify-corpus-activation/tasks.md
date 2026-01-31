# Tasks: Simplify Corpus Activation

## Backend Changes

### 1. Change corpus builder output directory
- [ ] Update `backend/routers/corpus_wizard.py` line 1840 to use `backend/corpus/` instead of `backend/corpus/tmp/`
- [ ] Remove or update any hardcoded references to `tmp/` directory
- [ ] Verify `backend/modules/corpus_builder.py` default output_dir handles direct corpus path

### 2. Add overwrite warning endpoint
- [ ] Create `/api/corpus-wizard/check-existing` endpoint in `backend/routers/corpus_wizard.py`
- [ ] Check if `backend/corpus/manifest.json` exists
- [ ] Return corpus metadata if exists (name, build date, document count, size)
- [ ] Return empty response if no existing corpus

### 3. Remove activation endpoint
- [ ] Delete or deprecate `/api/corpus-wizard/activate` endpoint in `backend/routers/corpus_wizard.py`
- [ ] Remove backup creation logic (lines 1271-1296)
- [ ] Remove file moving logic (lines 1300-1305)

### 4. Update target configuration
- [ ] Move target configuration and .env update logic from activation to build completion
- [ ] Update .env files immediately after successful build
- [ ] Ensure TEST_TARGET is set correctly in all environment files

### 5. Remove test search endpoint
- [ ] Delete or deprecate `/api/corpus-wizard/test-search` endpoint in `backend/routers/corpus_wizard.py`
- [ ] Remove test search implementation code
- [ ] Remove citation formatting code specific to test search

## Frontend Changes

### 6. Add overwrite warning to build step
- [ ] Call check-existing endpoint before starting build
- [ ] Display warning modal if existing corpus found
- [ ] Show existing corpus details (name, date, size)
- [ ] Require explicit confirmation before proceeding
- [ ] Update `frontend/src/pages/CorpusWizard.vue` build initiation logic

### 7. Remove activation step UI
- [ ] Remove "Activate" tab/step from wizard navigation
- [ ] Update step numbers (Build becomes final step)
- [ ] Remove activation-related reactive state variables
- [ ] Update wizard completion logic to finish after build

### 8. Update build completion
- [ ] Show "Build Complete - Corpus Ready" message instead of "Ready to Activate"
- [ ] Display corpus statistics (document count, size, filters)
- [ ] Add message: "Your corpus is now active. Go to the main application to test queries."
- [ ] Add "Go to Main App" button/link
- [ ] Remove "Go to Activation" button

### 9. Remove test search UI
- [ ] Remove test search component from build completion view
- [ ] Remove test search reactive state variables
- [ ] Remove test search API calls
- [ ] Remove test search results display

## Testing & Validation

### 10. Test complete workflow
- [ ] Verify warning appears when overwriting existing corpus
- [ ] Verify corpus builds directly in `backend/corpus/`
- [ ] Verify validation confirms files exist after build
- [ ] Verify .env files updated with correct TEST_TARGET
- [ ] Verify no tmp/ directory created
- [ ] Test with empty corpus directory (first build)
- [ ] Test with existing corpus (overwrite scenario)
- [ ] Verify main app works with newly built corpus immediately

### 11. Clean up existing tmp directories
- [ ] Document process for users to remove any existing `backend/corpus/tmp/` directories
- [ ] Add note to migration guide about tmp/ cleanup

## Documentation

### 12. Update documentation
- [ ] Update corpus wizard documentation to reflect new workflow
- [ ] Remove references to activation step and test search
- [ ] Document manual backup recommendations
- [ ] Document that users should test via main application
- [ ] Update screenshots/diagrams if present
