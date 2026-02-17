# SUPERSEDED PROPOSAL

**Status**: Partially Implemented, Remainder Superseded
**Date**: February 5, 2026

## Why This Proposal is Superseded

This proposal was partially implemented in commit 99ab576 on January 31, 2026, with subsequent adjustments that modified the original design. The final implementation differs from the proposal due to technical constraints discovered during development.

### What Was Implemented

1. **Removed Activation Step** ✅
   - Corpus is immediately available after build
   - No separate activation UI or endpoint

2. **Removed Test Search** ✅
   - Test search UI and endpoints completely removed (Commit: 40b1861)
   - Users test via main application

3. **Overwrite Warning** ✅
   - Warning displayed before overwriting existing corpus
   - Shows existing corpus details

### What Was Changed from Original Proposal

1. **Still Using Temp Directory**
   - Originally proposed: Build directly in backend/corpus/
   - Actually implemented: Build in backend/corpus_build_temp/ then move
   - Reason: ChromaDB instance conflicts when building in active directory (Commit: 504ae84)

2. **Kept Some Complexity**
   - File movement from temp to final location still required
   - This complexity was necessary to avoid ChromaDB conflicts

### Technical Lessons Learned

The attempt to build directly in the final location failed due to ChromaDB maintaining active connections to the existing vector store. The solution required:
- Building in an isolated temporary directory
- Moving files after build completion
- This approach balances simplicity with technical requirements

## Related Changes

- `fix-corpus-wizard-integration` - Addressed integration issues
- `update-corpus-site-title` - Addresses remaining UI title issue
- Multiple incremental fixes to corpus wizard

## Recommendation

This proposal should not be implemented as originally written. The hybrid approach currently in place (simplified flow but with necessary temp directory) represents the best balance between simplicity and technical constraints.