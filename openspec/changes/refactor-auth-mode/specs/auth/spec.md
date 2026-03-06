# Auth

## ADDED Requirements

### Requirement: Tri-Modal Authentication
The system MUST support three authentication modes selected by the `AUTH_METHOD` environment variable: `cognito`, `cloudflare`, and `none`. Exactly one mode MUST be active per deployment.

#### Scenario: Cognito mode
- **WHEN** `AUTH_METHOD` is set to `cognito`
- **THEN** the backend validates JWT tokens from the `Authorization: Bearer` header using AWS Cognito JWKS
- **AND** the Cognito `sub` claim is used as the identity input for anonymous ID generation
- **AND** the frontend injects Cognito JWT tokens into API requests
- **AND** behaviour is identical to the current `VITE_USE_COGNITO_AUTH=true` mode

#### Scenario: Cloudflare mode
- **WHEN** `AUTH_METHOD` is set to `cloudflare`
- **THEN** the backend extracts user identity from the `Cf-Access-Authenticated-User-Email` header
- **AND** the email address is used as the identity input for anonymous ID generation
- **AND** the frontend does not inject any authentication tokens
- **AND** Cloudflare Access handles authentication at the edge transparently

#### Scenario: None mode
- **WHEN** `AUTH_METHOD` is set to `none`
- **THEN** the backend does not require or validate any authentication credentials
- **AND** all users are treated as anonymous with `sub` set to `anonymous`
- **AND** the frontend does not inject any authentication tokens
- **AND** behaviour is identical to the current `VITE_USE_COGNITO_AUTH=false` mode

#### Scenario: Default mode
- **WHEN** `AUTH_METHOD` is not set in the environment
- **AND** `VITE_USE_COGNITO_AUTH` is not set
- **THEN** the system defaults to `none` mode

### Requirement: Backward Compatibility with VITE_USE_COGNITO_AUTH
The system MUST support the deprecated `VITE_USE_COGNITO_AUTH` variable during the transition period, mapping it to the new `AUTH_METHOD` modes.

#### Scenario: Legacy true mapping
- **WHEN** `AUTH_METHOD` is not set
- **AND** `VITE_USE_COGNITO_AUTH` is set to `true`
- **THEN** the system operates in `cognito` mode
- **AND** a deprecation warning is logged at startup

#### Scenario: Legacy false mapping
- **WHEN** `AUTH_METHOD` is not set
- **AND** `VITE_USE_COGNITO_AUTH` is set to `false`
- **THEN** the system operates in `none` mode
- **AND** a deprecation warning is logged at startup

#### Scenario: AUTH_METHOD takes precedence
- **WHEN** both `AUTH_METHOD` and `VITE_USE_COGNITO_AUTH` are set
- **THEN** `AUTH_METHOD` takes precedence
- **AND** `VITE_USE_COGNITO_AUTH` is ignored

### Requirement: Cloudflare Access Header Trust Model
The system MUST trust the `Cf-Access-Authenticated-User-Email` header without additional verification when `AUTH_METHOD=cloudflare`, relying on the Cloudflare tunnel as the trust boundary.

#### Scenario: Valid Cloudflare header
- **WHEN** a request arrives with `AUTH_METHOD=cloudflare`
- **AND** the `Cf-Access-Authenticated-User-Email` header is present
- **THEN** the header value is accepted as the authenticated user's email
- **AND** no additional token verification is performed

#### Scenario: Missing Cloudflare header
- **WHEN** a request arrives with `AUTH_METHOD=cloudflare`
- **AND** the `Cf-Access-Authenticated-User-Email` header is absent
- **THEN** the user is treated as unauthenticated
- **AND** auth-gated endpoints return an appropriate error

### Requirement: Unified Authentication Interface
The backend auth module MUST provide a single `get_authenticated_user(request)` function that returns a consistent user dictionary regardless of auth mode.

#### Scenario: Consistent user dict format
- **WHEN** `get_authenticated_user(request)` is called
- **THEN** it returns a dictionary with keys: `sub`, `username`, `authenticated`, `auth_method`
- **AND** `sub` contains the identity string (Cognito sub, email, or `anonymous`)
- **AND** `authenticated` is `True` when identity was verified, `False` otherwise
- **AND** `auth_method` reflects the active mode (`cognito`, `cloudflare`, or `none`)

#### Scenario: Non-throwing variant
- **WHEN** `optional_authenticated_user(request)` is called
- **AND** authentication fails or is unavailable
- **THEN** it returns `{"sub": "anonymous", "username": "anonymous", "authenticated": False, "auth_method": "<active-mode>"}`
- **AND** no exception is raised

### Requirement: Anonymous ID Generation from Any Auth Mode
The anonymous ID service MUST generate consistent, privacy-preserving IDs from any stable identity string, not only Cognito UUIDs.

#### Scenario: Cognito sub input
- **WHEN** `generate_anonymous_id()` receives a Cognito sub (UUID)
- **THEN** it produces `anon_<16-char-hash>` using SHA-256 with the environment salt

#### Scenario: Email input
- **WHEN** `generate_anonymous_id()` receives an email address
- **THEN** it produces `anon_<16-char-hash>` using SHA-256 with the environment salt
- **AND** the same email always produces the same anonymous ID within the same environment

#### Scenario: Cross-mode isolation
- **WHEN** a Cognito sub and an email address refer to the same physical user
- **THEN** the anonymous IDs are different (different input strings produce different hashes)
- **AND** this is acceptable because deployments using different auth modes are separate environments

### Requirement: Frontend Auth Method Awareness
The frontend MUST read `VITE_AUTH_METHOD` to determine whether to inject Cognito JWT tokens into API requests.

#### Scenario: Cognito token injection
- **WHEN** `VITE_AUTH_METHOD` is `cognito`
- **THEN** the frontend loads the Cognito OAuth module
- **AND** injects `Authorization: Bearer <JWT>` headers into API requests

#### Scenario: Non-Cognito modes
- **WHEN** `VITE_AUTH_METHOD` is `cloudflare` or `none`
- **THEN** the frontend does not load the Cognito OAuth module
- **AND** no `Authorization` header is injected into API requests

### Requirement: Environment File Configuration
All environment files MUST include `AUTH_METHOD` and `VITE_AUTH_METHOD` variables with deployment-appropriate defaults.

#### Scenario: Development and feature environments
- **WHEN** `config/.env.development` or `config/.env.development.feature` is used
- **THEN** `AUTH_METHOD=none` and `VITE_AUTH_METHOD=none` are set

#### Scenario: Staging and production environments
- **WHEN** `config/.env.staging` or `config/.env.production` is used
- **THEN** `AUTH_METHOD=cognito` and `VITE_AUTH_METHOD=cognito` are set

#### Scenario: Cloudflare environment
- **WHEN** the env file has `AUTH_METHOD=cloudflare` (for Cloudflare Tunnel deployments)
- **THEN** `AUTH_METHOD=cloudflare` and `VITE_AUTH_METHOD=cloudflare` are set

#### Scenario: Template documentation
- **WHEN** `config/.env.template` is referenced
- **THEN** `AUTH_METHOD=none` and `VITE_AUTH_METHOD=none` are set as defaults
- **AND** a comment documents the three available modes
- **AND** `VITE_USE_COGNITO_AUTH` includes a deprecation notice
