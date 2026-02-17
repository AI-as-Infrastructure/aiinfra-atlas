# Document Preview and Validation

## ADDED Requirements

### Requirement: Document Preview Step
The wizard SHALL include a preview step between Sources and Model Selection to validate document discovery.

#### Scenario: User reviews discovered documents
GIVEN the user has configured source settings
WHEN they reach the preview step
THEN they SHALL see a sample of discovered documents
AND extracted metadata (URLs, dates) SHALL be displayed
AND total document count SHALL be shown

### Requirement: Preview Validation
The preview step SHALL validate document parsing before proceeding to build.

#### Scenario: User identifies parsing issues
GIVEN the preview shows incorrectly parsed documents
WHEN the user reviews the preview
THEN they SHALL be able to return to Sources step
AND adjust filters or extraction settings
AND re-preview the results

### Requirement: Metadata Display
The preview SHALL display extracted metadata for validation.

#### Scenario: User verifies URL extraction
GIVEN documents contain inline URLs
WHEN viewing the preview
THEN extracted URLs SHALL be displayed for sample documents
AND dates parsed from filenames SHALL be shown
AND any parsing errors SHALL be highlighted