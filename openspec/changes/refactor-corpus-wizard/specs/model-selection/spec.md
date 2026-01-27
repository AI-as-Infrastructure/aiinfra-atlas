# Model Selection

## MODIFIED Requirements

### Requirement: Simplified Model Selection
The model selection step SHALL offer a default model and custom Hugging Face model option.

#### Scenario: User selects default model
GIVEN the user is on the model selection step
WHEN they view available options
THEN they SHALL see a default model (sentence-transformers/all-MiniLM-L6-v2)
AND a custom model input field for Hugging Face model IDs
AND the default SHALL be pre-selected

### Requirement: Chunk Configuration
The model selection step SHALL include chunk size and overlap settings with sensible defaults.

#### Scenario: User configures chunking
GIVEN the user is on the model selection step
WHEN they view chunking options
THEN chunk size SHALL default to 1000 characters
AND chunk overlap SHALL default to 200 characters
AND both values SHALL be editable

### Requirement: Model Information Display
The model selection SHALL display model characteristics.

#### Scenario: User views model details
GIVEN the user selects a model
WHEN the selection is made
THEN embedding dimensions SHALL be displayed
AND model size SHALL be shown
AND download status SHALL be indicated