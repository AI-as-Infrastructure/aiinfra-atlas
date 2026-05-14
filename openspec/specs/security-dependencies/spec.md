# security-dependencies Specification

## Purpose
Security dependency management ensuring known critical and high-severity vulnerabilities are patched.
## Requirements
### Requirement: Critical Python Dependencies Patched
The system MUST NOT use Python packages with known critical or high-severity vulnerabilities when patched versions are available and compatible.

#### Scenario: python-jose replaced with PyJWT
- **WHEN** the application installs dependencies from `config/requirements.txt`
- **THEN** `python-jose` is NOT present in the dependency list
- **AND** `PyJWT[crypto]>=2.8.0` is used for all JWT validation
- **AND** both Cognito and Cloudflare auth modes function correctly with PyJWT

#### Scenario: psutil updated to latest stable
- **WHEN** the application installs dependencies from `config/requirements.txt`
- **THEN** `psutil` is version 7.x or higher

### Requirement: No Unused @aws-amplify/ui-vue Dependency
The `@aws-amplify/ui-vue` package MUST NOT be present in `frontend/package.json` as it is unused and introduces transitive vulnerabilities.

#### Scenario: Package removed from dependencies
- **WHEN** the frontend dependencies are reviewed
- **THEN** `@aws-amplify/ui-vue` is not listed in `frontend/package.json`
- **AND** no frontend source files import from `@aws-amplify/ui-vue`
- **AND** the lodash prototype pollution (GHSA-xxjr-mmjv-4gpg) and nanoid predictability (GHSA-mwcw-c2x4-8c55) vulnerabilities from this package are eliminated

