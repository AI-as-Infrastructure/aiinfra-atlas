# Tasks: Update Security Dependencies

## Phase 1: Python Dependency Patches
- [x] **Task 1.1**: Bump `nltk` 3.9.1 -> 3.9.3 in `config/requirements.txt` (CVE-2025-14009, Dependabot #32)
- [x] **Task 1.2**: Bump `unstructured` 0.17.2 -> 0.18.18 in `config/requirements.txt` (CVE-2025-64712, Dependabot #30)
- [x] **Task 1.3**: Bump `python-multipart` 0.0.20 -> 0.0.22 in `config/requirements.txt` (CVE-2026-24486, Dependabot #29)

## Phase 2: npm Cleanup
- [ ] **Task 2.1**: Remove `@aws-amplify/ui-vue` from `frontend/package.json` (unused, source of lodash + nanoid vulns)

## Phase 3: Validation
- [ ] **Task 3.1**: Run `openspec validate update-security-dependencies --strict`
- [ ] **Task 3.2**: Verify `frontend/package.json` is valid JSON
- [ ] **Task 3.3**: Verify no application code imports `@aws-amplify/ui-vue` components

## Deferred Items (separate PRs)
- [ ] **Deferred A**: FastAPI 0.115 -> 0.135+ (fixes starlette CVE-2025-27523, CVE-2025-62727)
- [ ] **Deferred B**: aws-amplify v5 -> v6 (fixes axios, fast-xml-parser, remaining lodash/nanoid via transitive deps)
- [ ] **Deferred C**: langchain 0.3 -> 1.x (fixes SSRF GHSA-2g6r-c272-w58r)
- [ ] **Deferred D**: vite v5 -> v7 (fixes esbuild dev-server vulnerability)
