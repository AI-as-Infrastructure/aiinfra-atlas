# Proposal: Harden Cloudflare Deployment Security

## Change ID
`harden-cloudflare-deployment`

## Summary
Add defence-in-depth security controls for Cloudflare Zero Trust deployments: JWT validation of Cloudflare Access tokens, API rate limiting, restricted CORS, nginx origin verification, and sanitised error responses. These changes address gaps identified during pre-production security review of the `refactor-auth-mode` and `add-cloudflare-tunnel-deployment` work.

## Motivation
The `refactor-auth-mode` change introduced `AUTH_METHOD=cloudflare` which extracts user identity from the `Cf-Access-Authenticated-User-Email` header. The current implementation trusts this header without cryptographic verification, relying solely on the assumption that traffic only reaches the origin through the tunnel. This is insufficient for production:

1. **No JWT validation**: `extract_cloudflare_user()` reads an email header without verifying the `Cf-Access-Jwt-Assertion` JWT. If any path exists to reach the backend directly (misconfigured firewall, localhost access, cloudflared crash), the email header can be trivially spoofed.
2. **No rate limiting**: `slowapi` is a dependency and `RATE_LIMIT_PER_MINUTE` is configured, but no rate limiting code exists. LLM API costs and availability are unprotected.
3. **CORS too permissive**: `allow_methods=["*"]` and `allow_headers=["*"]` expose unnecessary attack surface.
4. **No nginx origin verification**: If cloudflared stops but nginx continues running, requests to localhost bypass authentication entirely.
5. **Error messages leak implementation details**: Exception messages expose provider names, environment variable names, and backend architecture.

## Scope

### In Scope
- Cloudflare Access JWT validation using Cloudflare's public key endpoint
- New env vars: `CLOUDFLARE_TEAM_DOMAIN`, `CLOUDFLARE_ACCESS_AUD`
- SlowAPI rate limiting on query endpoints
- Restricted CORS methods and headers
- Nginx header validation for Cloudflare origin verification
- Sanitised error messages for unauthenticated endpoints
- Firewall verification step in Cloudflare deploy script
- Deploy script dependency on cloudflared service

### Out of Scope
- Changes to Cognito auth flow (unaffected)
- Cloudflare dashboard or Access policy configuration
- WAF rules at the Cloudflare edge (operator responsibility)
- Prompt injection hardening (separate concern, lower priority for authenticated users)
- Dependency CVE patching (covered by `update-security-dependencies`)

## Impact
- Affected specs: `cloudflare-security` (new capability)
- Affected code:
  - `backend/modules/auth.py` -- JWT validation for Cloudflare mode
  - `backend/app.py` -- CORS restriction, rate limiting middleware
  - `backend/routers/query.py` -- rate limiting decorator
  - `backend/modules/llm.py` -- error message sanitisation
  - `backend/routers/core.py` -- diagnostics endpoint access control
  - `deploy/cloudflare/cloudflare.sh` -- firewall check, service dependency
  - `deploy/cloudflare/nginx-cloudflare.conf.template` -- origin verification
  - `config/.env.template` -- new Cloudflare env vars
  - `config/.env.production` -- new Cloudflare env vars

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cloudflare public key rotation breaks JWT validation | Low | High | Cache keys with TTL, fetch fresh on validation failure |
| Rate limiting blocks legitimate burst usage | Low | Medium | Configure per-user limits, generous defaults (60/min) |
| CORS restriction breaks existing frontends | Low | Low | Only restrict to methods/headers actually used |
| JWT validation adds latency | Low | Low | Key caching, validation only on authenticated endpoints |
| Nginx header check false-positive blocks | Very Low | Medium | Use Cf-Ray header (always present on Cloudflare requests) |

## Related
- `refactor-auth-mode` -- Introduced `AUTH_METHOD=cloudflare` (completed)
- `add-cloudflare-tunnel-deployment` -- Cloudflare tunnel infrastructure (completed)
- `add-reverse-proxy-to-cloudflare` -- Nginx reverse proxy (completed)
- `update-security-dependencies` -- Dependency CVE patching (in progress)
