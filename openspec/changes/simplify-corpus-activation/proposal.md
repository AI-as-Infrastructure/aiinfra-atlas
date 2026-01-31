# Simplify Corpus Activation

## Summary
Simplify the corpus build and activation workflow by building directly in the final location and eliminating unnecessary complexity around backups and temporary directories.

## Problem
The current corpus wizard build and activation flow is overly complex:
- Builds corpus in `backend/corpus/tmp/`
- Requires separate "activation" step that moves files from `tmp/` to `backend/corpus/`
- Creates automatic backups of previous corpus
- After activation, `tmp/` is empty, preventing re-testing
- Clicking "Activate" twice fails because tmp/ no longer contains the build
- Complex backup logic that backs up entire corpus directory including tmp/
- Confusing for single-user development environment

This violates the principle of simplicity stated in `.claude/CLAUDE.md`:
> "Research Tool Philosophy: This is a research prototype emphasizing lean, well-documented code that fails fast."

## Solution
Build corpus directly in the final location (`backend/corpus/`) and eliminate unnecessary steps:

1. **Direct Build**: Change corpus builder to build directly in `backend/corpus/` instead of `tmp/`
2. **Simple Warning**: Before building, warn user if existing corpus will be overwritten
3. **No Backups**: Remove automatic backup functionality
4. **No Activation**: Remove the activation step entirely - corpus is live immediately after build
5. **No Test Search**: Remove test search UI and endpoint - users test with main app instead
6. **Update .env Automatically**: After successful build, automatically update TEST_TARGET in .env files

This aligns with the fail-fast approach: if users need backups, they should handle that manually at the system level. Validation confirms files are correct, then users test via the main application interface.

## Capabilities
- `corpus-activation`: Modified to eliminate staging/activation workflow

## Dependencies
- `refactor-corpus-wizard` change (nearly complete at 52/53 tasks)
- Existing corpus builder backend modules
- Runtime mode management for .env updates

## Risks & Mitigations
- **Risk**: Users accidentally overwrite working corpus
  - **Mitigation**: Clear warning message before build starts, showing what will be overwritten
- **Risk**: No way to rollback to previous corpus
  - **Mitigation**: Document that users should use git, filesystem snapshots, or manual backups for production use
- **Risk**: Breaking existing workflows that depend on activation
  - **Mitigation**: This is a development tool; breaking changes are acceptable for simplification

## Validation
- Build completes successfully in `backend/corpus/`
- Validation endpoint confirms files exist and are structured correctly
- .env files updated correctly with new TEST_TARGET
- Warning displayed before overwriting existing corpus
- No tmp/ directory created or used
- Clean corpus/ directory structure after build
- Main app works with newly built corpus immediately

## Out of Scope
- Automatic backups
- Multi-corpus management
- Rollback mechanisms
- Cross-corpus comparison
