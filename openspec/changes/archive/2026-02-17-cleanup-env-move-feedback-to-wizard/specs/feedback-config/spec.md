# Feedback Configuration Specification

## ADDED Requirements

### Requirement: Manifest-Based Feedback Configuration
The system SHALL store feedback type visibility settings in the corpus manifest under a `feedback` section, replacing build-time environment variables.

#### Scenario: Feedback config stored in manifest
- **WHEN** a corpus is built via the Corpus Wizard
- **THEN** the manifest.json SHALL contain a `feedback` section with `simple_enabled`, `enhanced_enabled`, and `skip_enabled` boolean fields

#### Scenario: Default values applied
- **WHEN** the manifest has no `feedback` section
- **THEN** all feedback types SHALL default to enabled (true)

### Requirement: Feedback Configuration API
The system SHALL provide a `/api/system/feedback-config` endpoint that returns the current feedback configuration from the manifest.

#### Scenario: API returns manifest config
- **WHEN** a GET request is made to `/api/system/feedback-config`
- **THEN** the response SHALL contain `simple_enabled`, `enhanced_enabled`, and `skip_enabled` boolean fields
- **AND** the values SHALL reflect the manifest configuration

#### Scenario: API returns defaults when manifest missing
- **WHEN** a GET request is made to `/api/system/feedback-config`
- **AND** the manifest has no `feedback` section
- **THEN** all fields SHALL return `true` (all enabled)

### Requirement: Corpus Wizard Feedback UI
The Corpus Wizard SHALL provide toggles for configuring feedback type visibility in Step 7 (System Requirements).

#### Scenario: User configures feedback types
- **WHEN** a user is in the System Requirements step of the Corpus Wizard
- **THEN** they SHALL see toggles for Simple Feedback, Enhanced Feedback, and Skip Option
- **AND** each toggle SHALL default to enabled

#### Scenario: Validation prevents no feedback options
- **WHEN** a user attempts to disable all feedback types
- **THEN** the system SHALL display a warning that at least one feedback type must be enabled

### Requirement: Frontend Reads Config from API
The frontend SHALL fetch feedback configuration from the API at runtime instead of reading build-time environment variables.

#### Scenario: InlineFeedback fetches config
- **WHEN** the InlineFeedback component mounts
- **THEN** it SHALL fetch configuration from `/api/system/feedback-config`
- **AND** display buttons based on the returned configuration

#### Scenario: Graceful fallback on API error
- **WHEN** the API request fails
- **THEN** the frontend SHALL fallback to showing all feedback options enabled

## REMOVED Requirements

### Requirement: Environment Variable Feedback Configuration
The system SHALL NO LONGER use `VITE_FEEDBACK_SIMPLE_ENABLED`, `VITE_FEEDBACK_ENHANCED_ENABLED`, or `VITE_FEEDBACK_SKIP_ENABLED` environment variables.

**Reason**: Feedback configuration is now stored in the corpus manifest and served via API, enabling runtime configuration without rebuilds.

**Migration**: Existing deployments should rebuild their corpus using the Corpus Wizard to configure feedback settings, or use the default (all enabled) behavior.

#### Scenario: Env vars removed from templates
- **WHEN** checking .env template files
- **THEN** no `VITE_FEEDBACK_SIMPLE_ENABLED`, `VITE_FEEDBACK_ENHANCED_ENABLED`, or `VITE_FEEDBACK_SKIP_ENABLED` variables SHALL exist
