# Design: Refactor Auth Mode from Boolean to Tri-Modal

## Context
The ATLAS auth system is currently a binary toggle (`VITE_USE_COGNITO_AUTH=true|false`). The Cloudflare deployment authenticates users at the edge via Cloudflare Access, but the backend has no way to extract that identity because the only auth path is Cognito JWT verification.

The anonymous ID service (`backend/services/anonymous_id_service.py`) accepts any string input and produces `anon_<16-char-hash>`. It currently receives Cognito `sub` (UUID), but will work equally well with an email address or any other stable identifier.

## Goals / Non-Goals

**Goals:**
- Single `AUTH_METHOD` variable that selects authentication strategy
- Cloudflare Access identity extraction for telemetry, feedback, and inter-rater
- Backward compatibility with `VITE_USE_COGNITO_AUTH` during transition
- Minimal code change surface -- dispatcher pattern, not rewrite

**Non-Goals:**
- Supporting multiple auth methods simultaneously (one mode per deployment)
- Building an auth plugin system or registry
- Changing the Cognito OAuth flow or frontend login UI
- Modifying the anonymous ID hashing algorithm or format

## Decisions

### Decision: Dispatcher pattern in auth.py rather than separate modules
A single `backend/modules/auth.py` with a `get_auth_method()` dispatcher and mode-specific functions keeps the change contained. The module is 191 lines today; adding Cloudflare extraction and a dispatcher keeps it under 300 lines.

**Alternative considered:** Separate modules (`auth_cognito.py`, `auth_cloudflare.py`, `auth_none.py`) with a factory.
- Rejected: Over-engineered for three simple modes. The Cognito code is already in `auth.py` and moving it creates unnecessary churn.

### Decision: AUTH_METHOD as the canonical variable, VITE_USE_COGNITO_AUTH deprecated
The new canonical variable is `AUTH_METHOD` (backend) / `VITE_AUTH_METHOD` (frontend). The `VITE_` prefix is needed for Vite to expose it to the frontend build.

Backward compatibility logic:
1. If `AUTH_METHOD` is set, use it directly
2. If `AUTH_METHOD` is not set but `VITE_USE_COGNITO_AUTH` is set, map: `true` -> `cognito`, `false` -> `none`, log deprecation warning
3. If neither is set, default to `none`

### Decision: Trust Cf-Access-Authenticated-User-Email without verification
Cloudflare Access sets `Cf-Access-Authenticated-User-Email` after validating the user's identity at the edge. The header is trustworthy in the Cloudflare deployment because:
1. The origin server has no public ports (UFW deny-all-incoming)
2. All traffic arrives through the cloudflared tunnel
3. Cloudflare Access policies are enforced before traffic enters the tunnel
4. The header cannot be injected by external clients

**Alternative considered:** Validate `Cf-Access-JWT-Assertion` (the signed JWT from Cloudflare Access).
- Rejected for now: Adds complexity (JWKS fetch from Cloudflare, token verification) with minimal security benefit given the tunnel-only access model. Can be added later if the threat model changes.

### Decision: Email as identity input to anonymous_id_service
For `AUTH_METHOD=cloudflare`, the Cloudflare Access email is passed to `anonymous_id_service.generate_anonymous_id()` instead of a Cognito UUID. The hashing is one-way and the output format is identical (`anon_<16-char-hash>`).

This means:
- The same physical user will get different anonymous IDs in Cognito vs Cloudflare deployments (different input strings)
- Within a single Cloudflare deployment, the same email always produces the same anonymous ID (stable for inter-rater)
- The `ANONYMOUS_ID_SALT` provides environment isolation as before

### Decision: Rename generate_anonymous_id parameter from cognito_sub to identity_string
The `generate_anonymous_id()` method in `anonymous_id_service.py` currently names its parameter `cognito_sub`. This should be renamed to `identity_string` to reflect that it now accepts any stable user identifier (Cognito sub, email, etc.). The validation (minimum 10 characters) remains appropriate for both UUIDs and email addresses.

### Decision: Frontend uses VITE_AUTH_METHOD to decide token injection
The frontend `api.js` currently checks `isCognitoEnabled()` to decide whether to inject a Bearer token. This changes to checking `VITE_AUTH_METHOD === 'cognito'`. The `amplify-auth.js` module (Cognito OAuth flow) is only loaded when `VITE_AUTH_METHOD === 'cognito'`.

For `AUTH_METHOD=cloudflare`, the frontend does nothing special -- Cloudflare Access handles auth transparently via cookies/headers at the edge. No Bearer token is needed.

### Decision: Unified get_authenticated_user() replaces multiple auth checks
Currently, auth checks are scattered across `telemetry/api.py:84-129`, `routers/feedback.py:28-46`, and `routers/inter_rater.py:18-26`. These all independently check `VITE_USE_COGNITO_AUTH`, extract tokens, and generate anonymous IDs.

The refactored `auth.py` will export a single `get_authenticated_user(request)` function that:
1. Reads `AUTH_METHOD`
2. Dispatches to the correct extraction logic
3. Returns a consistent user dict: `{"sub": str, "username": str, "authenticated": bool, "auth_method": str}`

All callers switch from inline auth logic to this single dependency.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Anonymous IDs differ between Cognito and Cloudflare deployments | Documented; deployments are isolated environments with separate salts |
| Cloudflare header trust model weaker than JWT verification | Acceptable for tunnel-only deployment; JWT validation can be added later |
| Backward compatibility code adds complexity | Deprecation path is simple (3-line mapping); can be removed in next major version |
| `generate_vue_files.sh` must handle new variable | Minimal change -- extract `AUTH_METHOD` alongside existing variables |

## Open Questions
None -- all resolved.
