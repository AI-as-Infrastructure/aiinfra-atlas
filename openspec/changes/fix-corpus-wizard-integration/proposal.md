# Fix Corpus Wizard Integration

## Summary

Fix critical integration issues in the corpus wizard that prevent newly built corpora from functioning correctly. The wizard builds corpora successfully but fails to integrate them with the existing ATLAS system, resulting in non-functional deployments.

## Problem Statement

After building a corpus through the wizard, three critical issues prevent it from working:

1. **Filter System Broken**: The generated retriever cannot read the manifest structure correctly, causing filters to not appear in the UI
2. **Missing Target Configuration**: No target configuration file is generated, causing "Unknown error" when queries are attempted
3. **Site Title Not Updated**: The VITE_SITE_TITLE environment variable is not updated, leaving the UI with the wrong title

These issues make the corpus wizard output unusable without manual intervention.

## Proposed Solution

### 1. Fix Retriever Manifest Reading
- Update the generated retriever template to correctly read the manifest structure
- Ensure filter options are properly extracted from `manifest.fields.corpus.values`

### 2. Generate Target Configuration
- Create a target configuration file (e.g., `k20_claude4.txt`) during the validation step
- Use sensible defaults for the target configuration
- Add a UI note explaining how users can create additional target configurations

### 3. Update Environment Variables
- Update VITE_SITE_TITLE in the .env file during activation
- Regenerate frontend configuration files to apply the new title
- Ensure the title change is reflected in the UI

## User Impact

**Before**: Users can build a corpus but it doesn't work - filters don't appear, queries fail, and the title is wrong.

**After**: Users can build a corpus and immediately use it - filters work, queries succeed, and the UI shows the correct title.

## Technical Scope

### Modified Components
- `backend/modules/corpus_builder.py` - Template generation for retriever
- `backend/routers/corpus_wizard.py` - Target generation and environment updates
- `frontend/src/pages/CorpusWizard.vue` - UI updates for target configuration

### New Components
- Target configuration template
- Environment variable update utility

## Validation Approach

1. Build a test corpus through the wizard
2. Verify filters appear in the UI
3. Verify queries work correctly
4. Verify the site title updates
5. Verify users can add custom target configurations

## Dependencies

- Depends on the existing corpus wizard implementation
- No external dependencies

## Risks and Mitigations

**Risk**: Breaking existing corpus functionality
**Mitigation**: Only modify the generated files, not the core retriever logic

**Risk**: Environment file corruption
**Mitigation**: Create backup before modification, validate syntax after update