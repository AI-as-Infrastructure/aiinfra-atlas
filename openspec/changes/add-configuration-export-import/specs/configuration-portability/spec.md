# Configuration Portability Capability

## ADDED Requirements

### Requirement: Configuration Export

The system SHALL provide the ability to export complete corpus and test target configurations to a JSON file.

#### Scenario: User exports configuration from main UI
Given a user has configured a corpus and test target
When they click the "Export Configuration" button above the Test Target box
Then a JSON file containing all configuration settings is downloaded
And the file includes corpus, test target, and system settings

#### Scenario: Export includes all necessary settings
Given a configuration export is initiated
When the export file is generated
Then it contains source paths, embedding models, chunk settings, filters
And it includes test target provider, model, and parameters
And system configuration toggles are preserved

### Requirement: Configuration Import

The system SHALL provide the ability to import configuration from a previously exported JSON file.

#### Scenario: User imports configuration in wizard
Given a user is on the corpus wizard metadata step
When they select "Import Configuration" and upload a valid JSON file
Then the configuration is validated and preview is shown
And upon confirmation the settings are applied to the wizard

#### Scenario: Import validates configuration compatibility
Given a user attempts to import a configuration file
When the file is processed
Then version compatibility is checked
And resource availability is validated
And any issues are reported to the user

### Requirement: Configuration Validation

The system SHALL validate imported configurations before applying them.

#### Scenario: Invalid configuration is rejected
Given a user uploads a configuration file with invalid structure
When the import is attempted
Then the system identifies the validation errors
And provides specific feedback about what is invalid
And no partial configuration is applied

#### Scenario: Missing resources are handled gracefully
Given an imported configuration references unavailable models or paths
When validation occurs
Then the user is warned about missing resources
And given the option to update paths or cancel import

### Requirement: Configuration Format Specification

The system SHALL use a versioned JSON format for configuration export/import.

#### Scenario: Configuration includes version metadata
Given a configuration is exported
When the JSON file is created
Then it includes atlas_config_version field
And it includes the ATLAS version that created it
And export timestamp is recorded

#### Scenario: Backward compatibility is maintained
Given a configuration from an older version is imported
When version checking occurs
Then compatible settings are identified and applied
And incompatible settings generate warnings
And user is informed of any limitations

## MODIFIED Requirements

### Requirement: Main UI Layout

The main UI SHALL include a clearly labeled configuration export button distinct from session export.

#### Scenario: Export button is properly positioned
Given the main UI is loaded
When the Test Target box is rendered
Then an "Export Configuration" button appears above it
And it has a distinct icon (gear with download arrow)
And tooltip explains it exports system configuration

#### Scenario: Export button is distinguishable
Given both session and configuration export options exist
When users view the UI
Then configuration export has different styling/icon
And tooltips clearly explain the difference
And button labels are unambiguous

### Requirement: Corpus Wizard Flow

The corpus wizard SHALL support importing configurations as an alternative to manual setup.

#### Scenario: Import option is available at start
Given a user starts the corpus wizard
When they reach the metadata step
Then an "Import Configuration" button is visible
And selecting it opens a file picker for JSON files

#### Scenario: Imported config populates wizard
Given a valid configuration is imported
When the wizard processes the import
Then all relevant fields are pre-populated
And user can review and modify before proceeding
And validation occurs before moving to next step

### Requirement: API Architecture

The backend SHALL expose endpoints for configuration export and import operations.

#### Scenario: Export endpoint returns complete config
Given a GET request to /api/configuration/export
When the endpoint processes the request
Then it returns current corpus configuration
And includes active test target settings
And includes system configuration state

#### Scenario: Import endpoint validates and applies config
Given a POST request to /api/configuration/import with JSON payload
When the endpoint processes the configuration
Then it validates structure and compatibility
And applies the configuration if valid
And returns detailed status response

## REMOVED Requirements

None - this is an additive feature that doesn't remove existing functionality.