# Proposal: Update Documentation for Wizard Workflow

## Summary

Overhaul all project documentation to reflect the architectural shift from a pre-built Git LFS corpus to a wizard-driven, product-like configuration experience. Approximately 80% of documentation describes a system that no longer exists.

## Motivation

The ATLAS project has undergone a fundamental change: the corpus wizard now replaces manual vector store creation, environment variable configuration, and Git LFS distribution. Users following current documentation will encounter:

- Failed Git LFS commands (no pre-built vector store shipped)
- Wrong file paths (backend/targets/ vs backend/corpus/)
- Manual setup steps that are now automated by the wizard
- No mention of System Mode, configure/deploy modes, or corpus_active.json
- References to environment variables that no longer drive corpus configuration

The documentation must be rewritten to present ATLAS as a configurable research tool where the wizard is the primary setup path, not an optional add-on.

## Scope

### Full Rewrite (4 files)
- **ReadMe.md** - Quick start must guide users to the wizard, not Git LFS
- **docs/development.md** - Development workflow now starts with the wizard
- **docs/configuration.md** - Restructure: wizard-managed config vs .env config
- **docs/create_store.md** - Wizard is primary path; manual creation is advanced option

### Significant Updates (6 files)
- **.claude/CLAUDE.md** - Add wizard workflow, corpus_active.json, configure/deploy modes
- **docs/key_modules.md** - Add corpus wizard modules, backend/corpus/ structure
- **docs/manifest.md** - Update paths to backend/corpus/, document v1.4 schema
- **docs/test_targets.md** - Explain wizard-generated targets as primary path
- **docs/production.md** - Add wizard setup to deployment workflow
- **docs/runtime-mode-env-handling.md** - Clarify corpus_active.json role in mode system

### Minor Updates (10 files)
- **docs/RAG_search.md** - Update config references and paths
- **docs/authentication.md** - Update inter-rater config location
- **docs/staging.md** - Add wizard testing guidance
- **docs/telemetry.md** - Add wizard telemetry attributes
- **docs/health_monitoring.md** - Update paths to backend/corpus/
- **docs/load_testing.md** - Add wizard prerequisite
- **docs/gpu_compatibility.md** - Add wizard GPU usage notes
- **docs/testing.md** - Add wizard test documentation
- **docs/backups.md** - Add corpus config backup guidance
- **docs/analysis.md** - Verify wizard corpus compatibility

### Archive (1 file)
- **docs/corpus_wizard_integration.md** - Historical integration fixes, merge relevant content into corpus_wizard.md

### Current / No Changes (3 files)
- **docs/data_privacy.md** - Architecture-agnostic
- **docs/token_counting.md** - Implementation-agnostic
- **docs/inter_rater.md** - Recently updated

## Key Principles for the Rewrite

1. **Wizard-first**: Every setup guide should lead with the wizard. Manual/advanced paths are secondary.
2. **No Git LFS references**: The repo ships clean; users build their own corpus.
3. **corpus_active.json is central config**: Not environment variables for corpus settings.
4. **backend/corpus/ is the active directory**: Not backend/targets/ for wizard-built corpora.
5. **System Mode page is the entry point**: Configure mode -> wizard -> deploy mode -> chat.
6. **Research tool philosophy**: Lean documentation, fail-fast approach, amateur RSE practices.
7. **Source-agnostic**: Documentation should not assume Hansard or any specific corpus content.

## Out of Scope

- Code changes (this is documentation only)
- Creating new documentation files beyond what exists
- Changing the wizard or backend behaviour
- Updating openspec/project.md (separate concern)

## Risks

- Documentation may drift again as features are added; mitigated by keeping docs terse and linking to code
- Some advanced workflows (manual vector store creation) may still be needed; preserve as clearly marked advanced sections
