# Capability: Embedding Model Selection

## ADDED Requirements

### Requirement: Default model with custom option
The system SHALL provide a recommended general-purpose embedding model and allow custom model selection from HuggingFace.

#### Scenario: Display default model recommendation
GIVEN a user is configuring their corpus
WHEN they reach the model selection step
THEN the system displays:
  - Default: sentence-transformers/all-MiniLM-L6-v2 (recommended)
  - Description: "General-purpose model suitable for most corpora"
  - Performance: "Fast processing with good accuracy"
  - Custom option: Input field for HuggingFace model ID
AND allows the user to proceed with either choice

#### Scenario: Use custom HuggingFace model
GIVEN a user wants to use a specific embedding model
WHEN they enter a HuggingFace model ID
THEN the system:
  - Validates the model exists and is accessible
  - Downloads model metadata
  - Checks compatibility with the system
  - Displays model characteristics (size, dimensions)
  - Allows testing with corpus samples
AND proceeds with the custom model if validation passes

### Requirement: Model testing with corpus samples
The system SHALL allow users to test embedding models with actual corpus content before final selection.

#### Scenario: Test model with corpus samples
GIVEN a user has selected a model (default or custom)
WHEN they click "Test with corpus sample"
THEN the system:
  - Extracts 5 random passages from the corpus
  - Generates embeddings with the selected model
  - Performs similarity searches within the sample
  - Shows processing time per document
  - Displays embedding quality metrics
AND allows the user to test with different samples

#### Scenario: Validate custom model compatibility
GIVEN a user enters a custom model ID
WHEN the system validates the model
THEN it checks:
  - Model exists on HuggingFace
  - Model type is compatible (sentence-transformers)
  - Model size fits within system resources
  - Embedding dimensions are supported
AND provides clear error messages if validation fails

### Requirement: Model performance estimation
The system SHALL provide performance estimates based on corpus size and selected model.

#### Scenario: Estimate processing time
GIVEN a model is selected and corpus analyzed
WHEN the user reviews model selection
THEN the system displays:
  - Estimated processing time (CPU vs GPU)
  - Memory requirements
  - Disk space for embeddings
  - Recommended batch size
  - Expected queries per second
AND updates estimates if model is changed

## MODIFIED Requirements

### Requirement: Embedding configuration
The system SHALL configure embedding parameters based on the selected model's characteristics.

#### Scenario: Auto-configure for selected model
GIVEN a model is selected (default or custom)
WHEN configuring the embedding pipeline
THEN the system:
  - Sets chunk_size based on model's max tokens
  - Configures batch size for available memory
  - Sets appropriate pooling strategy
  - Optimizes for model-specific requirements
AND displays these settings for user review

## REMOVED Requirements

### ~~Requirement: Time-period based model selection~~
~~The system SHALL recommend embedding models based on the corpus time period and material type.~~

**Rationale**: Simplified to a single general-purpose default model with custom option rather than complex time-period matching logic.