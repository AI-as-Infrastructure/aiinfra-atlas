# Corpus Configuration Spec

## ADDED Requirements

### Requirement: Site title reflects active corpus

The system MUST update the VITE_SITE_TITLE environment variable to match the display_name of the active corpus after successful corpus build.

#### Scenario: Building corpus with custom name

Given a user builds a corpus through the wizard with display_name "Parliamentary Records 1901"
When the corpus build completes successfully
Then the VITE_SITE_TITLE in the appropriate environment file is updated to "Parliamentary Records 1901"
And the UI displays "Parliamentary Records 1901" as the site title after frontend restart

#### Scenario: Building corpus without display_name

Given a user builds a corpus without specifying a display_name
When the corpus build completes successfully
Then the VITE_SITE_TITLE uses the corpus name field as fallback
And the UI displays the corpus name as the site title

### Requirement: Environment updates respect runtime mode

The system MUST update the correct environment file based on the current runtime mode.

#### Scenario: Update in development mode

Given the system is running in development mode
When a corpus build completes
Then the VITE_SITE_TITLE is updated in config/.env.development
And other environment files remain unchanged

#### Scenario: Update in deploy mode

Given the system is running in deploy mode
When a corpus build completes
Then the system logs the intended title update
And respects the deploy mode restrictions on file modifications