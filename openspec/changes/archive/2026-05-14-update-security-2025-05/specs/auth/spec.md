# auth Specification

## ADDED Requirements

### Requirement: Debug Endpoint Not Available in Production
The `/api/debug/user-id` endpoint MUST NOT be accessible in production environments.

#### Scenario: Debug endpoint returns 404 in production
- **WHEN** a request is made to `/api/debug/user-id`
- **AND** `ENVIRONMENT=production`
- **THEN** the response status code is 404
- **AND** no auth configuration info is returned

#### Scenario: Debug endpoint available in development
- **WHEN** a request is made to `/api/debug/user-id`
- **AND** `ENVIRONMENT=development`
- **THEN** the debug information is returned normally
