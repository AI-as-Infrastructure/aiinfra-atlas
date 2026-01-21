# Capability: Wizard User Interface

## ADDED Requirements

### Requirement: Wizard mode operation
The system SHALL provide a dedicated wizard mode that temporarily disables normal operation while configuring a new corpus.

#### Scenario: Enter wizard mode
GIVEN an administrator wants to configure a new corpus
WHEN they execute "make corpus-wizard-cpu" or "make corpus-wizard-gpu"
THEN the system enters wizard mode
AND normal query endpoints are disabled
AND the UI redirects to the corpus wizard interface
AND a status indicator shows wizard mode is active

#### Scenario: Emergency exit from wizard mode
GIVEN the system is in wizard mode
WHEN an error occurs or the user needs to abort
THEN they can execute "make corpus-wizard-exit"
AND the system exits wizard mode without changes
AND normal operations resume immediately

### Requirement: Progressive wizard flow
The system SHALL guide users through corpus configuration with a step-by-step wizard interface.

#### Scenario: Complete wizard flow
GIVEN a user starts the corpus wizard
WHEN they progress through the steps:
  1. Provide corpus metadata (name, time period, entities)
  2. Select source (local directory or GitHub)
  3. Review and customize discovered filters
  4. Select embedding model from recommendations
  5. Monitor build progress
  6. Test and activate the corpus
THEN each step validates before allowing progression
AND the user can navigate back to previous steps
AND progress is saved between sessions

### Requirement: Real-time build progress
The system SHALL provide real-time progress updates during vector store creation.

#### Scenario: Monitor corpus build progress
GIVEN a corpus build is in progress
WHEN the user views the progress screen
THEN they see:
  - Current document being processed
  - Number of documents completed vs total
  - Estimated time remaining
  - Live log output (with filtering options)
  - Ability to pause/resume the build
AND progress updates via Server-Sent Events
AND the UI remains responsive during the build

### Requirement: Filter customization interface
The system SHALL allow users to review, edit, and test discovered filters before building the corpus.

#### Scenario: Customize discovered filters
GIVEN the system has discovered potential filters
WHEN the user reviews the filter configuration step
THEN they can:
  - See all suggested filters with document counts
  - Edit filter labels and patterns
  - Delete unwanted filters
  - Add custom filters
  - Test filters with sample documents
  - Preview which documents match each filter
AND changes are validated before proceeding

### Requirement: Model selection with testing
The system SHALL recommend embedding models and allow testing with corpus samples.

#### Scenario: Test embedding models
GIVEN the system has recommended embedding models based on the corpus time period
WHEN the user is on the model selection step
THEN they see:
  - Recommended models with match scores
  - Explanation of why each model is recommended
  - Option to test with random corpus samples
  - Performance metrics for each model
  - Option to specify a custom model
AND the selected model is validated before building

## MODIFIED Requirements

### Requirement: Corpus source validation
The system SHALL validate corpus sources before processing and provide clear feedback on issues.

#### Scenario: Validate local directory
GIVEN a user specifies a local directory path
WHEN the system validates the source
THEN it checks:
  - Directory exists and is readable
  - Contains supported file types (.txt, .xml)
  - Has sufficient files for meaningful corpus
  - Directory structure is parseable
AND provides specific error messages for any issues

#### Scenario: Validate GitHub repository
GIVEN a user specifies a GitHub repository URL
WHEN the system validates the source
THEN it checks:
  - Repository exists and is accessible
  - Contains corpus files in the specified path
  - Repository size is within limits
  - Network connectivity is stable
AND provides fallback options if validation fails