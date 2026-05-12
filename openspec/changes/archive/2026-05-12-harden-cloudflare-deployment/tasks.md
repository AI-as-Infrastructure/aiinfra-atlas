# Tasks: Harden Cloudflare Deployment Security

## 1. Cloudflare JWT Validation
- [x] 1.1 Add `CLOUDFLARE_TEAM_DOMAIN` and `CLOUDFLARE_ACCESS_AUD` env vars to `config/.env.template`
- [x] 1.2 Implement JWT public key fetching and caching in `backend/modules/auth.py` (fetch from `https://<team-domain>/cdn-cgi/access/certs`, cache with 1h TTL)
- [x] 1.3 Implement `verify_cloudflare_jwt()` function: validate signature (RS256), audience, issuer, expiry
- [x] 1.4 Update `extract_cloudflare_user()` to require valid JWT before trusting email header
- [x] 1.5 Add graceful fallback: re-fetch keys once on validation failure (handles key rotation)
- [x] 1.6 Add unit tests for JWT validation (valid token, expired token, wrong audience, missing header)

## 2. Rate Limiting
- [x] 2.1 Initialise SlowAPI limiter in `backend/rate_limit.py` (shared module) with `RATE_LIMIT_PER_MINUTE` config
- [x] 2.2 Configure key function to use `Cf-Connecting-IP` header when behind Cloudflare, fallback to remote address
- [x] 2.3 Apply rate limit decorator to `/api/ask/stream` in `backend/routers/query.py`
- [x] 2.4 Apply rate limit decorator to `/api/ask/async` in `backend/routers/query.py`
- [x] 2.5 Add 429 error handler with `Retry-After` header (via SlowAPI default handler)
- [x] 2.6 Add unit tests for rate limiting (under limit, at limit, over limit)

## 3. CORS Restriction
- [x] 3.1 Replace `allow_methods=["*"]` with `["GET", "POST", "OPTIONS"]` in `backend/app.py`
- [x] 3.2 Replace `allow_headers=["*"]` with explicit list: `Content-Type`, `Authorization`, `X-Telemetry-Opt-In`, `X-Trace-Id`, `X-Request-Id`
- [x] 3.3 Verify frontend requests still work with restricted CORS (dev and staging)

## 4. Nginx Origin Verification
- [x] 4.1 Add `Cf-Ray` header check to `deploy/cloudflare/nginx-cloudflare.conf.template` (return 403 if missing)
- [x] 4.2 Add `Requires=cloudflared.service` to gunicorn systemd unit in `deploy/cloudflare/cloudflare.sh`

## 5. Error Message Sanitisation
- [x] 5.1 Sanitise LLM provider error messages in `backend/modules/llm.py` (keep detail in logs, generic message to client)
- [x] 5.2 Sanitise queue/Redis error messages in `backend/routers/query.py`
- [x] 5.3 Review `/api/diagnostics` endpoint in `backend/routers/core.py` for information leakage (already gated behind auth, returns bool presence only - acceptable)

## 6. Deploy Script Hardening
- [x] 6.1 Add UFW port 8000 verification step to `deploy/cloudflare/cloudflare.sh`
- [x] 6.2 Add pre-flight check that cloudflared service is active before starting gunicorn

## 7. Integration Testing
- [x] 7.1 Test `AUTH_METHOD=cloudflare` with JWT validation enabled (valid and invalid tokens)
- [x] 7.2 Test `AUTH_METHOD=cognito` is unaffected by changes
- [x] 7.3 Test `AUTH_METHOD=none` is unaffected by changes
- [x] 7.4 Test rate limiting with concurrent requests
- [x] 7.5 Test CORS with frontend in dev and staging
