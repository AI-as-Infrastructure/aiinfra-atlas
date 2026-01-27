# Corpus Wizard Workflow

## ADDED Requirements

### Requirement: Workflow Type Selection
The wizard SHALL provide an initial step to select between Text and XML processing workflows.

#### Scenario: User selects text workflow
GIVEN the user starts the corpus wizard
WHEN they are on the first step
THEN they SHALL see options for "Text" and "XML" workflows
AND selecting "Text" SHALL configure the wizard for text document processing

### Requirement: Seven-Step Workflow
The wizard SHALL follow a seven-step workflow for text processing: Workflow Type, Metadata, Sources, Preview, Model, Build, Activate.

#### Scenario: User navigates through wizard
GIVEN the user has selected text workflow
WHEN they proceed through the wizard
THEN they SHALL progress through exactly 7 steps in order
AND each step SHALL validate before allowing progression

## MODIFIED Requirements

### Requirement: Step Navigation
The wizard SHALL prevent forward navigation until the current step is valid.

#### Scenario: User tries to skip ahead
GIVEN the user is on the metadata step with incomplete data
WHEN they try to navigate to the sources step
THEN the navigation SHALL be blocked
AND validation errors SHALL be displayed

## REMOVED Requirements

### Requirement: Requirements Step
The separate "Requirements" step SHALL be removed from the workflow.

#### Scenario: Simplified workflow
GIVEN the wizard workflow
WHEN displaying available steps
THEN there SHALL be no "Requirements" step
AND system requirements SHALL be checked automatically in the background