# Implementation Tasks

## Phase 1: Remove Environment Variables

### 1.1 Remove INTER_RATER from .env files
- [x] Remove all `INTER_RATER_*` variables from `config/.env.template`
- [x] Remove all `INTER_RATER_*` variables from `config/.env.development`
- [x] Remove all `INTER_RATER_*` variables from `config/.env.staging` (if exists)
- [x] Remove all `INTER_RATER_*` variables from `config/.env.production` (if exists)

### 1.2 Remove INTER_RATER from Backend Code
- [x] Update `backend/services/phoenix_client.py` to use `PHOENIX_PROJECT_NAME` directly
- [x] Update `backend/services/inter_rater_service.py` to read from manifest only (no env fallback)
- [x] Update `backend/telemetry/api.py` to remove `INTER_RATER_ENABLED` env checks
- [x] Update `backend/telemetry/inter_rater_feedback.py` to read from manifest
- [x] Update `backend/modules/system_configuration.py` to remove `ENABLE_INTER_RATER` check
- [x] Update `tests/conftest.py` to use manifest-based fixture

## Phase 2: Add Manifest Support

### 2.1 Add Manifest Support for Inter-Rater Config
- [x] Update `backend/modules/corpus_config.py` to include `InterRaterConfig` model
- [x] Add `_load_inter_rater_config()` function in inter_rater_service.py
- [x] Update corpus builder to include inter-rater settings in manifest output

### 2.2 Update Corpus Wizard Backend
- [x] Add inter-rater fields handling in `corpus_wizard.py` build endpoint
- [x] Include inter-rater config in manifest generation during build
- [x] Add `reload_config()` method to inter_rater_service for post-build reload
- [x] Add validation for inter-rater numeric ranges (max_ratings: 1-10, sessions_per_user: 1-50)

## Phase 3: Frontend Changes

### 3.1 Add Inter-Rater UI to Corpus Wizard
- [x] Add "Inter-Rater Reliability" section to RequirementsChecker step (Step 7)
- [x] Add toggle for enabling inter-rater mode
- [x] Add number input for max_ratings (1-10, default 3)
- [x] Add number input for sessions_per_user (1-50, default 5)
- [x] Add help text explaining the settings
- [x] Wire up to build request payload in CorpusWizard.vue

## Phase 4: Documentation

### 4.1 Update Documentation
- [x] Update `docs/inter_rater.md` to document wizard configuration (remove env var references)
- [x] Update configuration examples from bash to JSON format
- [x] Add February 2026 release notes

## Acceptance Criteria

### Functionality
- [x] Inter-rater settings can be configured via corpus wizard
- [x] Settings are persisted in manifest.json
- [x] Backend reads settings from manifest only (no env var fallback)
- [x] No `INTER_RATER_*` env vars remain in .env files
- [x] Phoenix queries use `PHOENIX_PROJECT_NAME` directly

### UI
- [x] Inter-rater section displays in Step 7 (System Requirements)
- [x] Help text explains purpose of each setting
- [x] Validation prevents invalid numeric values via HTML input constraints

### Documentation
- [x] Wizard configuration documented
- [x] All env var references updated to manifest format

## Testing Requirements
- [x] Unit test: InterRaterService reads from manifest (verified manually)
- [x] Unit test: InterRaterService uses defaults when manifest has no inter_rater section (verified manually)
- [x] Unit test: Phoenix client uses PHOENIX_PROJECT_NAME (verified manually)
- [x] Integration test: Corpus build includes inter-rater config in manifest (verified manually)
- [x] Manual test: Configure inter-rater via wizard and verify functionality
- [x] Grep verification: No INTER_RATER_* references in .env files

## Implementation Notes

- Manifest version bumped to 1.3 to include inter_rater section
- InterRaterService automatically reloads config after corpus builds
- Frontend uses camelCase (maxRatings, sessionsPerUser) which maps to snake_case in backend
- Tests fixture updated to use manifest-based mock instead of env var fixture
