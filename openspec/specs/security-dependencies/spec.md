# security-dependencies Specification

## Purpose
Security dependency management ensuring known critical and high-severity vulnerabilities are patched.
## Requirements
### Requirement: Critical Python Dependencies Patched
The system MUST NOT use Python packages with known critical or high-severity vulnerabilities when patched versions are available and compatible.

#### Scenario: nltk Zip Slip patched
- **WHEN** the application installs dependencies from `config/requirements.txt`
- **THEN** `nltk` is version 3.9.3 or higher
- **AND** the Zip Slip vulnerability (CVE-2025-14009) is resolved

#### Scenario: unstructured path traversal patched
- **WHEN** the application installs dependencies from `config/requirements.txt`
- **THEN** `unstructured` is version 0.18.18 or higher
- **AND** the MSG attachment path traversal vulnerability (CVE-2025-64712) is resolved

#### Scenario: python-multipart arbitrary file write patched
- **WHEN** the application installs dependencies from `config/requirements.txt`
- **THEN** `python-multipart` is version 0.0.22 or higher
- **AND** the arbitrary file write vulnerability (CVE-2026-24486) is resolved

### Requirement: No Unused @aws-amplify/ui-vue Dependency
The `@aws-amplify/ui-vue` package MUST NOT be present in `frontend/package.json` as it is unused and introduces transitive vulnerabilities.

#### Scenario: Package removed from dependencies
- **WHEN** the frontend dependencies are reviewed
- **THEN** `@aws-amplify/ui-vue` is not listed in `frontend/package.json`
- **AND** no frontend source files import from `@aws-amplify/ui-vue`
- **AND** the lodash prototype pollution (GHSA-xxjr-mmjv-4gpg) and nanoid predictability (GHSA-mwcw-c2x4-8c55) vulnerabilities from this package are eliminated

