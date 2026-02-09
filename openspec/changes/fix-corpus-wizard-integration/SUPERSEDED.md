# SUPERSEDED PROPOSAL

**Status**: Superseded by implementation
**Date**: February 5, 2026

## Why This Proposal is Superseded

This proposal has been superseded by incremental fixes that were implemented directly between January 31 and February 3, 2026. The critical issues identified in this proposal have been addressed through the following commits:

### Issues Resolved

1. **Filter System Fixed** (Commit: e484a57)
   - Retriever now correctly reads manifest structure
   - Filters appear properly in the UI
   - Documents are correctly tagged with corpus identifiers

2. **Target Configuration** (Commits: Multiple)
   - Target configuration is now generated during corpus build
   - Configuration is saved to corpus_active.json
   - All telemetry fields are properly included

3. **corpus_active.json Updates** (Commit: 1332ee1)
   - File is properly updated after corpus build
   - Retriever module and collection names are correctly set

### Remaining Work

The only remaining issue (VITE_SITE_TITLE not being updated) has been extracted into a separate, minimal proposal: `update-corpus-site-title`.

## Related Changes

- `simplify-corpus-activation` - Partially implemented, removed activation step
- `update-corpus-site-title` - New minimal proposal for remaining issue
- Various incremental fixes in corpus wizard implementation

## Recommendation

This proposal should not be implemented as written. The issues have been resolved through incremental development, which proved more effective than a large-scale refactoring.