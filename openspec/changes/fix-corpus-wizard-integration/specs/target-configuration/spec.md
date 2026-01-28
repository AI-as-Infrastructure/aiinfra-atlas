# Target Configuration Specification

## Overview

This specification defines how the corpus wizard generates and manages target configuration files that enable the query system to function with newly built corpora.

## ADDED Requirements

### Requirement: Wizard SHALL generate target configuration file

The corpus wizard must create at least one target configuration file during the validation phase to ensure queries work immediately after activation.

#### Scenario: Generating default target configuration

Given a corpus has been built and validated
When the user completes the validation step
Then a target configuration file named `k20_claude4.txt` should be created
And it should contain sensible defaults for the corpus
And be placed in the backend/targets/ directory

#### Scenario: Target configuration with correct settings

Given a target configuration is being generated
When the file is created
Then it should include:
- Correct LLM provider and model settings
- Appropriate search parameters (k=20 for k20_claude4)
- Reference to the correct retriever and vector store
- Embedding model matching the corpus

### Requirement: Wizard SHALL provide target management UI

The wizard interface must inform users about target configurations and how to customize them.

#### Scenario: Displaying target information

Given the wizard validation step is complete
When the target configuration is generated
Then the UI should display:
- The name of the generated target file
- Basic information about its settings
- Instructions for creating additional targets

#### Scenario: Target customization guidance

Given a user wants to create custom targets
When they view the validation results
Then they should see documentation on:
- The target file format
- Available parameters and their effects
- How to create variations (e.g., k10_gpt4, k5_llama)

### Requirement: System SHALL clean up obsolete targets

The system should remove target files that are no longer valid or needed.

#### Scenario: Removing old target files

Given the targets directory contains obsolete files
When a new corpus is activated
Then any target files without corresponding corpora should be identified
And optionally removed or archived
And the user should be notified of the cleanup

## MODIFIED Requirements

### Requirement: Target loading must handle missing files gracefully

The base target system must provide clear error messages when target files are missing.

#### Scenario: Missing target file error

Given TEST_TARGET is set to a non-existent target
When the system attempts to load it
Then it should provide a clear error message
And suggest available targets
And indicate how to create the missing target