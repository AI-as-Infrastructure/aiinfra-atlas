# Environment Management Specification

## Overview

This specification defines how the corpus wizard updates environment variables and regenerates configuration files to ensure the UI reflects the correct corpus information.

## ADDED Requirements

### Requirement: Activation SHALL update environment variables

The corpus activation process SHALL update relevant environment variables to reflect the new corpus configuration.

#### Scenario: Updating VITE_SITE_TITLE

Given a corpus with display name "Historical Documents 1901"
When the corpus is activated
Then the VITE_SITE_TITLE in .env.development should be updated
And the value should be set to "Historical Documents 1901"
And the original value should be backed up

#### Scenario: Preserving other environment variables

Given an environment file with multiple variables
When VITE_SITE_TITLE is updated
Then all other variables should remain unchanged
And the file format should be preserved
And comments should be maintained

### Requirement: Frontend configuration SHALL be regenerated

After updating environment variables, the frontend configuration SHALL be regenerated to apply the changes.

#### Scenario: Regenerating Vue configuration

Given environment variables have been updated
When the activation process completes
Then the generate_vue_files.sh script should be executed
And frontend configuration files should be regenerated
And the new title should appear in the UI

#### Scenario: Handling regeneration failures

Given the configuration regeneration fails
When the error occurs
Then the activation should not fail completely
And the user should be notified of the issue
And manual regeneration instructions should be provided

### Requirement: Environment updates SHALL be safe

Environment file modifications SHALL be performed safely with proper validation and rollback capabilities.

#### Scenario: Safe environment file updates

Given an environment file needs updating
When the update is performed
Then the original file should be backed up first
And the new content should be validated before writing
And syntax errors should be detected and prevented

#### Scenario: Rollback on failure

Given an environment update fails
When the failure is detected
Then the original environment file should be restored
And the user should be notified of the rollback
And the error details should be logged

## MODIFIED Requirements

### Requirement: Environment configuration SHALL support corpus metadata

The environment system SHALL be extended to support corpus-specific metadata beyond just the title.

#### Scenario: Additional corpus metadata

Given a corpus with rich metadata
When it is activated
Then relevant metadata should be stored in environment variables:
- CORPUS_NAME for the internal identifier
- CORPUS_DESCRIPTION for the description
- CORPUS_VERSION for versioning
And these should be accessible to both frontend and backend