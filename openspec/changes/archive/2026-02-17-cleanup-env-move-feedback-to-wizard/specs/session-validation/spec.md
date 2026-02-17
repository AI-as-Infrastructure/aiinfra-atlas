# Session Validation Specification

## REMOVED Requirements

### Requirement: Session Validation Service
The system SHALL NO LONGER provide AI-assisted session validation functionality.

**Reason**: The Session Validation feature is disabled in production and development environments, adds LLM API costs when enabled, and increases codebase complexity without active use.

**Migration**: No migration required as feature is already disabled. If needed in future, can be re-implemented as a wizard-configured feature.

#### Scenario: Validation service removed
- **WHEN** checking the backend services directory
- **THEN** no `validation_service.py` file SHALL exist

#### Scenario: Validation router removed
- **WHEN** checking the backend routers directory
- **THEN** no `validation.py` router file SHALL exist

#### Scenario: Validation endpoints removed
- **WHEN** making requests to `/api/validate_session` or `/api/validate_config`
- **THEN** the response SHALL be 404 Not Found

### Requirement: Validation Environment Variables
The system SHALL NO LONGER use `VALIDATION_*` environment variables.

**Reason**: The Session Validation feature has been removed entirely.

**Migration**: Remove these variables from .env files. No code changes required as the feature is already disabled.

#### Scenario: Validation env vars removed
- **WHEN** checking .env template files
- **THEN** no `VALIDATION_ENABLED`, `VALIDATION_LLM_MODE`, `VALIDATION_LLM_DEFAULT`, `VALIDATION_LLM_ALTERNATE`, `VALIDATION_PROVIDER_DEFAULT`, or `VALIDATION_PROVIDER_ALTERNATE` variables SHALL exist

### Requirement: AI-Assisted Feedback Toggle
The system SHALL NO LONGER provide an AI-Assisted Feedback option in the UI.

**Reason**: AI-Assisted Feedback was tied to the Session Validation feature which has been removed.

**Migration**: The "AI Assisted Feedback" button will no longer appear in the UI. Users can use Simple or Enhanced feedback instead.

#### Scenario: AI-assisted env var removed
- **WHEN** checking .env template files
- **THEN** no `VITE_FEEDBACK_AI_ASSISTED_ENABLED` variable SHALL exist

#### Scenario: AI-assisted button removed from UI
- **WHEN** viewing the feedback options in InlineFeedback component
- **THEN** no "AI Assisted Feedback" button SHALL be displayed
