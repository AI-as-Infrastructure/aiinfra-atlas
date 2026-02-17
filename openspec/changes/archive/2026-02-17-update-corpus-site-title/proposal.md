# Update Corpus Site Title

## Summary

Update the VITE_SITE_TITLE environment variable after corpus build to display the corpus name in the UI instead of the default "ATLAS".

## Why

After building a new corpus through the wizard, the UI continues to display "ATLAS" as the site title instead of the corpus name. This is confusing for users who have just built a custom corpus and expect to see their corpus name reflected in the interface.

## Problem Statement

When a corpus is built through the wizard:
- The corpus metadata includes a display_name (e.g., "Parliamentary Records 1901")
- The frontend uses VITE_SITE_TITLE environment variable for the UI title
- This variable is never updated during or after corpus build
- Users see "ATLAS" instead of their corpus name

## Proposed Solution

After successful corpus build, update VITE_SITE_TITLE in the environment files:
1. Read the display_name from the built corpus manifest
2. Update VITE_SITE_TITLE in config/.env.development (and other env files as needed)
3. Trigger frontend configuration regeneration if needed

## User Impact

**Before**: UI shows "ATLAS" regardless of which corpus is active

**After**: UI shows the actual corpus name (e.g., "Parliamentary Records 1901")

## Technical Scope

### Modified Components
- `backend/routers/corpus_wizard.py` - Add environment variable update after build

### Implementation Details
- Update happens in the build completion phase, after corpus_active.json is updated
- Use the existing mode_manager to handle environment updates appropriately
- Ensure the update is applied to the correct environment file based on runtime mode

## Dependencies

- Existing environment management utilities
- Mode manager for handling different runtime modes

## Validation Approach

1. Build a test corpus with a custom name
2. Verify VITE_SITE_TITLE is updated in the environment file
3. Verify the UI displays the correct corpus name after refresh
4. Test in both development and deploy modes

## Risks and Mitigations

**Risk**: Environment file corruption during update
**Mitigation**: Use safe file writing with atomic operations

**Risk**: Frontend not picking up the change
**Mitigation**: Document that frontend may need restart/rebuild to reflect title change