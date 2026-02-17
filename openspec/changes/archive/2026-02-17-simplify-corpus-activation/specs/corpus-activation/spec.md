# Corpus Activation

## MODIFIED Requirements

### Requirement: Direct Corpus Building
The corpus builder SHALL build directly in the final location without staging directories.

#### Scenario: User builds a new corpus
GIVEN a user completes corpus configuration
WHEN they start the build process
THEN the corpus SHALL be built directly in `backend/corpus/`
AND no temporary or staging directory SHALL be created
AND the corpus SHALL be immediately available for use after build completes

### Requirement: Overwrite Warning
The system SHALL warn users before overwriting an existing corpus.

#### Scenario: User builds with existing corpus present
GIVEN an existing corpus is present in `backend/corpus/`
WHEN the user initiates a new build
THEN the system SHALL display existing corpus metadata
AND SHALL require explicit confirmation to proceed
AND SHALL warn that the existing corpus will be overwritten with no automatic backup

#### Scenario: User builds with no existing corpus
GIVEN no corpus exists in `backend/corpus/`
WHEN the user initiates a build
THEN the build SHALL proceed without warnings
AND SHALL create corpus files directly in the target directory

### Requirement: Immediate Availability
Corpus files SHALL be immediately available after build completion.

#### Scenario: Build completes successfully
GIVEN a corpus build has completed
WHEN the build process finishes
THEN all corpus files SHALL exist in `backend/corpus/`
AND the manifest.json SHALL be present
AND the vector store SHALL be fully persisted
AND test search SHALL work immediately
AND .env configuration SHALL be updated automatically

## REMOVED Requirements

### Requirement: ~~Pre-activation Validation~~
~~The activation step SHALL validate the corpus before making it active.~~

**Rationale**: Activation step is removed. Validation happens via test search during build completion.

### Requirement: ~~Activation Confirmation~~
~~The activation step SHALL require explicit confirmation before switching corpora.~~

**Rationale**: No separate activation step. Confirmation happens before build starts.

### Requirement: ~~Rollback Capability~~
~~The activation step SHALL provide rollback information.~~

**Rationale**: Manual backups are user responsibility. Automatic rollback removed for simplicity.

## ADDED Requirements

### Requirement: Main App Integration
The build completion view SHALL direct users to test via the main application.

#### Scenario: User completes build and wants to test
GIVEN a corpus build has completed
WHEN the user views build completion
THEN validation SHALL confirm files exist and are structured correctly
AND a message SHALL direct the user to the main application
AND the corpus SHALL be immediately usable in the main app
AND no separate test interface SHALL be provided in the wizard

### Requirement: Configuration Update
The system SHALL automatically update environment configuration after successful build.

#### Scenario: Build completes with target configuration
GIVEN a corpus build completes successfully
AND a target configuration was provided
WHEN the build finishes
THEN TEST_TARGET SHALL be updated in all .env files
AND the target configuration file SHALL be created
AND the system SHALL be ready to use the new corpus immediately
