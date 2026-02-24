# Tasks: Update Documentation for Wizard Workflow

## Phase 1: Critical Path (users will fail without these)

- [x] 1. Rewrite ReadMe.md: wizard-first quick start, remove Git LFS, update architecture overview (DOC-001, DOC-006, DOC-017)
- [x] 2. Rewrite docs/development.md: wizard as primary setup, remove manual vector store steps, update troubleshooting (DOC-007, DOC-014, DOC-017)
- [x] 3. Rewrite docs/configuration.md: separate wizard-managed config (corpus_active.json, manifest) from .env config (API keys, Redis, telemetry) (DOC-002, DOC-008, DOC-014)
- [x] 4. Rewrite docs/create_store.md: wizard as primary method, manual creation as advanced section (DOC-009, DOC-017)

## Phase 2: High Priority (confusing or misleading)

- [x] 5. Update .claude/CLAUDE.md: add wizard workflow, corpus_active.json, configure/deploy modes, backend/corpus/ structure, remove Git LFS references (DOC-005, DOC-017)
- [x] 6. Update docs/key_modules.md: add wizard modules (corpus_wizard.py, corpus_builder.py, manifest_loader.py, mode_manager.py), document backend/corpus/ directory (DOC-004, DOC-012)
- [x] 7. Update docs/manifest.md: correct paths to backend/corpus/manifest.json, document v1.4 schema with build environment and filters (DOC-010, DOC-014)
- [x] 8. Update docs/test_targets.md: explain wizard-generated targets, manual creation as advanced, update paths (DOC-011, DOC-014)
- [x] 9. Update docs/production.md: add wizard setup and deploy mode to deployment checklist (DOC-013, DOC-014)
- [x] 10. Update docs/runtime-mode-env-handling.md: document corpus_active.json role, configure/deploy mode lifecycle, System Mode page (DOC-003, DOC-002)

## Phase 3: Minor Updates (path corrections and prerequisites)

- [x] 11. Update docs/RAG_search.md: fix config references, update chroma/BM25 paths to backend/corpus/ (DOC-015)
- [x] 12. Update docs/authentication.md: verified - no stale references found (DOC-015)
- [x] 13. Update docs/staging.md: verified - no stale references found (DOC-015)
- [x] 14. Update docs/telemetry.md: verified - no stale references found (DOC-015)
- [x] 15. Update docs/health_monitoring.md: verified - no stale references found (DOC-015)
- [x] 16. Update docs/load_testing.md: verified - no stale references found (DOC-015)
- [x] 17. Update docs/gpu_compatibility.md: verified - no stale references found (DOC-015)
- [x] 18. Update docs/testing.md: verified - no stale references found (DOC-015)
- [x] 19. Update docs/backups.md: verified - no stale references found (DOC-015)
- [x] 20. Update docs/analysis.md: verified - no stale references found (DOC-015)

## Phase 4: Cleanup

- [x] 21. Archive docs/corpus_wizard_integration.md: deleted (historical fixes document, content superseded by corpus_wizard.md) (DOC-016)
- [x] 22. Review docs/corpus_wizard.md: updated persist_directory path and System Mode page reference
- [x] 23. Final cross-reference check: searched all docs for stale references - remaining backend/targets/manifest.json refs are legitimate fallback documentation (DOC-017)

## Dependencies

- Tasks 1-4 can be done in parallel (independent files)
- Tasks 5-10 can be done in parallel after Phase 1
- Tasks 11-20 can be done in parallel after Phase 2
- Tasks 21-23 depend on all prior phases being complete
