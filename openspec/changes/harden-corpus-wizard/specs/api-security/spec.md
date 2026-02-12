# Capability: API Security for Corpus Wizard

## ADDED Requirements

### Requirement: Authentication for sensitive endpoints
The system SHALL use existing Cognito authentication for configuration and corpus management endpoints.

#### Scenario: Enable authentication via Cognito toggle
- **GIVEN** the system has `VITE_USE_COGNITO_AUTH=true` in environment
- **WHEN** a request is made to a protected endpoint without valid JWT
- **THEN** the system returns HTTP 401 Unauthorized
- **AND** the response body contains a generic error message

#### Scenario: Protected endpoints require authentication
- **GIVEN** Cognito authentication is enabled
- **WHEN** a request is made to any of these endpoints:
  - POST `/api/configuration/import`
  - GET `/api/configuration/export`
  - POST `/api/corpus-wizard/build`
  - POST `/api/corpus-wizard/add-target`
  - POST `/api/corpus-wizard/update-target/{target_id}`
  - DELETE `/api/corpus-wizard/delete-target/{target_id}`
  - POST `/api/corpus-wizard/set-default-target/{target_id}`
- **THEN** the system validates the JWT against AWS Cognito JWKS
- **AND** unauthenticated requests are rejected with HTTP 401

#### Scenario: Authentication disabled for development
- **GIVEN** the system has `VITE_USE_COGNITO_AUTH=false` or unset
- **WHEN** a request is made to any endpoint
- **THEN** the request is processed with an anonymous user context
- **AND** this allows local development without Cognito setup

### Requirement: Safe error responses
The system SHALL return generic error messages to clients while logging detailed errors internally.

#### Scenario: Hide internal paths in errors
- **GIVEN** an operation fails due to a file system error
- **WHEN** the error is returned to the client
- **THEN** the response contains a generic message like "Operation failed"
- **AND** the full error with file paths is logged server-side
- **AND** the response does not expose internal directory structure

#### Scenario: Hide stack traces in errors
- **GIVEN** an unexpected exception occurs during request processing
- **WHEN** the error is returned to the client
- **THEN** the response contains HTTP 500 with generic message
- **AND** the full stack trace is logged server-side
- **AND** the response does not include exception details or line numbers

#### Scenario: Log errors with context
- **GIVEN** any error occurs during API request processing
- **WHEN** the error is logged
- **THEN** the log entry includes:
  - Full exception message and type
  - Stack trace (for unexpected errors)
  - Request context (endpoint, parameters)
  - Timestamp
- **AND** sensitive data (credentials, tokens) is redacted from logs
