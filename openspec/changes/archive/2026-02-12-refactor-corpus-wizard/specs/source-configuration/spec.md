# Source Configuration

## MODIFIED Requirements

### Requirement: Integrated Source and Filter Configuration
The source step SHALL integrate directory selection, filtering, and extraction options in a single interface.

#### Scenario: User configures local directory source
GIVEN the user is on the source configuration step
WHEN configuring a local directory source
THEN directory path input SHALL be available
AND file extension filters SHALL be configurable
AND subdirectory inclusion SHALL be selectable
AND all options SHALL be on the same screen

### Requirement: Inline URL Extraction
The source configuration SHALL include an option for extracting URLs from the first line of documents.

#### Scenario: User enables URL extraction
GIVEN documents contain URLs in the first line
WHEN configuring sources
THEN a checkbox for "Extract URL from first line" SHALL be available
AND when checked, URL extraction SHALL be enabled
AND the URL format SHALL be validated

### Requirement: Date Extraction from Filenames
The source configuration SHALL support date extraction from properly formatted filenames.

#### Scenario: User configures date extraction
GIVEN filenames contain dates in a standard format
WHEN configuring sources
THEN date pattern options SHALL be available
AND common patterns SHALL be suggested (YYYY-MM-DD, DD-MM-YYYY)
AND custom patterns SHALL be supported