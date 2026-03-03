# Design: Cloudflare Zero Trust Tunnel Deployment

## Context
ATLAS needs a deployment option for environments where:
- The server is behind NAT/CGNAT (home networks, institutional firewalls)
- No ports can be exposed to the internet
- Zero-trust identity verification is required
- SSL certificate management overhead must be eliminated

Cloudflare Tunnel (`cloudflared`) meets all constraints by creating outbound-only encrypted connections from the origin server to Cloudflare's edge network.

## Goals / Non-Goals

**Goals:**
- Self-contained deploy script that does not modify existing deployment paths
- No exposed ports on the origin server
- No nginx dependency
- No SSL certificate management
- Systemd-managed services for all components
- Support for both home server and institutional VM environments

**Non-Goals:**
- Replacing the existing EC2+nginx production deployment
- Automating Cloudflare dashboard configuration (tunnel creation, DNS, Zero Trust policies)
- Multi-region or high-availability tunnel configuration
- Cloudflare Workers or Pages integration

## Decisions

### Decision: Token-based tunnel authentication (not cert-based)
Cloudflare supports two tunnel authentication modes:
1. **Certificate-based** (locally managed): `cloudflared tunnel create` generates a tunnel credential file
2. **Token-based** (remotely managed): Tunnel created in Cloudflare dashboard, token passed to `cloudflared`

**Chosen: Token-based.** Rationale:
- Tunnel configuration managed in Cloudflare dashboard (single pane of glass with Zero Trust policies)
- Token is a single string stored in `.env.cloudflare` -- simpler than managing credential JSON files
- Tunnel can be monitored and reconfigured from dashboard without SSH access to origin
- Aligns with zero-trust philosophy (management plane separate from data plane)

### Decision: Gunicorn serves static files (no nginx)
The existing production deploy uses nginx to serve Vue.js `dist/` static files and proxy API/WS to Gunicorn. For the Cloudflare deployment:

**Chosen: Gunicorn serves everything via FastAPI `StaticFiles` mount.** Rationale:
- Eliminates nginx as a dependency entirely
- Cloudflare edge caches static assets (Cache-Control headers), offsetting Gunicorn's lower static file throughput
- Simplifies the deployment to two services: Gunicorn + cloudflared
- ATLAS is a research tool with low concurrent user counts; Gunicorn is sufficient

**Alternative considered:** Keep nginx as local reverse proxy between cloudflared and Gunicorn.
- Rejected: adds unnecessary complexity for the target use case (single-digit concurrent users)

### Decision: Ingress rules use HTTP (not WS protocol)
Cloudflare Tunnel handles WebSocket upgrades transparently when the ingress service URL uses `http://`. There is no need to specify `ws://` separately.

**Chosen: Single `http://localhost:8000` ingress rule.** Rationale:
- `cloudflared` detects the `Upgrade: websocket` header and handles the upgrade automatically
- Simpler configuration than separate HTTP and WS ingress rules
- Matches Cloudflare's own documentation recommendations

### Decision: Config file approach for cloudflared
`cloudflared` can run with either CLI flags or a YAML config file.

**Chosen: YAML config file at `/etc/cloudflared/config.yml`.** Rationale:
- Ingress rules are complex to express as CLI flags
- Config file is auditable and version-controllable
- Matches the pattern used by existing deploy scripts (nginx.conf.template)

### Decision: UFW firewall to block all inbound connections
The deploy script MUST configure UFW to deny all incoming traffic and allow only outbound connections. This enforces the zero-trust posture at the OS level -- even if cloudflared is misconfigured, no ports are reachable.

**Chosen: UFW deny incoming, allow outgoing.** Rationale:
- Defence in depth: firewall + no listening ports + tunnel = three layers
- UFW is standard on Ubuntu and simpler than raw iptables
- SSH access preserved only if explicitly allowed by the operator before running the script
- Script will warn about SSH implications before enabling UFW

**Rules applied:**
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow out 443/tcp   # cloudflared outbound to Cloudflare edge
ufw allow out 53        # DNS resolution
ufw --force enable
```

Note: The script will NOT add an SSH allow rule automatically. Operators who need SSH access must add `ufw allow ssh` before or after deployment. This is deliberate -- for home servers behind NAT, SSH is typically accessed via LAN and doesn't need a firewall rule. For institutional VMs, SSH access policies are site-specific.

### Decision: Multiple tunnel support via environment files
Different environments (staging, production) use separate tunnel tokens and names, following the existing `.env.{environment}` pattern.

**Chosen: `config/.env.cloudflare` as the default, with `CLOUDFLARE_ENV` override.** Rationale:
- Mirrors the existing pattern (`config/.env.production`, `config/.env.staging`)
- Operators can create `config/.env.cloudflare-staging` and `config/.env.cloudflare-production`
- The `CLOUDFLARE_ENV` variable (or a Makefile argument) selects which file to use
- Each environment has its own `CLOUDFLARE_TUNNEL_TOKEN` and `CLOUDFLARE_TUNNEL_NAME`
- Tunnel-specific Zero Trust policies are managed in the Cloudflare dashboard per tunnel

### Decision: Static files served from origin VM (not Cloudflare Pages/R2)
Static Vue.js assets could be deployed to Cloudflare Pages or R2 for edge-native serving, or served from the origin VM via Gunicorn.

**Chosen: Origin VM via Gunicorn.** Rationale:
- Single atomic deployment (`make cf` deploys everything)
- No additional Cloudflare service dependency (Pages, R2, Wrangler CLI)
- No split deployment to reason about or debug
- Cloudflare edge caches static assets via Cache-Control headers regardless
- Research tool with single-digit concurrent users -- origin throughput is not a bottleneck

**Alternative considered:** Cloudflare Pages for frontend, tunnel for API only.
- Rejected: adds deployment complexity, requires separate build pipeline and Wrangler tooling, splits the application across two deployment mechanisms

### Decision: Cloud-agnostic deployment
The existing `deploy/production/production.sh` is already mostly cloud-agnostic (standard apt, systemd, SSH). The only cloud-specific code is the EC2 instance lookup in `stop_production.sh`. The Cloudflare deployment script will be fully cloud-agnostic.

**Chosen: No cloud provider assumptions.** Rationale:
- Target environments include home servers (no cloud), university VMs (various providers), and generic Linux VPS
- The script requires only: Ubuntu/Debian with apt, systemd, and outbound HTTPS connectivity
- Connection to the server for deployment is via SSH (operator's responsibility) or local execution

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Cloudflare outage = site down | Document LAN-only access as fallback (Gunicorn on localhost:8000) |
| Token in .env file | File is gitignored; document rotation procedure |
| No nginx = no request buffering | Cloudflare edge buffers requests; Gunicorn timeout handles slow clients |
| Static file perf without nginx | Edge caching; research tool traffic is API-dominant |
| UFW blocks SSH if not pre-allowed | Script warns operator; SSH rule must be added explicitly |
| UFW not installed on non-Ubuntu | Script checks for UFW availability; skips with warning if absent |

## Open Questions
None -- all resolved.
