# Capability: Code Quality Standards for Corpus Wizard

## ADDED Requirements

### Requirement: Encapsulated build progress state
The system SHALL manage build progress through a dedicated manager class rather than global state.

#### Scenario: Start a new build
- **GIVEN** a corpus build is initiated
- **WHEN** the build starts
- **THEN** the BuildProgressManager creates a new build record
- **AND** the record includes build_id, config, status, and timestamps
- **AND** concurrent builds are isolated from each other

#### Scenario: Update build progress
- **GIVEN** a build is in progress
- **WHEN** progress data is reported (document count, current file, etc.)
- **THEN** the BuildProgressManager updates the build record atomically
- **AND** concurrent update attempts are serialized via async lock
- **AND** the update is immediately visible to progress queries

#### Scenario: Query build progress
- **GIVEN** a client requests build progress
- **WHEN** the progress endpoint is called with a build_id
- **THEN** the BuildProgressManager returns the current state
- **AND** missing build_ids return None (not an error)
- **AND** the query does not modify state

#### Scenario: Complete a build
- **GIVEN** a build finishes (success or failure)
- **WHEN** the build is marked complete
- **THEN** the BuildProgressManager updates final status
- **AND** completion timestamp is recorded
- **AND** the build record is retained for client queries

### Requirement: Standardized exception handling
The system SHALL use consistent exception handling patterns throughout the corpus wizard.

#### Scenario: Catch specific exceptions
- **GIVEN** code may raise exceptions
- **WHEN** exceptions are caught
- **THEN** specific exception types are caught (not bare `except:`)
- **AND** `except Exception:` is used only when all exceptions should be handled
- **AND** `except:` (bare) is never used

#### Scenario: Handle exceptions consistently
- **GIVEN** an exception is caught
- **WHEN** the handler executes
- **THEN** one of these patterns is followed:
  - Re-raise: `raise` or `raise NewException() from e`
  - Log and continue: `logger.error(...); continue/return default`
  - Convert to HTTP error: `raise HTTPException(...)`
- **AND** exceptions are never silently swallowed with `pass`

#### Scenario: Propagate context with exceptions
- **GIVEN** an exception is caught and re-raised
- **WHEN** a new exception is raised
- **THEN** the original exception is chained using `from e`
- **AND** the full exception chain is available for debugging

### Requirement: Shared utility functions
The system SHALL use shared utility functions for common operations to avoid code duplication.

#### Scenario: Generate target configuration
- **GIVEN** a test target needs to be created or updated
- **WHEN** the target configuration content is generated
- **THEN** the `build_target_config_content()` utility is used
- **AND** all target operations use the same generation logic
- **AND** changes to the format require updating only one location

#### Scenario: Validate regex patterns
- **GIVEN** a regex pattern needs validation
- **WHEN** validation is performed
- **THEN** the `validate_regex_pattern()` utility is used
- **AND** validation logic is consistent across all call sites
- **AND** error messages follow the same format

#### Scenario: Validate file paths
- **GIVEN** a user-provided path needs validation
- **WHEN** validation is performed
- **THEN** the `validate_safe_path()` utility is used
- **AND** all path validation uses the same security checks
- **AND** the utility is imported from `path_validator` module

### Requirement: Module-level imports
The system SHALL place all import statements at module level, not inside functions.

#### Scenario: Import organization
- **GIVEN** a module requires external dependencies
- **WHEN** the module is loaded
- **THEN** all imports are at the top of the file
- **AND** imports are not repeated inside functions
- **AND** import errors are caught at module load time, not runtime

#### Scenario: Regex compilation
- **GIVEN** regex patterns are used multiple times
- **WHEN** the module is loaded
- **THEN** frequently-used patterns are pre-compiled at module level
- **AND** compiled patterns are reused rather than recompiled in loops
