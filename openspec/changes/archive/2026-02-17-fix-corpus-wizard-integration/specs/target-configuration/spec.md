# Target Configuration Specification

## Overview

This specification defines how the corpus wizard generates and manages target configuration files that enable the query system to function with newly built corpora. The unified configuration system combines settings from multiple sources (manifest.json, target .txt files, and environment variables) and is critical for:

- Query execution and retrieval
- UI display in TestTargetBox component
- Telemetry tracking in Phoenix for performance analysis
- Creating the composite_target identifier used throughout the system

## ADDED Requirements

### Requirement: Wizard SHALL provide target configuration UI

The corpus wizard SHALL include a configuration page where users can define the default test target settings, with sensible defaults suggested from k20_claude4 configuration.

#### Scenario: Target configuration page in wizard

Given a corpus has been built and validated
When the user reaches the target configuration step
Then a configuration UI should be displayed with:
- LLM provider selection (defaulting to ANTHROPIC)
- Model selection (defaulting to claude-3-sonnet-20240229)
- Search parameters (k value defaulting to 20)
- Score threshold settings (defaulting to 0.5)
- Citation limit settings (defaulting to 10)
And the user can modify these values before proceeding

#### Scenario: Generating target from user configuration

Given the user has configured target settings in the wizard
When they confirm the configuration
Then a target configuration file should be created
And it should contain the user's selected settings
And be placed in the backend/targets/ directory with appropriate naming

### Requirement: Wizard SHALL display unified configuration

The wizard SHALL display a unified test configuration that combines both corpus creation settings and test target settings in a single view.

#### Scenario: Displaying unified configuration

Given the user has completed both corpus and target configuration
When viewing the test target UI box
Then it should display:
- Corpus configuration (embedding model, vector store, collection name)
- Target configuration (LLM provider, model, search parameters)
- Processing configuration (chunk size, overlap from corpus creation)
- Complete composite target identifier
And all settings should be shown in a cohesive format

#### Scenario: Configuration review before activation

Given the user is about to activate the corpus
When they review the configuration
Then they should see:
- All corpus-related settings from the build process
- All target-related settings they configured
- The final target file name that will be created
- Any warnings about incompatible settings

### Requirement: Configuration SHALL maintain telemetry compatibility

The generated target configuration SHALL include all fields required by the telemetry system to ensure proper tracking and analysis in Phoenix.

#### Scenario: Telemetry fields are complete

Given a target configuration is generated
When the unified configuration is loaded by TargetConfig class
Then it should include all required telemetry fields:
- composite_target (TEST_TARGET + CHROMA_COLLECTION_NAME)
- atlas_version, target_version, target_id
- llm_provider, llm_model
- search parameters (search_k, search_type, search_score_threshold)
- embedding_model, chunk_size, chunk_overlap
And these fields should be tracked correctly in Phoenix telemetry

#### Scenario: Unified configuration integrity

Given the corpus wizard generates both manifest.json and target .txt files
When the TargetConfig class merges these sources
Then the unified configuration should:
- Correctly merge settings from all three sources (env, manifest, target)
- Generate a valid composite_target identifier
- Be accessible via /api/config endpoint
- Display correctly in TestTargetBox UI component
- Be fully captured in telemetry attributes

### Requirement: System SHALL clean up obsolete targets

The system SHALL remove target files that are no longer valid or needed.

#### Scenario: Removing old target files

Given the targets directory contains obsolete files
When a new corpus is activated
Then any target files without corresponding corpora should be identified
And optionally removed or archived
And the user should be notified of the cleanup

## MODIFIED Requirements

### Requirement: Target loading SHALL handle missing files gracefully

The base target system SHALL provide clear error messages when target files are missing.

#### Scenario: Missing target file error

Given TEST_TARGET is set to a non-existent target
When the system attempts to load it
Then it should provide a clear error message
And suggest available targets
And indicate how to create the missing target