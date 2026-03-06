# Proposal: Add Reverse Proxy to Cloudflare Tunnel Deployment

## Change ID
`add-reverse-proxy-to-cloudflare`

## Summary
Replace the FastAPI `StaticFiles` static asset serving (Option 3) in the Cloudflare Tunnel deployment with Nginx reverse proxy serving (Option 2), aligning with the production deployment pattern and eliminating a security anti-pattern.

## Motivation
The current Cloudflare deployment uses Gunicorn/FastAPI to serve static frontend assets directly via a `SERVE_STATIC=true` flag and a `StaticFiles` mount in `backend/app.py`. This is a security anti-pattern because:

1. **Path traversal risk**: FastAPI/Starlette's static file handling is not a battle-tested web server. A path traversal vulnerability in the application layer has no mitigation between it and source code, environment secrets, and configuration files that share the same permission tree.
2. **No separation of concerns**: The API server and static file server run in the same process with the same filesystem permissions.
3. **Missing protections**: A dedicated reverse proxy like Nginx provides request buffering, header sanitisation, and request size limits that mitigate classes of attack Cloudflare's edge layer does not cover.

The production deployment (`deploy/production/`) already uses Nginx to serve static files and proxy API/WebSocket traffic. The Cloudflare deployment should adopt the same pattern, adapted for the tunnel context (localhost-only, no SSL).

## Scope

### In Scope
- Add Nginx to the Cloudflare deployment as a localhost-only reverse proxy
- Create `deploy/cloudflare/nginx-cloudflare.conf.template` derived from production template, stripped of SSL/certbot
- Nginx listens on `127.0.0.1:80` (not exposed publicly; cloudflared connects to it)
- Nginx serves Vue.js `dist/` static files with SPA fallback
- Nginx proxies `/api` and `/ws` to Gunicorn on `127.0.0.1:8000`
- Add `no-cache` header for `index.html` to prevent Cloudflare caching the HTML entry point (hashed asset filenames handle cache busting for all other static files)
- Update `cloudflare.sh` to install Nginx, deploy config, manage Nginx systemd service
- Update `stop_cloudflare.sh` and `clean_cloudflare.sh` for the Nginx service
- Remove `SERVE_STATIC=true` from Gunicorn systemd service
- Remove the `SERVE_STATIC` conditional code block from `backend/app.py`
- Update cloudflared ingress to route to Nginx (`http://localhost:80`) instead of Gunicorn
- Update Makefile help targets to reflect the architecture change

### Out of Scope
- Changes to existing `deploy/production/`, `deploy/staging/`, or `deploy/dev/` scripts
- Cloudflare dashboard configuration
- Changes to backend application code beyond removing the `SERVE_STATIC` block
- Frontend code changes
- Cloudflare cache configuration beyond the `index.html` no-cache header

## Architecture

```
                    Internet
                       |
              Cloudflare Edge
           (TLS, WAF, DDoS, CDN)
                       |
            Zero Trust Access
           (SSO, MFA, email OTP)
                       |
                       | (outbound-only QUIC/HTTP2)
                       |
              cloudflared tunnel
              (systemd service)
                       |
              127.0.0.1:80
                       |
                     Nginx
            (localhost-only reverse proxy)
            +----------+----------+
            |          |          |
         /api       /ws      /* (static)
      (proxy)   (proxy/ws)  Vue.js dist/
            |          |
       127.0.0.1:8000
            |
    Gunicorn + Uvicorn
       (API only)
            |
       Redis (127.0.0.1:6379)
```

Key changes from current Cloudflare deployment:
- Nginx added as localhost-only reverse proxy between cloudflared and Gunicorn
- Gunicorn no longer serves static files (API and WebSocket only)
- Static files served by Nginx from `/opt/atlas/frontend/dist` (same as production)
- `index.html` served with `Cache-Control: no-cache` to prevent Cloudflare caching the entry point
- Hashed asset filenames (JS, CSS) cached normally at the Cloudflare edge
- `SERVE_STATIC` code removed from `backend/app.py` entirely (no deployment path uses it)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Nginx adds a dependency | N/A | Low | Already present in production stack; well-understood by team |
| Configuration drift between production and Cloudflare Nginx configs | Low | Low | Cloudflare config derived from production template; minimal differences |
| Port conflict on localhost:80 | Low | Low | Script checks for existing Nginx; no public binding |
| Increased deployment complexity | Low | Low | One additional apt package and systemd service; script handles it |

## Related
- `add-cloudflare-tunnel-deployment` -- Original Cloudflare deployment (will be modified by this change)
- `deploy/production/nginx.conf.template` -- Production Nginx config (basis for Cloudflare variant)
- `deploy/production/production.sh` -- Production deploy script (pattern to follow)

## Acceptance Criteria
- [ ] `make cf` deploys ATLAS with Nginx as a localhost reverse proxy between cloudflared and Gunicorn
- [ ] Static files served by Nginx, not FastAPI/Gunicorn
- [ ] `index.html` served with `Cache-Control: no-cache` header
- [ ] Hashed assets (JS, CSS) served with long-lived cache headers
- [ ] `/api` and `/ws` traffic proxied to Gunicorn on `127.0.0.1:8000`
- [ ] No `SERVE_STATIC` code remains in `backend/app.py`
- [ ] `make scf` gracefully stops Nginx alongside other services
- [ ] `make dcf` cleans up Nginx config alongside other artifacts
- [ ] Existing deploy scripts (`make p`, `make s`, `make b/f`) are unaffected
- [ ] WebSocket connections work through cloudflared -> Nginx -> Gunicorn
- [ ] No ports exposed to the public internet (Nginx binds to 127.0.0.1 only)
