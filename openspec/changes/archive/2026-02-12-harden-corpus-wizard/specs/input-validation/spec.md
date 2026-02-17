# Capability: Input Validation for Corpus Wizard

## ADDED Requirements

### Requirement: Path traversal prevention
The system SHALL validate all user-provided file paths to prevent directory traversal attacks.

#### Scenario: Reject parent directory references
- **GIVEN** a user provides a path containing `../` sequences
- **WHEN** the system validates the path
- **THEN** the request is rejected with HTTP 400 Bad Request
- **AND** the response indicates "Invalid path"
- **AND** no file system access occurs outside allowed directories

#### Scenario: Reject URL-encoded traversal
- **GIVEN** a user provides a path with URL-encoded traversal like `%2e%2e%2f`
- **WHEN** the system validates the path
- **THEN** the path is URL-decoded before validation
- **AND** the traversal attempt is detected and rejected
- **AND** the request returns HTTP 400 Bad Request

#### Scenario: Validate resolved path within bounds
- **GIVEN** a user provides a path that resolves outside the allowed base directory
- **WHEN** the system validates the path
- **THEN** the path is resolved to its absolute form (following symlinks)
- **AND** the resolved path is checked against the allowed base directory
- **AND** paths outside the base are rejected with HTTP 400

#### Scenario: Source path validation
- **GIVEN** a user specifies a source location for corpus analysis or preview
- **WHEN** the request reaches `/api/corpus-wizard/analyze` or `/api/corpus-wizard/preview`
- **THEN** the source path is validated before any file system access
- **AND** only paths within the project directory or explicitly allowed locations are permitted

### Requirement: URL parameter validation
The system SHALL validate all URL path parameters to prevent injection attacks.

#### Scenario: Validate target_id format
- **GIVEN** a request to `/api/corpus-wizard/update-target/{target_id}` or `/api/corpus-wizard/delete-target/{target_id}`
- **WHEN** the target_id contains characters other than alphanumeric, underscore, or hyphen
- **THEN** the request is rejected with HTTP 400 Bad Request
- **AND** no file system operation is attempted
- **AND** the response indicates "Invalid target ID format"

#### Scenario: Validate corpus_id format
- **GIVEN** a request includes a corpus identifier
- **WHEN** the identifier contains path separators or special characters
- **THEN** the request is rejected with HTTP 400 Bad Request
- **AND** the identifier is not used in file paths

### Requirement: Environment file write sanitization
The system SHALL sanitize all user input before writing to environment or configuration files.

#### Scenario: Sanitize display name for env file
- **GIVEN** a corpus build completes and updates the site title in `.env`
- **WHEN** the display_name contains newlines, quotes, or shell metacharacters
- **THEN** dangerous characters are escaped or removed
- **AND** the resulting env file is valid and parseable
- **AND** no command injection is possible via the display_name

#### Scenario: Reject invalid display names
- **GIVEN** a corpus configuration includes a display_name
- **WHEN** the name contains only special characters or is empty
- **THEN** the system uses a safe default value
- **AND** a warning is logged about the invalid input

### Requirement: GitHub URL validation
The system SHALL validate GitHub repository URLs before cloning or fetching content.

#### Scenario: Validate GitHub domain
- **GIVEN** a user provides a repository URL for corpus source
- **WHEN** the URL host is not `github.com` or `www.github.com`
- **THEN** the request is rejected with HTTP 400
- **AND** the response indicates only GitHub repositories are supported

#### Scenario: Validate repository path parameter
- **GIVEN** a user specifies a subdirectory path within a GitHub repository
- **WHEN** the path contains `../` or attempts to access parent directories
- **THEN** the path is validated and sanitized
- **AND** traversal attempts are rejected

### Requirement: Regex pattern validation
The system SHALL validate user-provided regex patterns for safety and correctness.

#### Scenario: Detect ReDoS patterns
- **GIVEN** a user provides a regex pattern for date extraction or filtering
- **WHEN** the pattern contains potentially catastrophic backtracking constructs
- **THEN** the system applies a compilation timeout
- **AND** patterns that exceed the timeout are rejected
- **AND** the response indicates the pattern is too complex

#### Scenario: Validate regex syntax
- **GIVEN** a user provides an invalid regex pattern
- **WHEN** the system attempts to compile the pattern
- **THEN** compilation errors are caught gracefully
- **AND** a clear error message is returned indicating the syntax issue
- **AND** the error does not expose internal implementation details
