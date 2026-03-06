# Data Privacy

This document describes ATLAS's approach to data privacy: how identities are protected, what data is collected, and what is explicitly not collected.

## Principles

- **Minimal data collection**: only what is required to operate the app
- **No PII persisted**: no IP addresses, emails, or user names are stored in logs or telemetry
- **Anonymous by design**: authenticated users are mapped to irreversible anonymous IDs for all analytics/telemetry
- **Explicit configuration**: sensitive behavior requires explicit enablement in environment files
- **Privacy-safe logging**: debug information is truncated and sanitized to prevent identity exposure
- **Secure by default**: sensitive endpoints require authentication and are disabled in production

## Authentication and Anonymity

- Authentication is handled by `AUTH_METHOD`: `cognito` (AWS Cognito JWT), `cloudflare` (Cloudflare Access header), or `none` (anonymous).
- For Cognito, the JWT is validated server-side; claims are not logged. For Cloudflare, the `Cf-Access-Authenticated-User-Email` header is trusted because traffic only reaches the origin through the tunnel.
- A centralized service (`backend/services/anonymous_id_service.py`) derives a consistent, irreversible anonymous ID from the user's stable identity (Cognito UUID or Cloudflare email) using an environment-specific salt.
  - **Format**: `anon_<16-hex>` (SHA-256 hash truncated to 16 characters)
  - **Salt**: Controlled via `ANONYMOUS_ID_SALT`; different salts per environment prevent cross-environment correlation
  - **Irreversible**: Cannot trace back to original Cognito sub
  - **Session-agnostic**: Same user gets same anonymous ID across logout/login cycles
  - **Original identifiers**: Never stored or exported beyond the hashing process

## Telemetry and Phoenix

- Feedback and annotations sent to Phoenix include only anonymized identifiers and rating metadata necessary for evaluation.
- Inter-rater feedback is clearly marked with `[Inter-rater]` prefixes and metadata flags (`is_inter_rater`, `rater_id` as anonymous ID, `original_span_id`).
- Secrets (e.g., `PHOENIX_API_KEY`) are never logged; headers are redacted in error logs.
- No client IP addresses are included in Phoenix payloads.

## Client IPs

- Client IPs are not collected, logged, or exported anywhere in the application.
- Historical per-IP rate limiting has been removed; only a simple request size limit remains.

## Logging

- **Backend logs** avoid raw payloads and sensitive fields. Only high-level statuses and anonymized IDs are logged
- **Authorization headers, tokens, and emails** are never logged in full
- **Raw identity strings** (Cognito subs, emails) are never logged; only their anonymous hashes are used
- **Anonymous IDs** are truncated to first 12 characters for debugging (e.g., `anon_ce74b9a...`)
- **Span IDs** are truncated to first 8 characters for debugging (e.g., `0acc527d...`)
- **Frontend** suppresses verbose logs in production; no auth tokens or emails printed to console
- **Error logging** includes sanitized details for troubleshooting while preserving anonymity

## Data Stored

- Anonymous ratings/annotations and operational telemetry (non-PII) in Phoenix.
- Optional local backups of Phoenix exports (Parquet/CSV) for analytics, containing only anonymized fields.
- Environment configuration files (`config/.env.*`) stored locally by operators, never checked into version control with real secrets.

## Data Not Stored

- No IP addresses, emails, names, or raw authentication tokens.
- No raw chat payloads beyond what is required for model operation and user-visible history.

## Configuration Summary

- **`AUTH_METHOD`**: Authentication mode -- `cognito`, `cloudflare`, or `none`. Set once; `VITE_AUTH_METHOD` is derived automatically at build time for the frontend.
- **`ANONYMOUS_ID_SALT`**: Environment-specific salt for anonymous ID generation
- **`PHOENIX_API_KEY` / `PHOENIX_CLIENT_HEADERS`**: Phoenix credentials (used only in headers; never logged)
- **`TELEMETRY_ENABLED`**: Telemetry pipeline control; if disabled, feedback accepted but not exported
- **`INTER_RATER_ENABLED`**: Enable inter-rater functionality (requires `AUTH_METHOD=cognito` or `AUTH_METHOD=cloudflare`)
- **`ENVIRONMENT`**: Determines which .env file to load and isolates anonymous IDs

## Debug Endpoints (Development Only)

- **`GET /api/debug/user-id`**: Verifies user ID extraction from JWT tokens
  - **Development only**: Should be disabled or access-controlled in production
  - **Returns**: Sanitized debugging information without exposing full tokens
  - **Privacy-safe**: Shows only extraction success/failure and truncated IDs

## Inter-rater Anonymity

- **Session allocation**: Users cannot predict which sessions they'll be assigned
- **Rating blindness**: Inter-raters see questions/answers but not original rater identity
- **Temporal separation**: Sessions may have time delays between original rating and inter-rating
- **Pattern obfuscation**: Deterministic but unpredictable allocation prevents gaming
- **Cross-correlation prevention**: Environment-specific salts prevent linking users across environments

## Contact

For privacy questions or issues, review this document and the relevant modules:
- `backend/services/anonymous_id_service.py` - Anonymous ID generation
- `backend/telemetry/api.py` - Authentication and user ID extraction
- `backend/telemetry/feedback.py` - Phoenix annotation storage
- `backend/services/inter_rater_service.py` - Inter-rater allocation
- `backend/app.py` - Main application and environment loading

If you find any logging or code that could expose PII, please open an issue and reference this document.

## Recent Privacy Enhancements (2025-08)

- ✅ **Enhanced authentication logging**: Added detailed but privacy-safe debugging for JWT token processing
- ✅ **Consistent ID truncation**: Standardized truncation patterns across all logging (8 chars for Cognito, 12 for anonymous IDs)
- ✅ **Debug endpoint**: Added development-only endpoint for authentication troubleshooting
- ✅ **Inter-rater anonymity**: Strengthened session allocation to prevent identity correlation
- ✅ **Authorization header security**: Fixed frontend to properly send auth tokens while preventing logging
