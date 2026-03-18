# Proposal: Update Security Dependencies

## Change ID
`update-security-dependencies`

## Summary
Patch critical and high-severity vulnerabilities in Python and npm dependencies, and remove the unused `@aws-amplify/ui-vue` package. Deferred items requiring major version upgrades are documented for follow-up.

## Motivation
Dependabot and local audits (`pip-audit`, `npm audit`) identified multiple vulnerabilities:

### Applied (this change)

| Package | Old | New | CVE | Severity |
|---------|-----|-----|-----|----------|
| `nltk` | 3.9.1 | 3.9.3 | CVE-2025-14009 | Critical (Zip Slip / RCE) |
| `unstructured` | 0.17.2 | 0.18.18 | CVE-2025-64712 | Critical (path traversal RCE) |
| `python-multipart` | 0.0.20 | 0.0.22 | CVE-2026-24486 | High (arbitrary file write) |

### Applied (npm cleanup)

| Package | Action | Reason |
|---------|--------|--------|
| `@aws-amplify/ui-vue` v3 | **Remove** | Imported but zero components used; source of lodash prototype pollution (moderate) and nanoid predictability (moderate) vulnerabilities |

### Deferred (requires separate PRs with breaking changes)

| Issue | Blocker | Severity |
|-------|---------|----------|
| starlette DoS (CVE-2025-27523, CVE-2025-62727) | Needs FastAPI 0.115 -> 0.135+ (strict Content-Type, security class 401->403 change) | High |
| langchain SSRF (GHSA-2g6r-c272-w58r) | Needs langchain 0.3 -> 1.x ecosystem upgrade | Low |
| npm: axios, fast-xml-parser (via aws-amplify v5) | Needs aws-amplify v5 -> v6 (Auth API rewrite) | High / Critical |
| npm: esbuild (via vite v5) | Needs vite v5 -> v7 (dev-only risk) | Moderate |
| ecdsa timing attack (CVE-2024-23342) | No fix available; transitive dep of python-jose | Moderate |

## Scope

### In Scope
- Bump `nltk`, `unstructured`, `python-multipart` in `config/requirements.txt`
- Remove `@aws-amplify/ui-vue` from `frontend/package.json`
- Document deferred items for follow-up

### Out of Scope
- FastAPI major upgrade (0.115 -> 0.135+)
- LangChain ecosystem upgrade (0.3 -> 1.x)
- aws-amplify v5 -> v6 migration
- Vite v5 -> v7 upgrade
- Lockfile regeneration (environment-specific, done at deploy time)

## Impact
- Affected code: `config/requirements.txt`, `frontend/package.json`
- No application code changes required for the Python bumps
- Removing `@aws-amplify/ui-vue` has zero runtime impact (unused)
- No API or behavior changes

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| unstructured 0.18.18 API changes | Low | Low | Only used for document ingestion; partition functions unchanged |
| nltk 3.9.3 behavior changes | Low | Low | Only used for text tokenization in corpus creation |
| python-multipart 0.0.22 compat | Very Low | Low | FastAPI 0.115.12 requires >=0.0.18; 0.0.22 is within range |
