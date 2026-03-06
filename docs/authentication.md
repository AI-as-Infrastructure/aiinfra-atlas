# Authentication

ATLAS supports three authentication modes selected by the `AUTH_METHOD` environment variable:

| Mode | `AUTH_METHOD` | Description |
|------|--------------|-------------|
| **Cognito** | `cognito` | AWS Cognito JWT authentication (production, staging) |
| **Cloudflare** | `cloudflare` | Cloudflare Access header-based identity (Cloudflare Tunnel deployments) |
| **None** | `none` | No authentication (development, testing) |

**Key Features:**
- Tri-modal authentication dispatcher (`backend/modules/auth.py`)
- Anonymous user ID generation from any auth mode
- Required for inter-rater functionality (cognito or cloudflare)
- Cognito: JWT token validation with automatic Authorization header handling
- Cloudflare: Transparent identity via `Cf-Access-Authenticated-User-Email` header
- Session-agnostic user identification

## Configuration

Authentication mode is controlled via environment variables in your `.env` file:

### Auth Mode Selection
- **`AUTH_METHOD=none`**: No authentication (open access, development)
- **`AUTH_METHOD=cognito`**: AWS Cognito JWT authentication (required for inter-rater on non-Cloudflare deployments)
- **`AUTH_METHOD=cloudflare`**: Cloudflare Access header-based identity (Cloudflare Tunnel deployments)
- **`VITE_AUTH_METHOD`**: Derived automatically from `AUTH_METHOD` at build time (do not set manually)

### Deprecated (backward compatible)
- **`VITE_USE_COGNITO_AUTH=true|false`**: Mapped to `AUTH_METHOD=cognito|none` if `AUTH_METHOD` is not set. Logs a deprecation warning.

### Anonymous ID Configuration
- **`ANONYMOUS_ID_SALT`**: Environment-specific salt for generating anonymous user IDs
- **`ENVIRONMENT`**: Environment name (development/staging/production) for ID isolation

## AWS Cognito Setup

To enable authentication, you need to:

1. **Create a Cognito User Pool** in the AWS Cognito console
2. **Configure the Cognito environment variables** using the template provided in `config/.env.template`

### Required Cognito Variables (AUTH_METHOD=cognito only)

**Frontend Configuration:**
- **`VITE_AUTH_METHOD`**: Derived automatically from `AUTH_METHOD` at build time
- **`VITE_COGNITO_REGION`**: AWS region for your Cognito User Pool
- **`VITE_COGNITO_DOMAIN`**: Cognito domain URL
- **`VITE_COGNITO_USERPOOL_ID`**: User Pool ID
- **`VITE_COGNITO_CLIENT_ID`**: App Client ID
- **`VITE_COGNITO_LOGIN_REDIRECT_URI`**: Callback URL after login
- **`VITE_COGNITO_LOGOUT_REDIRECT_URI`**: Redirect URL after logout
- **`VITE_COGNITO_LOGOUT_ENDPOINT`**: Cognito logout endpoint
- **`VITE_COGNITO_OAUTH_SCOPE`**: OAuth scopes (typically `"openid email profile"`)

**Backend Configuration:**
- **`ANONYMOUS_ID_SALT`**: Salt for anonymous ID generation (keep secret)
- **`ENVIRONMENT`**: Environment name for ID isolation
- **`INTER_RATER_ENABLED`**: Enable inter-rater functionality (requires auth)

For detailed environment file setup, refer to the [Configuration Guide](configuration.md).

## Authentication Flow

### Cognito Mode (AUTH_METHOD=cognito)

**Frontend (Vue 3 + Amplify):**
1. **Login**: User authenticates via Cognito hosted UI
2. **Token Storage**: JWT ID token stored securely by Amplify
3. **API Requests**: All API calls automatically include `Authorization: Bearer <token>` header
4. **Token Refresh**: Amplify handles automatic token refresh

**Backend (FastAPI):**
1. **Token Extraction**: Extract JWT token from `Authorization` header
2. **Token Validation**: Verify token signature and expiration with Cognito
3. **User Identification**: Extract `sub` claim from validated token
4. **Anonymous ID**: Generate privacy-preserving anonymous ID from Cognito `sub`

### Cloudflare Mode (AUTH_METHOD=cloudflare)

**Frontend:** No special handling. Cloudflare Access authenticates users at the edge transparently (SSO, MFA, email OTP). No Bearer tokens are injected.

**Backend (FastAPI):**
1. **Header Extraction**: Read `Cf-Access-Authenticated-User-Email` header
2. **Trust Model**: Header is trusted because origin is unreachable outside the tunnel (no public ports, UFW deny-all-incoming)
3. **User Identification**: Email address used as identity string
4. **Anonymous ID**: Generate privacy-preserving anonymous ID from email

### None Mode (AUTH_METHOD=none)

All users are anonymous. No authentication headers are sent or expected. Used for development and testing.

## Anonymous User IDs

For privacy and analytics, authenticated users are mapped to anonymous IDs:

```python
# Generation process (accepts any identity string: Cognito sub, email, etc.)
raw_input = f"{environment_salt}_{identity_string}"
anonymous_hash = hashlib.sha256(raw_input.encode()).hexdigest()[:16]
anonymous_id = f"anon_{anonymous_hash}"
```

**Properties:**
- **Auth-mode agnostic**: Works with Cognito sub (UUID) or Cloudflare email
- **Consistent**: Same identity string always gets same anonymous ID
- **Irreversible**: Cannot trace back to original identity
- **Environment-isolated**: Different environments produce different IDs
- **Mode-isolated**: Different auth modes produce different IDs for the same physical user (by design)
- **Privacy-preserving**: Safe for logging and telemetry

## API Authentication

### Protected Endpoints
The following endpoints require authentication when `AUTH_METHOD=cognito` or `AUTH_METHOD=cloudflare`:

- **`POST /api/feedback`**: Submit user feedback (requires user_id for inter-rater)
- **`GET /api/inter-rater/stats`**: Get inter-rater session availability
- **`GET /api/inter-rater/sessions`**: Get sessions for inter-rating
- **`GET /api/debug/user-id`**: Debug user ID extraction (development only)

### Authentication Headers
All authenticated requests must include:
```
Authorization: Bearer <cognito_jwt_token>
```

**Recent Fix**: Frontend components now properly send Authorization headers with all feedback submissions.

## Inter-rater Requirements

Inter-rater functionality **requires authentication** because:
- Users must be excluded from rating their own sessions
- Anonymous user IDs needed for rating attribution
- Prevents duplicate ratings by same user
- Enables user-specific session allocation

## Token Validation

The backend validates JWT tokens by:
1. **Signature verification**: Using Cognito public keys
2. **Expiration check**: Ensuring token is not expired
3. **Issuer validation**: Confirming token from correct Cognito User Pool
4. **Audience validation**: Verifying token for correct client

## Debugging Authentication

### Development Endpoint
**`GET /api/debug/user-id`** (development only):
- Shows authentication extraction details
- Returns sanitized debugging information
- Helps troubleshoot JWT token issues

### Common Issues
1. **Missing Authorization header**: Frontend not sending tokens
   - **Fix**: Ensure all API calls use the authenticated `apiRequest()` utility
2. **Token expired**: JWT token has expired
   - **Fix**: Amplify should auto-refresh; check refresh token validity
3. **Invalid signature**: Token corrupted or from wrong User Pool
   - **Fix**: Verify Cognito configuration matches

## Logging and Privacy

Authentication logging is privacy-safe:
- **Cognito subs**: Truncated to first 8 characters (`f93ef458...`)
- **Anonymous IDs**: Truncated to first 12 characters (`anon_ce74b9a...`)
- **JWT tokens**: Never logged in full
- **Headers**: Authorization headers redacted in error logs

## Recent Authentication Fixes (2025-08)

- ✅ **Frontend Authorization Headers**: Fixed all feedback components to send JWT tokens
- ✅ **User ID Extraction**: Enhanced backend token processing with comprehensive logging
- ✅ **Inter-rater Authentication**: Properly captures user IDs for session exclusion
- ✅ **Debug Endpoint**: Added development-only endpoint for troubleshooting
- ✅ **Anonymous ID Service**: Enhanced error handling and validation