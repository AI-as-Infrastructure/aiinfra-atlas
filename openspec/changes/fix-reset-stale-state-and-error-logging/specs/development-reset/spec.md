## MODIFIED Requirements

### Requirement: Development Reset MUST Restore Default Environment State

The `make reset` command MUST remove all corpus-specific state, including resetting `VITE_SITE_TITLE` in `config/.env.development` to the template default value and removing `backend/targets/manifest.json`. After reset, the system MUST behave as a first-time installation with no stale corpus metadata.

#### Scenario: Reset restores default VITE_SITE_TITLE

- **GIVEN** a corpus has been built and `VITE_SITE_TITLE` in `config/.env.development` has been set to the corpus display name
- **WHEN** the user runs `make reset`
- **THEN** `VITE_SITE_TITLE` in `config/.env.development` MUST be reset to `"ATLAS"`
- **AND** all other `.env.development` settings (API keys, provider config) MUST be preserved

#### Scenario: Reset removes stale manifest from targets

- **GIVEN** a corpus has been built and `backend/targets/manifest.json` exists with corpus metadata
- **WHEN** the user runs `make reset`
- **THEN** `backend/targets/manifest.json` MUST be removed
- **AND** the Vector Store Overview MUST not display stale data from a previous build
