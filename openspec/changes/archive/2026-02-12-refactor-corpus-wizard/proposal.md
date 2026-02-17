# Refactor Corpus Wizard Workflow

## Summary
Simplify and improve the corpus configuration wizard workflow to be more intuitive and user-friendly, with clearer separation of concerns and better progress visibility.

## Problem
The current corpus wizard has 7 steps with unclear flow:
- "Requirements" step is ambiguous and unnecessary
- Filters are a separate step but should be part of source configuration
- No preview/validation before building
- Model selection is overly complex
- Missing progress indicators during build
- No pre-activation validation

## Solution
Restructure the wizard into a cleaner workflow with:
1. **Workflow Type Selection**: Choose between Text or XML processing
2. **Metadata**: Simplified to essential fields (title, description, copyright, DOI)
3. **Sources**: Integrated directory structure, filters, URL extraction, and date parsing
4. **Preview/Validation**: New step to review discovered documents before proceeding
5. **Model Selection**: Simplified to default model + custom Hugging Face option with chunk settings
6. **Build**: Enhanced with progress visibility and error reporting
7. **Activate**: Pre-activation checks and validation

## Capabilities
- `corpus-wizard-workflow`: Restructured wizard flow and navigation
- `metadata-collection`: Simplified metadata fields
- `source-configuration`: Integrated source selection with filtering and extraction
- `document-preview`: New preview and validation step
- `model-selection`: Simplified embedding model selection
- `build-progress`: Enhanced build monitoring
- `activation-checks`: Pre-activation validation

## Dependencies
- Existing corpus builder backend modules
- Current metadata extractor and URL builder modules
- Hugging Face embeddings integration

## Risks & Mitigations
- **Risk**: Breaking existing corpus configurations
  - **Mitigation**: Maintain backward compatibility with existing configs
- **Risk**: User confusion during migration
  - **Mitigation**: Clear documentation and migration guide

## Validation
- Unit tests for each wizard step
- Integration test for complete workflow
- Manual testing with sample corpora
- Validation against existing corpus configurations