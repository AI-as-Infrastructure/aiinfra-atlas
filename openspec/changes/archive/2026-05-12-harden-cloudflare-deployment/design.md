# Design: Harden Cloudflare Deployment Security

## Context
ATLAS is a research prototype deploying behind Cloudflare Zero Trust tunnels. The current `AUTH_METHOD=cloudflare` implementation trusts the `Cf-Access-Authenticated-User-Email` header without cryptographic verification. A pre-production security review identified this and several other gaps that need defence-in-depth controls before production deployment.

The user base is small (authenticated researchers), but the system handles LLM API keys and incurs per-query costs, making abuse prevention important.

## Goals / Non-Goals

**Goals:**
- Validate Cloudflare Access identity cryptographically (JWT)
- Prevent abuse of LLM query endpoints (rate limiting)
- Reduce attack surface (CORS, error messages, nginx validation)
- Maintain fail-fast philosophy -- security failures should be loud, not silent

**Non-Goals:**
- Enterprise-grade WAF or IDS (Cloudflare edge handles this)
- Prompt injection hardening (separate concern)
- Multi-tenant isolation (single-team deployment)
- Automated penetration testing framework

## Decisions

### 1. Cloudflare JWT Validation

**Decision**: Validate `Cf-Access-Jwt-Assertion` header using Cloudflare's public key endpoint (`https://<team-domain>/cdn-cgi/access/certs`).

**Implementation**:
- Fetch and cache Cloudflare's public keys (RSA) with 1-hour TTL
- Validate JWT signature, audience (`CLOUDFLARE_ACCESS_AUD`), issuer, and expiry
- On validation failure, fall back to re-fetching keys once (handles key rotation)
- Use `PyJWT` (already available via `python-jose[cryptography]` dependency) for JWT decode
- Only active when `AUTH_METHOD=cloudflare`

**Alternatives considered**:
- Trust headers without validation (current state) -- rejected, insufficient for production
- Validate at nginx level with Cloudflare's `cf-connecting-ip` -- doesn't verify identity, only origin
- Use a Cloudflare Worker for validation -- adds external dependency and complexity

### 2. Rate Limiting

**Decision**: Use SlowAPI (already in `requirements.txt`) with per-IP rate limiting on `/api/ask/stream` and `/api/ask/async`.

**Implementation**:
- Default: 60 requests/minute per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- Behind Cloudflare, use `Cf-Connecting-IP` header for real client IP
- Return 429 with `Retry-After` header on limit exceeded
- No rate limiting on static assets or health checks

**Alternatives considered**:
- Cloudflare rate limiting rules -- good complement but doesn't protect against localhost abuse
- Redis-backed rate limiting -- overkill for single-server deployment
- Per-user (authenticated) rate limiting -- good future enhancement, per-IP sufficient for now

### 3. CORS Restriction

**Decision**: Restrict to `GET, POST, OPTIONS` methods and explicit header list.

**Allowed headers**: `Content-Type`, `Authorization`, `X-Telemetry-Opt-In`, `X-Trace-Id`, `X-Request-Id`

### 4. Nginx Origin Verification

**Decision**: Check for `Cf-Ray` header in nginx (present on all Cloudflare-proxied requests). Return 403 if missing.

**Implementation**: Single `if` block in nginx config. Only applies to `nginx-cloudflare.conf.template` (staging/production nginx configs unaffected).

### 5. Error Message Sanitisation

**Decision**: Replace implementation-detail error messages with generic messages for client-facing responses. Keep detailed messages in server logs only.

**Pattern**:
```python
# Internal log (detailed)
logger.error(f"ANTHROPIC_API_KEY not found in environment")
# Client response (generic)
raise ValueError("LLM provider configuration error. Contact administrator.")
```

## Risks / Trade-offs

| Trade-off | Decision | Rationale |
|-----------|----------|-----------|
| JWT validation adds ~5ms latency | Accept | Only on authenticated endpoints, negligible vs LLM response time |
| Rate limiting may affect load testing | Accept | Configurable limit, can increase for testing |
| Stricter CORS may break future integrations | Accept | Easy to extend allowed headers later |
| Key caching could serve stale keys | Accept | Re-fetch on validation failure handles rotation |

## Migration Plan

1. Add new env vars with sensible defaults (no breaking changes)
2. JWT validation only activates when `CLOUDFLARE_TEAM_DOMAIN` and `CLOUDFLARE_ACCESS_AUD` are set
3. Rate limiting uses existing `RATE_LIMIT_PER_MINUTE` env var
4. CORS changes are backward-compatible (subset of previous `["*"]`)
5. No data migration required

**Rollback**: Set `CLOUDFLARE_TEAM_DOMAIN=""` to disable JWT validation and revert to header-trust mode.

## Open Questions

- Should rate limiting be per-user (authenticated identity) rather than per-IP in a future iteration?
- Should the diagnostics endpoint (`/api/diagnostics`) require an admin role, or is authentication sufficient?
