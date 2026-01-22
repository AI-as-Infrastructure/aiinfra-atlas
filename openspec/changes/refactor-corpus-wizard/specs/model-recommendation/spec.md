# Capability: Embedding Model Recommendation

## ADDED Requirements

### Requirement: Time-period based model selection
The system SHALL recommend embedding models based on the corpus time period and material type.

#### Scenario: Recommend model for historical corpus
GIVEN a corpus from 1825-1882 containing personal correspondence
WHEN the system recommends embedding models
THEN it suggests:
  - Primary: Livingwithmachines/bert_1760_1900 (95% match)
  - Alternative: Livingwithmachines/bert_1890_1900 (70% match)
  - Fallback: sentence-transformers/all-MiniLM-L6-v2 (60% match)
AND explains each recommendation:
  - "Trained on period-appropriate texts"
  - "Optimized for Victorian prose style"
  - "General purpose fallback"

#### Scenario: Recommend model for modern corpus
GIVEN a corpus from 2000-2024 containing academic papers
WHEN the system recommends embedding models
THEN it suggests:
  - Primary: sentence-transformers/all-mpnet-base-v2
  - Alternative: allenai/scibert_scivocab_uncased
  - Domain-specific: PubMedBERT (if medical)
AND provides performance characteristics for each

### Requirement: Model testing with corpus samples
The system SHALL allow users to test embedding models with actual corpus content before selection.

#### Scenario: Test model with random samples
GIVEN a user wants to verify model suitability
WHEN they click "Test with corpus sample"
THEN the system:
  - Extracts 5 random passages from the corpus
  - Generates embeddings with each candidate model
  - Measures semantic similarity preservation
  - Shows processing time per document
  - Displays quality metrics
AND the user can test with different samples

#### Scenario: Compare model performance
GIVEN multiple models are being considered
WHEN the user runs comparison tests
THEN the system displays:
  - Side-by-side quality metrics
  - Processing speed differences
  - Memory requirements
  - Semantic similarity scores
  - Recommendation confidence
AND highlights the best performer for the corpus

### Requirement: Custom model support
The system SHALL allow users to specify custom embedding models beyond the recommended options.

#### Scenario: Use custom HuggingFace model
GIVEN a user has a specialized embedding model
WHEN they enter a HuggingFace model ID
THEN the system:
  - Validates the model exists and is accessible
  - Downloads model metadata
  - Checks compatibility with the system
  - Allows testing with corpus samples
  - Warns if model characteristics don't match corpus
AND proceeds with the custom model if validation passes

### Requirement: Model-corpus compatibility warnings
The system SHALL warn users when selected models may not be optimal for their corpus.

#### Scenario: Warn about period mismatch
GIVEN a user selects a modern model for historical text
WHEN they proceed to build
THEN the system warns:
  "Selected model was trained on modern text (post-2000) but your corpus is from 1825-1882. This may result in suboptimal search quality."
AND offers to return to model selection
AND allows override with acknowledgment

## MODIFIED Requirements

### Requirement: Embedding configuration
The system SHALL configure embedding parameters based on model characteristics and corpus type rather than using fixed values.

#### Scenario: Auto-configure chunking for model
GIVEN a model with specific token limits
WHEN configuring the embedding pipeline
THEN the system:
  - Sets chunk_size based on model's max tokens
  - Adjusts overlap for corpus density
  - Optimizes batch size for memory
  - Configures pooling strategy
AND displays these settings for user review