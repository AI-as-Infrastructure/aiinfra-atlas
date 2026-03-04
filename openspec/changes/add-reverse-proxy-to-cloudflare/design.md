# Design: Add Reverse Proxy to Cloudflare Tunnel Deployment

## Context
The Cloudflare Tunnel deployment currently uses FastAPI's `StaticFiles` mount to serve frontend assets directly from Gunicorn. This was a deliberate simplification (fewer moving parts), but has been identified as a security anti-pattern: the API server serves files from the same permission tree as source code and environment secrets, with no battle-tested request filtering between the internet and the filesystem.

The production deployment already uses Nginx for this purpose. This change adapts that pattern for the Cloudflare tunnel context.

## Goals / Non-Goals

**Goals:**
- Eliminate path traversal risk by serving static files from Nginx rather than the application process
- Align Cloudflare and production deployment patterns for consistency
- Add `Cache-Control: no-cache` for `index.html` to ensure Cloudflare always fetches the latest entry point
- Remove all `SERVE_STATIC` code from the backend (dead code after this change)

**Non-Goals:**
- Replacing or modifying the production Nginx configuration
- Adding SSL to the Cloudflare Nginx config (cloudflared handles TLS)
- Serving static files from a different filesystem path (keep `/opt/atlas/frontend/dist`)
- Adding Cloudflare Pages or R2 integration

## Decisions

### Decision: Nginx (same as production) rather than Caddy or HAProxy
The production deployment already uses Nginx. Reusing the same reverse proxy:
- Avoids introducing a new dependency
- Allows the Cloudflare Nginx config to be derived directly from the production template
- Means the team already understands the operational characteristics

**Alternative considered:** Caddy (simpler config, automatic HTTPS).
- Rejected: Adds a new dependency when Nginx is already proven in the stack. HTTPS is irrelevant here (cloudflared handles TLS).

**Alternative considered:** HAProxy.
- Rejected: Heavier than needed for this use case. Nginx's static file serving is a core strength.

### Decision: Nginx binds to 127.0.0.1:80 only
Unlike production where Nginx listens on public interfaces (ports 80 and 443), the Cloudflare deployment binds Nginx exclusively to `127.0.0.1:80`. Traffic flow:

```
cloudflared -> 127.0.0.1:80 (Nginx) -> 127.0.0.1:8000 (Gunicorn)
```

This means:
- No public port exposure (UFW still denies all incoming)
- cloudflared connects to Nginx on localhost
- Nginx proxies API/WS to Gunicorn on localhost
- Three layers of isolation: UFW + no public listeners + tunnel

### Decision: Derive config from production nginx.conf.template
The Cloudflare Nginx config (`nginx-cloudflare.conf.template`) is a stripped-down version of the production `nginx.conf.template`:
- Remove: SSL configuration, certbot challenge, HSTS header, HTTP-to-HTTPS redirect
- Keep: Static file serving with `try_files`, `/api` proxy, `/ws` WebSocket proxy, cache headers
- Add: `Cache-Control: no-cache` for `index.html`, `listen 127.0.0.1:80` binding

### Decision: Cache-Control: no-cache for index.html
Per the engineering lead's guidance, `index.html` must not be cached at the Cloudflare edge because it is the entry point that references hashed asset bundles. If Cloudflare caches a stale `index.html`, users will reference old asset hashes that may no longer exist.

Hashed assets (JS, CSS with content hash in filename) get long-lived cache headers as they do in production -- Cloudflare edge caching handles the rest.

```nginx
location / {
    root $APP_DIR/frontend/dist;
    try_files $uri $uri/ /index.html;

    # Prevent Cloudflare from caching index.html (the asset manifest).
    # Hashed assets (JS, CSS) are cached normally via the location block below.
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```

### Decision: Remove SERVE_STATIC code entirely from backend/app.py
After this change, no deployment path uses `SERVE_STATIC`. The code block at `backend/app.py:183-208` becomes dead code and should be removed rather than left as a dormant attack surface.

### Decision: cloudflared ingress points to Nginx (port 80) instead of Gunicorn (port 8000)
The cloudflared config changes from:
```yaml
ingress:
  - service: http://localhost:8000
```
to:
```yaml
ingress:
  - service: http://localhost:80
```

This ensures all traffic flows through Nginx before reaching the application.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Nginx config diverges from production | Derive from same template; differences are minimal and documented |
| Nginx adds a service to manage | Already in team's operational knowledge from production |
| Port 80 conflict with existing Nginx | Cloudflare deploy checks for and removes conflicting Nginx configs |
| Slightly more complex deployment | Offset by security benefits and consistency with production |

## Open Questions
None -- all resolved.
