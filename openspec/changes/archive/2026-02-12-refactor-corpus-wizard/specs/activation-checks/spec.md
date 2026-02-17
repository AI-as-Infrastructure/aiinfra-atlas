# Activation Checks

## ADDED Requirements

### Requirement: Pre-activation Validation
The activation step SHALL validate the corpus before making it active.

#### Scenario: User activates a new corpus
GIVEN a corpus build has completed
WHEN the user reaches the activation step
THEN a test query SHALL be automatically executed
AND results SHALL be displayed for verification
AND corpus statistics SHALL be shown

### Requirement: Activation Confirmation
The activation step SHALL require explicit confirmation before switching corpora.

#### Scenario: User confirms activation
GIVEN the pre-activation checks pass
WHEN the user reviews the validation results
THEN they SHALL see a comparison with the current active corpus
AND a confirmation button SHALL be available
AND activation SHALL only proceed after confirmation

### Requirement: Rollback Capability
The activation step SHALL provide rollback information.

#### Scenario: User needs to rollback
GIVEN a new corpus has been activated
WHEN viewing the activation confirmation
THEN instructions for rollback SHALL be displayed
AND the previous corpus identifier SHALL be shown
AND rollback commands SHALL be provided