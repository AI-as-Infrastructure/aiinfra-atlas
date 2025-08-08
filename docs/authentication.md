# Authentication

This application implements AWS Cognito for user authentication with JWT token-based authorization. The authentication system is designed to be flexible and can be easily toggled on or off based on deployment requirements.

**Key Features:**
- JWT token validation on backend
- Anonymous user ID generation for privacy
- Required for inter-rater functionality
- Automatic Authorization header handling
- Session-agnostic user identification

## Configuration

Authentication is controlled via environment variables in your `.env` file:

### Basic Toggle
- **`VITE_USE_COGNITO_AUTH=false`**: Disable authentication (open access)
- **`VITE_USE_COGNITO_AUTH=true`**: Enable AWS Cognito authentication (required for inter-rater)

### Anonymous ID Configuration
- **`ANONYMOUS_ID_SALT`**: Environment-specific salt for generating anonymous user IDs
- **`ENVIRONMENT`**: Environment name (development/staging/production) for ID isolation

## AWS Cognito Setup

To enable authentication, you need to:

1. **Create a Cognito User Pool** in the AWS Cognito console
2. **Configure the Cognito environment variables** using the template provided in `config/.env.template`

### Required Cognito Variables

**Frontend Configuration:**
- **`VITE_USE_COGNITO_AUTH`**: Toggle authentication on/off
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

### Frontend (Vue 3 + Amplify)
1. **Login**: User authenticates via Cognito hosted UI
2. **Token Storage**: JWT ID token stored securely by Amplify
3. **API Requests**: All API calls automatically include `Authorization: Bearer <token>` header
4. **Token Refresh**: Amplify handles automatic token refresh

### Backend (FastAPI)
1. **Token Extraction**: Extract JWT token from `Authorization` header
2. **Token Validation**: Verify token signature and expiration with Cognito
3. **User Identification**: Extract `sub` claim from validated token
4. **Anonymous ID**: Generate privacy-preserving anonymous ID from Cognito `sub`

## Anonymous User IDs

For privacy and analytics, authenticated users are mapped to anonymous IDs:

```python
# Generation process
raw_input = f"{environment_salt}_{cognito_sub}"
anonymous_hash = hashlib.sha256(raw_input.encode()).hexdigest()[:16]
anonymous_id = f"anon_{anonymous_hash}"
```

**Properties:**
- **Consistent**: Same user always gets same anonymous ID
- **Irreversible**: Cannot trace back to original Cognito sub  
- **Environment-isolated**: Different environments produce different IDs
- **Privacy-preserving**: Safe for logging and telemetry

## API Authentication

### Protected Endpoints
The following endpoints require authentication when `VITE_USE_COGNITO_AUTH=true`:

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