# Capability: Inter-Rater Configuration in Corpus Wizard

## ADDED Requirements

### Requirement: Corpus-level inter-rater configuration
The system SHALL allow inter-rater reliability settings to be configured per corpus through the wizard interface.

#### Scenario: Configure inter-rater via wizard
- **GIVEN** the user is in the corpus wizard target configuration step
- **WHEN** the user expands the "Inter-Rater Reliability" section
- **THEN** the system displays:
  - A toggle to enable/disable inter-rater mode
  - A numeric input for maximum ratings per session (1-10)
  - A numeric input for sessions per user (1-20)
- **AND** help text explains each setting's purpose

#### Scenario: Save inter-rater settings to manifest
- **GIVEN** the user has configured inter-rater settings in the wizard
- **WHEN** the corpus build completes successfully
- **THEN** the manifest.json includes an `inter_rater` section with:
  - `enabled`: boolean
  - `max_ratings`: integer (1-10)
  - `sessions_per_user`: integer (1-20)

#### Scenario: Backend reads from manifest
- **GIVEN** a corpus has been built with inter-rater settings in manifest
- **WHEN** the InterRaterService initializes
- **THEN** the service reads settings from manifest.json
- **AND** uses those values for inter-rater functionality

#### Scenario: Default values when no manifest config
- **GIVEN** no inter-rater settings exist in manifest.json
- **WHEN** the InterRaterService initializes
- **THEN** the service uses default values:
  - `enabled`: false
  - `max_ratings`: 3
  - `sessions_per_user`: 5
- **AND** no environment variables are consulted

## REMOVED Requirements

### Requirement: All INTER_RATER environment variables
The system SHALL NOT use any `INTER_RATER_*` environment variables.

#### Scenario: No INTER_RATER_PROJECT variable
- **GIVEN** the inter-rater system needs to query Phoenix
- **WHEN** determining which project to query
- **THEN** the system uses `PHOENIX_PROJECT_NAME` environment variable
- **AND** does not reference `INTER_RATER_PROJECT`

#### Scenario: No INTER_RATER_ENABLED variable
- **GIVEN** the system is checking if inter-rater mode is enabled
- **WHEN** determining the enabled state
- **THEN** the system reads from corpus manifest only
- **AND** does not reference `INTER_RATER_ENABLED` environment variable

#### Scenario: No INTER_RATER_MAX_RATINGS variable
- **GIVEN** the system needs the max ratings per session
- **WHEN** loading the configuration
- **THEN** the system reads from corpus manifest only
- **AND** does not reference `INTER_RATER_MAX_RATINGS` environment variable

#### Scenario: No INTER_RATER_SESSIONS_PER_USER variable
- **GIVEN** the system needs the sessions per user limit
- **WHEN** loading the configuration
- **THEN** the system reads from corpus manifest only
- **AND** does not reference `INTER_RATER_SESSIONS_PER_USER` environment variable

## CHANGED Requirements

### Requirement: Inter-rater service initialization
The InterRaterService SHALL read configuration from corpus manifest only.

#### Scenario: Configuration loading
- **GIVEN** the InterRaterService is initializing
- **WHEN** loading configuration
- **THEN** the service reads from corpus manifest.json `inter_rater` section
- **AND** uses default values if section is missing (enabled=false, max_ratings=3, sessions_per_user=5)
- **AND** does not consult any environment variables
