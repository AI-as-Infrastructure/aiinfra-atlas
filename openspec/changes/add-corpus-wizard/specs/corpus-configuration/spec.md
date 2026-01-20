# Capability: Corpus Configuration Management

## ADDED Requirements

### Requirement: Corpus metadata tracking
The system SHALL track comprehensive metadata for each corpus including name, time period, copyright status, DOI, and citation information.

#### Scenario: Researcher configures Darwin corpus
GIVEN a researcher is configuring the Darwin Correspondence corpus
WHEN they provide metadata including:
  - Time period: 1825-1882
  - Copyright: "Public domain with CC-BY transcriptions"
  - DOI: "10.5281/zenodo.1234567"
THEN the system stores this metadata in the corpus configuration
AND the metadata is displayed in the UI when the corpus is active
AND the metadata is included in exported configurations

### Requirement: GitHub repository support
The system SHALL support using GitHub repositories as corpus sources through both git operations and API access.

#### Scenario: Load corpus from public GitHub repository
GIVEN a researcher wants to use a corpus from GitHub
WHEN they provide the repository URL "https://github.com/AI-as-Infrastructure/aiinfra-atlas-darwin"
THEN the system clones or downloads the repository
AND identifies the corpus files within the repository structure
AND caches the download for subsequent operations

#### Scenario: Load corpus from private GitHub repository
GIVEN a researcher has a private GitHub repository
WHEN they provide the repository URL and a GitHub access token
THEN the system authenticates and downloads the repository
AND the token is stored securely in environment variables
AND the corpus is accessible for processing

### Requirement: Configuration persistence
The system SHALL save corpus configurations as portable YAML files that can be shared and reused.

#### Scenario: Export and import corpus configuration
GIVEN a researcher has configured a corpus successfully
WHEN they export the configuration
THEN a YAML file is created with all settings including metadata, filters, and model selection
AND another researcher can import this configuration to reproduce the same corpus setup
AND the configuration includes version information for compatibility checking

### Requirement: Atomic corpus swapping
The system SHALL perform corpus swaps atomically with automatic backup and rollback capabilities.

#### Scenario: Successful corpus swap
GIVEN a new corpus has been built successfully
WHEN the user activates the new corpus
THEN the current corpus is backed up with a timestamp
AND the new corpus is moved to the active location
AND the system restarts with the new corpus active
AND the backup is retained for recovery

#### Scenario: Failed corpus swap with rollback
GIVEN a corpus swap operation fails during activation
WHEN the failure is detected
THEN the system automatically restores from the backup
AND the user is notified of the failure and recovery
AND the system remains operational with the original corpus

## MODIFIED Requirements

### Requirement: Corpus discovery
The system SHALL discover corpus structure through both automatic analysis and user-provided metadata rather than hardcoded patterns.

#### Scenario: Metadata-driven discovery
GIVEN a user provides metadata about expected entities (people, places, topics)
WHEN the system analyzes the corpus structure
THEN it uses the metadata to guide filter discovery
AND prioritizes patterns matching the provided entities
AND suggests filters based on both structure and metadata