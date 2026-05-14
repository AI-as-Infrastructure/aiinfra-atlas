# security-dependencies Specification

## MODIFIED Requirements

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
