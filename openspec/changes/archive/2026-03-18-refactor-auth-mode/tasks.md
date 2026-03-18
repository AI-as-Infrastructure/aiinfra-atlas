# Tasks: Refactor Auth Mode from Boolean to Tri-Modal

## Prerequisites
- [x] Review `backend/modules/auth.py` for current Cognito auth flow
- [x] Review `backend/services/anonymous_id_service.py` for identity hashing interface
- [x] Review `backend/telemetry/api.py:84-134` for identity extraction in feedback
- [x] Review `backend/routers/inter_rater.py` and `backend/routers/feedback.py` for auth checks
- [x] Confirm no other active changes conflict with auth module files

## Implementation Tasks

### Phase 1: Environment Configuration
- [x] **Task 1.1**: Update `config/.env.template` -- add `AUTH_METHOD=none` below `VITE_USE_COGNITO_AUTH`, add `VITE_AUTH_METHOD=none`, add deprecation comment on `VITE_USE_COGNITO_AUTH`
- [x] **Task 1.2**: Update `config/.env.development` -- add `AUTH_METHOD=none`, add `VITE_AUTH_METHOD=none`
- [x] **Task 1.3**: Update `config/.env.development.feature` -- add `AUTH_METHOD=none`, add `VITE_AUTH_METHOD=none`
- [x] **Task 1.4**: Update `config/.env.staging` -- add `AUTH_METHOD=cognito`, add `VITE_AUTH_METHOD=cognito` (preserves current Cognito behaviour)
- [x] **Task 1.5**: Update `config/.env.production` -- add `AUTH_METHOD=cognito`, add `VITE_AUTH_METHOD=cognito` (preserves current Cognito behaviour)
- [x] **Task 1.6**: Set `AUTH_METHOD=cloudflare` in core env file for Cloudflare Tunnel deployments (no separate .env.cloudflare file)

### Phase 2: Backend Auth Module Refactor
- [x] **Task 2.1**: Add `get_auth_method()` function to `backend/modules/auth.py` -- reads `AUTH_METHOD`, falls back to `VITE_USE_COGNITO_AUTH` mapping with deprecation warning, defaults to `none`
- [x] **Task 2.2**: Add `extract_cloudflare_user(request)` function to `backend/modules/auth.py` -- extracts `Cf-Access-Authenticated-User-Email` header, returns user dict with `authenticated=True` or raises HTTPException
- [x] **Task 2.3**: Add `get_authenticated_user(request)` dispatcher function to `backend/modules/auth.py` -- dispatches to Cognito JWT, Cloudflare header, or anonymous based on `get_auth_method()`
- [x] **Task 2.4**: Add `optional_authenticated_user(request)` dispatcher function -- non-throwing variant that returns anonymous user on failure
- [x] **Task 2.5**: Update `is_cognito_enabled()` to delegate to `get_auth_method() == "cognito"` for backward compatibility

### Phase 3: Anonymous ID Service Update
- [x] **Task 3.1**: Rename `generate_anonymous_id()` parameter from `cognito_sub` to `identity_string` in `backend/services/anonymous_id_service.py`
- [x] **Task 3.2**: Update docstrings and error messages to reflect generic identity input (not Cognito-specific)
- [x] **Task 3.3**: Update `get_anonymous_id_from_user_data()` to extract `sub` generically (works for both Cognito sub and Cloudflare email)

### Phase 4: Telemetry and Router Updates
- [x] **Task 4.1**: Refactor `backend/telemetry/api.py:84-134` -- replace inline Cognito auth logic with call to `get_authenticated_user(request)` or `optional_authenticated_user(request)`
- [x] **Task 4.2**: Refactor `backend/routers/feedback.py:28-46` -- replace `VITE_USE_COGNITO_AUTH` check and inline token extraction with auth dispatcher
- [x] **Task 4.3**: Refactor `backend/routers/inter_rater.py:18-50` -- replace `_get_user_id_from_request()` and `VITE_USE_COGNITO_AUTH` checks with auth dispatcher
- [x] **Task 4.4**: Ensure all three routers use the unified user dict format `{"sub": str, "username": str, "authenticated": bool, "auth_method": str}`

### Phase 5: Frontend Updates
- [x] **Task 5.1**: Update `frontend/src/utils/api.js:28-38` -- `isCognitoEnabled()` now checks `VITE_AUTH_METHOD` via updated `amplify-auth.js`
- [x] **Task 5.2**: Update any frontend auth utility that reads `VITE_USE_COGNITO_AUTH` to read `VITE_AUTH_METHOD` instead (with fallback) -- updated `amplify-auth.js` and `useAuth.js`
- [x] **Task 5.3**: Update `config/generate_vue_files.sh` -- extract `AUTH_METHOD` and `VITE_AUTH_METHOD` variables for frontend build

### Phase 6: Documentation
- [x] **Task 6.1**: Update `docs/configuration.md` -- document `AUTH_METHOD` variable, three modes, and deprecation of `VITE_USE_COGNITO_AUTH`
- [x] **Task 6.2**: Update `docs/authentication.md` -- comprehensive rewrite of auth modes, flows, and anonymous ID generation
- [x] **Task 6.3**: Update `docs/inter_rater.md` -- note that inter-rater works with all auth modes that provide identity
- [x] **Task 6.4**: Add deprecation note to `.env.template` comments for `VITE_USE_COGNITO_AUTH`

### Phase 7: Validation
- [x] **Task 7.1**: Run `openspec validate refactor-auth-mode --strict`
- [x] **Task 7.2**: Verify existing Cognito auth flow is unchanged when `AUTH_METHOD=cognito` (code review: same JWT verification path)
- [x] **Task 7.3**: Verify `AUTH_METHOD=none` produces same behaviour as current `VITE_USE_COGNITO_AUTH=false` (returns anonymous user dict)
- [x] **Task 7.4**: Verify `AUTH_METHOD=cloudflare` extracts email from `Cf-Access-Authenticated-User-Email` header (code review: `extract_cloudflare_user()`)
- [x] **Task 7.5**: Verify backward compatibility: `VITE_USE_COGNITO_AUTH=true` without `AUTH_METHOD` maps to `cognito` with deprecation warning (code review: `get_auth_method()`)
- [x] **Task 7.6**: Verify no changes to deploy scripts (`deploy/production/`, `deploy/staging/`, `deploy/cloudflare/`)

## Verification Commands
```bash
# Validate OpenSpec
openspec validate refactor-auth-mode --strict

# Check AUTH_METHOD is in all env files
grep -l "AUTH_METHOD" config/.env.*

# Check VITE_AUTH_METHOD is in all env files
grep -l "VITE_AUTH_METHOD" config/.env.*

# Check no remaining hard-coded VITE_USE_COGNITO_AUTH checks in backend (should only be in deprecation fallback)
grep -rn "VITE_USE_COGNITO_AUTH" backend/ --include="*.py"

# Check frontend uses VITE_AUTH_METHOD
grep -rn "VITE_AUTH_METHOD" frontend/src/

# Confirm deploy scripts unchanged
git diff --name-only deploy/production/ deploy/staging/ deploy/cloudflare/
```

## Rollback Plan
All changes are reversible:
1. Remove `AUTH_METHOD` and `VITE_AUTH_METHOD` from env files
2. Revert `backend/modules/auth.py` to Cognito-only version from git
3. Revert `anonymous_id_service.py` parameter rename from git
4. Revert telemetry/feedback/inter-rater routers from git
5. Revert frontend `api.js` from git
6. The `VITE_USE_COGNITO_AUTH` variable remains functional throughout
