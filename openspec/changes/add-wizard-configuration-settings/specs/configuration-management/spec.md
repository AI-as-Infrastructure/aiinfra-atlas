# Configuration Management Capability

## ADDED Requirements

### Requirement: System Configuration UI

The system SHALL provide a user interface for configuring telemetry and inter-rater feedback settings during the corpus wizard setup process.

#### Scenario: User configures telemetry during wizard setup
Given a user is setting up a new corpus
When they reach the System Configuration step
Then they can toggle telemetry on or off
And the setting is persisted for the session

#### Scenario: User configures inter-rater feedback during setup
Given a user is in the System Configuration step
When they toggle the inter-rater feedback setting
Then the system updates the configuration
And feedback collection is enabled or disabled accordingly

### Requirement: Configuration Persistence

The system SHALL persist user configuration choices across sessions and system restarts.

#### Scenario: Configuration survives restart
Given a user has configured telemetry settings
When the system is restarted
Then the telemetry settings remain as configured
And no manual intervention is required

#### Scenario: Configuration file is created
Given a user saves configuration settings
When the settings are persisted
Then a system_settings.json file is created
And the file contains the current configuration state

### Requirement: Configuration API

The system SHALL provide REST API endpoints for reading and updating system configuration.

#### Scenario: Update configuration via API
Given an authenticated request to update configuration
When the request contains valid telemetry settings
Then the configuration is updated
And a success response is returned

#### Scenario: Read current configuration
Given a request for current configuration
When the API endpoint is called
Then the current settings are returned
And the source of configuration is indicated

## MODIFIED Requirements

### Requirement: Wizard Step Flow

The corpus wizard SHALL include a System Configuration step as the second step in the setup process.

#### Scenario: Wizard includes configuration step
Given a user starts the corpus wizard
When they complete the metadata step
Then they are presented with the System Configuration step
And they must configure settings before proceeding

#### Scenario: Step numbering is updated
Given the new configuration step is added
When the wizard renders
Then all subsequent steps are renumbered
And navigation remains functional

### Requirement: Telemetry Initialization

The telemetry system SHALL respect runtime configuration settings in addition to environment variables.

#### Scenario: Telemetry respects runtime config
Given telemetry is disabled in configuration
When the application initializes
Then no telemetry data is collected
And Phoenix connections are not established

#### Scenario: Environment variables override config
Given telemetry is enabled in configuration file
And TELEMETRY_ENABLED=false in environment
When the system starts
Then telemetry remains disabled
And environment variable takes precedence

### Requirement: Inter-Rater Feedback System

The inter-rater feedback system SHALL check runtime configuration before accepting feedback.

#### Scenario: Feedback disabled via config
Given inter-rater feedback is disabled in configuration
When a user attempts to submit feedback
Then the feedback is rejected
And appropriate error message is returned

#### Scenario: Feedback UI reflects configuration
Given inter-rater feedback is disabled
When the UI renders
Then feedback buttons are hidden
And users cannot access feedback features