# Proposal: Refactor Auth Mode from Boolean to Tri-Modal

## Change ID
`refactor-auth-mode`

## Summary
Replace the boolean `VITE_USE_COGNITO_AUTH=true|false` toggle with a tri-modal `AUTH_METHOD=cognito|cloudflare|none` variable, enabling Cloudflare Access header-based identity for Cloudflare deployments while preserving Cognito JWT authentication for production and staging.

## Motivation
The Cloudflare Tunnel deployment (v0.2.4) added an Nginx reverse proxy but still has no user identity. The current auth model is a binary choice: Cognito JWT or nothing. This means:

1. **No telemetry identity behind Cloudflare Access**: Feedback, inter-rater sessions, and anonymous IDs all require `VITE_USE_COGNITO_AUTH=true`, which requires a full Cognito setup. Behind Cloudflare Access (which already authenticates users via SSO/MFA/email OTP), there is no way to extract identity for telemetry.
2. **Unnecessary Cognito dependency for tunneled deployments**: Cloudflare Access already provides authentication at the edge. Running Cognito in parallel is redundant and adds cost/complexity.
3. **Rigid boolean doesn't scale**: The `VITE_USE_COGNITO_AUTH` flag couples authentication provider choice to a single vendor. A mode selector is more extensible.

Cloudflare Access sets the `Cf-Access-Authenticated-User-Email` header on every request that passes through a tunnel with an Access policy. This header is trustworthy because traffic only reaches the origin through the tunnel -- there is no public port to forge headers against.

## Scope

### In Scope
- Add `AUTH_METHOD` environment variable with three modes: `cognito`, `cloudflare`, `none`
- Refactor `backend/modules/auth.py` to dispatch on `AUTH_METHOD` instead of `is_cognito_enabled()`
- Add Cloudflare Access header extraction (`Cf-Access-Authenticated-User-Email`)
- Feed Cloudflare identity into `anonymous_id_service` for telemetry/feedback/inter-rater
- Update `backend/telemetry/api.py` identity extraction to use the auth dispatcher
- Update `backend/routers/feedback.py` and `backend/routers/inter_rater.py` auth checks
- Update `frontend/src/utils/api.js` to skip Cognito token injection when `AUTH_METHOD != cognito`
- Update `config/generate_vue_files.sh` to handle `AUTH_METHOD`
- Update all 5 env files: `.env.template`, `.env.development`, `.env.development.feature`, `.env.staging`, `.env.production`
- Deprecate `VITE_USE_COGNITO_AUTH` (keep for backward compatibility in this phase, log warning if set)
- Update documentation

### Out of Scope
- Removing Cognito support (it remains fully functional)
- Changing Cloudflare dashboard or Access policy configuration
- Adding new auth providers beyond Cognito and Cloudflare Access
- Frontend login/logout UI changes (Cognito flow unchanged; Cloudflare Access is transparent)
- Modifying the anonymous ID hashing algorithm
- Changes to deploy scripts (auth mode is env config, not infrastructure)

## Architecture

```
AUTH_METHOD=cognito          AUTH_METHOD=cloudflare         AUTH_METHOD=none
     |                            |                             |
  JWT in                   Cf-Access-*                     No identity
  Authorization            headers from                    Anonymous user
  header                   Cloudflare edge                 (dev/testing)
     |                            |                             |
     v                            v                             v
  verify_cognito_token()   extract_cloudflare_user()       return anonymous
     |                            |                             |
     v                            v                             |
  Cognito sub (UUID)       email address                        |
     |                            |                             |
     +------------+---------------+-----------------------------+
                  |
                  v
        anonymous_id_service.generate_anonymous_id(identity_string)
                  |
                  v
           anon_<16-char-hash>
```

Key design points:
- The auth module becomes a dispatcher: one public interface, three backends
- `anonymous_id_service.generate_anonymous_id()` already accepts any string -- Cognito sub or email both work
- Cloudflare Access headers are trusted because the origin is unreachable outside the tunnel
- `AUTH_METHOD=none` replaces the current `VITE_USE_COGNITO_AUTH=false` behaviour (anonymous sub)
- Frontend only needs to know whether to inject Cognito JWT -- `VITE_AUTH_METHOD=cognito` triggers token injection, all other modes skip it

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Anonymous ID consistency breaks between modes | Low | Medium | Same hashing algorithm, different input strings; documented that IDs are mode-specific |
| Cloudflare header spoofing | Very Low | Low | Origin only reachable via tunnel; UFW denies all incoming |
| Backward compatibility with existing `VITE_USE_COGNITO_AUTH` | Low | Low | Deprecated with warning; if set and `AUTH_METHOD` absent, map `true`->`cognito`, `false`->`none` |
| Inter-rater data isolation across auth modes | Low | Medium | `ANONYMOUS_ID_SALT` is environment-specific; different salts produce different IDs |

## Related
- `add-cloudflare-tunnel-deployment` -- Cloudflare deployment (archived)
- `add-reverse-proxy-to-cloudflare` -- Nginx reverse proxy (archived)
- `backend/modules/auth.py` -- Current Cognito-only auth module
- `backend/services/anonymous_id_service.py` -- Anonymous ID generation service

## Acceptance Criteria
- [ ] `AUTH_METHOD=cognito` works identically to current `VITE_USE_COGNITO_AUTH=true`
- [ ] `AUTH_METHOD=cloudflare` extracts identity from `Cf-Access-Authenticated-User-Email` header
- [ ] `AUTH_METHOD=none` works identically to current `VITE_USE_COGNITO_AUTH=false`
- [ ] Feedback submissions include `user_id` when `AUTH_METHOD=cloudflare`
- [ ] Inter-rater sessions work with `AUTH_METHOD=cloudflare`
- [ ] Telemetry spans include anonymous user ID when `AUTH_METHOD=cloudflare`
- [ ] Frontend skips Cognito token injection when `AUTH_METHOD != cognito`
- [ ] All 6 env files updated with `AUTH_METHOD` and deprecation comment on `VITE_USE_COGNITO_AUTH`
- [ ] Setting `VITE_USE_COGNITO_AUTH` without `AUTH_METHOD` logs a deprecation warning and maps correctly
- [ ] Existing Cognito deployments (production, staging) are unaffected
