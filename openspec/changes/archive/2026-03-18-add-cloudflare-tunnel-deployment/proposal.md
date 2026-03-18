# Proposal: Add Cloudflare Zero Trust Tunnel Deployment

## Change ID
`add-cloudflare-tunnel-deployment`

## Summary
Add a self-contained Cloudflare Zero Trust Tunnel deployment option alongside existing production/staging deploy scripts, replacing nginx and SSL certificate management with `cloudflared` tunnels for maximum security posture.

## Motivation
The current production deployment (`deploy/production/`) assumes a Linux VM with nginx reverse proxy and Let's Encrypt SSL. Two emerging use cases require a different approach:

1. **Home web server**: Researchers hosting ATLAS on a personal server behind NAT/CGNAT need secure public access without port forwarding or dynamic DNS.
2. **National research infrastructure**: Institutional Linux VMs where reputational risk demands zero-trust access controls (identity-aware proxy, no exposed ports).

Cloudflare Tunnel (`cloudflared`) addresses both by:
- Publishing no ports -- the tunnel initiates outbound-only connections to Cloudflare's edge
- Eliminating SSL certificate management -- Cloudflare handles TLS termination
- Enabling Zero Trust access policies (SSO, MFA, email-based OTP) via the Cloudflare dashboard
- Providing DDoS protection, WAF, and bot management at the edge

## Scope

### In Scope
- New `deploy/cloudflare/` directory with deploy, stop, and clean scripts
- Makefile targets: `cf` (deploy), `scf` (stop), `dcf` (clean)
- Help targets: `help-cf`, `help-dcf`, `help-scf`
- Cloudflare-specific environment variables in `config/.env.template`
- Cloudflare tunnel vars set in `config/.env.production` (single env file, no separate overlay)
- `cloudflared` systemd service configuration with ingress rules
- Gunicorn serving both API and static frontend assets (no nginx)
- FastAPI static file mount for Vue.js `dist/` directory
- UFW firewall configuration (deny all incoming, allow outgoing only)
- Cloud-agnostic: works on any Linux VM with apt, systemd, and outbound HTTPS

### Out of Scope
- Changes to existing `deploy/production/`, `deploy/staging/`, or `deploy/dev/` scripts
- Cloudflare dashboard configuration (Zero Trust policies, DNS records, tunnel creation)
- Cloudflare Access application setup (documented in comments, configured by operator)
- Changes to backend application code (FastAPI, LLM modules)
- Frontend code changes

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
              127.0.0.1:8000
                       |
            Gunicorn + Uvicorn
            ┌──────────┬──────────┐
            │          │          │
         /api       /ws      /* (static)
        FastAPI   WebSocket  Vue.js dist/
            │
         Redis (127.0.0.1:6379)
```

Key differences from existing production deploy:
- No nginx -- Gunicorn serves static files directly via FastAPI `StaticFiles` mount
- No SSL certificates -- Cloudflare handles TLS at the edge
- No published ports -- `cloudflared` creates outbound-only tunnels
- UFW blocks all inbound traffic -- defence in depth at the OS level
- Cloud-agnostic -- no AWS, GCP, or Azure assumptions

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cloudflare service outage | Low | High | Document fallback to direct Gunicorn access on LAN |
| Tunnel token compromise | Low | High | Token stored in core env file (gitignored), rotatable via dashboard |
| Static file serving perf | Medium | Low | Cloudflare edge caching handles most static requests |
| WebSocket connection drops | Low | Medium | `cloudflared` natively supports WS; retry logic already in frontend |
| Gunicorn static file overhead | Low | Low | Production traffic is API-heavy; static assets cached at edge |
| UFW blocks SSH if not pre-allowed | Low | Medium | Script warns operator before enabling; SSH rule is operator's responsibility |

## Related
- `deploy/production/production.sh` -- Existing nginx+Gunicorn deploy (unchanged)
- `deploy/staging/staging_localhost.sh` -- Existing localhost staging (unchanged)
- Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/

## Acceptance Criteria
- [ ] `make cf` deploys ATLAS behind a Cloudflare Tunnel with no exposed ports
- [ ] `make scf` gracefully stops all services
- [ ] `make dcf` cleanly removes the Cloudflare deployment
- [ ] Existing deploy scripts (`make p`, `make s`, `make b/f`) are unaffected
- [ ] WebSocket connections work through the tunnel
- [ ] Static frontend assets served correctly via Gunicorn
- [ ] Script validates all required environment variables before proceeding
- [ ] `cloudflared` runs as a systemd service with automatic restart
- [ ] UFW configured to deny all incoming traffic
- [ ] All config loaded from single `config/.env.production` file
- [ ] Script is cloud-agnostic (no AWS/GCP/Azure assumptions)
