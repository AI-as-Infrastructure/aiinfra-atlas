## ADDED Requirements

### Requirement: Cloudflare Access JWT Validation
When `AUTH_METHOD=cloudflare`, the system SHALL validate the `Cf-Access-Jwt-Assertion` JWT header using Cloudflare's public keys before trusting user identity. The system SHALL verify the JWT signature (RS256), audience claim (`CLOUDFLARE_ACCESS_AUD`), issuer (`CLOUDFLARE_TEAM_DOMAIN`), and token expiry. If JWT validation fails, the request SHALL be treated as unauthenticated.

#### Scenario: Valid Cloudflare JWT
- **WHEN** a request includes a valid `Cf-Access-Jwt-Assertion` header with correct audience and non-expired signature
- **THEN** the system extracts user identity from the JWT claims and proceeds with the authenticated request

#### Scenario: Missing or invalid JWT
- **WHEN** a request is missing the `Cf-Access-Jwt-Assertion` header or the JWT fails validation (wrong audience, expired, bad signature)
- **THEN** the system treats the request as unauthenticated and returns 401 for protected endpoints

#### Scenario: Key rotation
- **WHEN** JWT validation fails due to an unknown key ID
- **THEN** the system re-fetches Cloudflare's public keys once and retries validation before rejecting the request

#### Scenario: JWT validation disabled
- **WHEN** `CLOUDFLARE_TEAM_DOMAIN` or `CLOUDFLARE_ACCESS_AUD` is not configured
- **THEN** the system falls back to header-trust mode with a warning log, preserving backward compatibility

### Requirement: API Rate Limiting
The system SHALL enforce per-IP rate limiting on LLM query endpoints to prevent abuse and control API costs. The rate limit SHALL be configurable via the `RATE_LIMIT_PER_MINUTE` environment variable.

#### Scenario: Request within rate limit
- **WHEN** a client sends requests to `/api/ask/stream` or `/api/ask/async` within the configured rate limit
- **THEN** the system processes the requests normally

#### Scenario: Rate limit exceeded
- **WHEN** a client exceeds the configured requests per minute for query endpoints
- **THEN** the system returns HTTP 429 with a `Retry-After` header and does not forward the request to the LLM

#### Scenario: Cloudflare real IP detection
- **WHEN** requests arrive through a Cloudflare tunnel
- **THEN** the rate limiter uses the `Cf-Connecting-IP` header to identify the real client IP rather than the localhost proxy address

### Requirement: Restricted CORS Policy
The system SHALL restrict CORS to only the HTTP methods and headers required by the frontend application, rather than allowing all methods and headers.

#### Scenario: Allowed request
- **WHEN** a cross-origin request uses GET, POST, or OPTIONS with standard ATLAS headers (Content-Type, Authorization, X-Telemetry-Opt-In, X-Trace-Id, X-Request-Id)
- **THEN** the system includes appropriate CORS headers in the response

#### Scenario: Disallowed method
- **WHEN** a cross-origin request uses PUT, DELETE, PATCH, or other non-standard methods
- **THEN** the preflight response does not include the method in `Access-Control-Allow-Methods`

### Requirement: Nginx Origin Verification
When deployed behind Cloudflare, the nginx reverse proxy SHALL verify that requests originated from the Cloudflare edge before forwarding to the backend.

#### Scenario: Request from Cloudflare
- **WHEN** a request arrives at nginx with the `Cf-Ray` header present (set by Cloudflare on all proxied requests)
- **THEN** nginx forwards the request to the gunicorn backend

#### Scenario: Direct request bypassing Cloudflare
- **WHEN** a request arrives at nginx without the `Cf-Ray` header
- **THEN** nginx returns HTTP 403 and does not forward the request

### Requirement: Sanitised Error Responses
The system SHALL NOT expose implementation details (provider names, environment variable names, internal architecture) in error responses returned to clients. Detailed error information SHALL be logged server-side only.

#### Scenario: LLM provider configuration error
- **WHEN** an LLM API key is missing or invalid
- **THEN** the client receives a generic error message (e.g., "LLM provider configuration error") and the server log contains the specific provider and variable name

#### Scenario: Internal service error
- **WHEN** an internal service (Redis, queue) is unavailable
- **THEN** the client receives a generic 503 "Service temporarily unavailable" message without naming the specific service

### Requirement: Deploy Script Security Verification
The Cloudflare deployment script SHALL verify security prerequisites before starting application services.

#### Scenario: Firewall verification
- **WHEN** the deployment script runs
- **THEN** it verifies that UFW blocks inbound connections to port 8000 and warns the operator if the rule is missing

#### Scenario: Service dependency
- **WHEN** the gunicorn systemd service starts
- **THEN** it requires the cloudflared service to be active, ensuring the tunnel is running before the backend accepts requests
