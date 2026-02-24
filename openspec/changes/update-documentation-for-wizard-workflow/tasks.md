# Tasks: Update Documentation for Wizard Workflow

## Phase 1: Critical Path (users will fail without these)

- [ ] 1. Rewrite ReadMe.md: wizard-first quick start, remove Git LFS, update architecture overview (DOC-001, DOC-006, DOC-017)
- [ ] 2. Rewrite docs/development.md: wizard as primary setup, remove manual vector store steps, update troubleshooting (DOC-007, DOC-014, DOC-017)
- [ ] 3. Rewrite docs/configuration.md: separate wizard-managed config (corpus_active.json, manifest) from .env config (API keys, Redis, telemetry) (DOC-002, DOC-008, DOC-014)
- [ ] 4. Rewrite docs/create_store.md: wizard as primary method, manual creation as advanced section (DOC-009, DOC-017)

## Phase 2: High Priority (confusing or misleading)

- [ ] 5. Update .claude/CLAUDE.md: add wizard workflow, corpus_active.json, configure/deploy modes, backend/corpus/ structure, remove Git LFS references (DOC-005, DOC-017)
- [ ] 6. Update docs/key_modules.md: add wizard modules (corpus_wizard.py, corpus_builder.py, manifest_loader.py, mode_manager.py), document backend/corpus/ directory (DOC-004, DOC-012)
- [ ] 7. Update docs/manifest.md: correct paths to backend/corpus/manifest.json, document v1.4 schema with build environment and filters (DOC-010, DOC-014)
- [ ] 8. Update docs/test_targets.md: explain wizard-generated targets, manual creation as advanced, update paths (DOC-011, DOC-014)
- [ ] 9. Update docs/production.md: add wizard setup and deploy mode to deployment checklist (DOC-013, DOC-014)
- [ ] 10. Update docs/runtime-mode-env-handling.md: document corpus_active.json role, configure/deploy mode lifecycle, System Mode page (DOC-003, DOC-002)

## Phase 3: Minor Updates (path corrections and prerequisites)

- [ ] 11. Update docs/RAG_search.md: fix config references, update chroma/BM25 paths to backend/corpus/ (DOC-015)
- [ ] 12. Update docs/authentication.md: update inter-rater config location to manifest (DOC-015)
- [ ] 13. Update docs/staging.md: add wizard testing guidance, configure/deploy mode notes (DOC-015)
- [ ] 14. Update docs/telemetry.md: add wizard-generated corpus telemetry attributes (DOC-015)
- [ ] 15. Update docs/health_monitoring.md: update health check paths to backend/corpus/ (DOC-015)
- [ ] 16. Update docs/load_testing.md: add wizard prerequisite for corpus setup (DOC-015)
- [ ] 17. Update docs/gpu_compatibility.md: add wizard GPU mode indicators and usage (DOC-015)
- [ ] 18. Update docs/testing.md: add wizard test documentation (DOC-015)
- [ ] 19. Update docs/backups.md: add corpus_active.json and backend/corpus/ to backup guidance (DOC-015)
- [ ] 20. Update docs/analysis.md: verify wizard corpus compatibility notes (DOC-015)

## Phase 4: Cleanup

- [ ] 21. Archive docs/corpus_wizard_integration.md: merge relevant content into corpus_wizard.md, delete original (DOC-016)
- [ ] 22. Review docs/corpus_wizard.md: ensure it positions wizard as THE primary path and references System Mode page as starting point
- [ ] 23. Final cross-reference check: search all docs for stale references to Git LFS, backend/targets/manifest.json, make vs, RETRIEVER_MODULE env var, default vector store (DOC-017)

## Dependencies

- Tasks 1-4 can be done in parallel (independent files)
- Tasks 5-10 can be done in parallel after Phase 1
- Tasks 11-20 can be done in parallel after Phase 2
- Tasks 21-23 depend on all prior phases being complete
