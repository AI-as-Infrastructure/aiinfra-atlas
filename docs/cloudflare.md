# Cloudflare Zero Trust Tunnel Deployment

Deploy ATLAS behind a Cloudflare Zero Trust Tunnel with no exposed ports, no nginx, and no SSL certificate management.

## Architecture

```
Internet -> Cloudflare Edge (TLS, WAF, DDoS)
         -> Zero Trust Access (SSO/MFA policies)
         -> cloudflared tunnel (outbound-only from server)
         -> 127.0.0.1:8000 (Gunicorn serves API + static files)
```

Key differences from the [production deployment](production.md):

| | Production | Cloudflare Tunnel |
|---|---|---|
| Reverse proxy | Nginx | None (cloudflared) |
| SSL | Let's Encrypt | Cloudflare Edge |
| Firewall | Ports 80/443 open | All incoming denied |
| Static files | Nginx | FastAPI (SERVE_STATIC=true) |
| Services | 4 (nginx, gunicorn, llm-worker, redis) | 4 (cloudflared, gunicorn, llm-worker, redis) |

## Prerequisites

- Ubuntu 20.04+ with apt, systemd, and outbound HTTPS
- Sudo privileges
- A Cloudflare account with Zero Trust access
- A domain managed by Cloudflare DNS

### Create the Tunnel

1. Go to [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com/) > Networks > Tunnels
2. Create a new tunnel (type: Cloudflared)
3. Copy the tunnel token
4. Add a public hostname pointing your domain to `http://localhost:8000`

## Configuration

Two environment files are required:

### 1. Cloudflare tunnel config

Create `config/.env.cloudflare` (or `config/.env.cloudflare-{env}` for multi-environment):

```bash
# Cloudflare tunnel credentials
CLOUDFLARE_TUNNEL_TOKEN="eyJhIjoi..."
CLOUDFLARE_TUNNEL_NAME="atlas-prod"
```

### 2. Application config

Use the standard application environment file (`config/.env.production` or `config/.env.{env}`). See [Configuration Guide](configuration.md) for details.

Required variables across both files:
- `CLOUDFLARE_TUNNEL_TOKEN` - from the Cloudflare dashboard
- `CLOUDFLARE_TUNNEL_NAME` - tunnel name for identification
- `VITE_API_URL` - your public domain (e.g. `https://atlas.example.com`)
- `REDIS_URL` - Redis connection string (e.g. `redis://:password@localhost:6379/1`)
- `ENVIRONMENT` - deployment environment name

### Multi-environment support

Use `CLOUDFLARE_ENV` to select environment-specific configs:

```bash
make cf                           # config/.env.cloudflare + config/.env.production
make cf CLOUDFLARE_ENV=staging    # config/.env.cloudflare-staging + config/.env.staging
make cf CLOUDFLARE_ENV=production # config/.env.cloudflare-production + config/.env.production
```

## Deployment

Clone the repository to `/opt/atlas` on the target server, then:

```bash
cd /opt/atlas
make cf
```

The script will:
1. Install system dependencies (Python 3.10, Redis, cloudflared -- no nginx)
2. Set up Python venv and install from `requirements.lock`
3. Install Node.js via nvm and build the Vue.js frontend
4. Configure Redis with authentication
5. Generate `/etc/cloudflared/config.yml`
6. Create systemd services (gunicorn, llm-worker, cloudflared)
7. Configure UFW firewall (deny all incoming, allow outgoing)
8. Start services and run health checks

### SSH access

The firewall configuration denies all incoming connections. If you need SSH access, add the rule **before** running `make cf`:

```bash
sudo ufw allow ssh
```

The deploy script will detect an existing SSH rule and preserve it.

## Lifecycle Commands

```bash
make cf    # Deploy (or redeploy)
make scf   # Graceful stop (preserves data and config for restart)
make dcf   # Full cleanup (removes services, app dir, logs)
```

For detailed help on any command:

```bash
make help-cf
make help-scf
make help-dcf
```

### Graceful stop order

`make scf` stops services in dependency order:
1. cloudflared (site goes offline immediately)
2. llm-worker (10-second wait for in-flight LLM requests)
3. gunicorn (stop API)
4. redis-server (stop last, preserves data)

### Cleanup

`make dcf` removes:
- systemd services (gunicorn, llm-worker, cloudflared)
- Application directory (`/opt/atlas`)
- Logs (`/var/log/atlas`)
- cloudflared config (`/etc/cloudflared/config.yml`)

Does **not** remove:
- UFW firewall rules (manage with `sudo ufw status`)
- Cloudflare tunnel in the dashboard (delete manually)
- Redis data

## Static File Serving

In the Cloudflare deployment there is no nginx to serve static files. Instead, Gunicorn runs with `SERVE_STATIC=true`, which activates a FastAPI static file mount in `backend/app.py`:

- `/assets/*` served from `frontend/dist/assets/`
- All other non-API routes return `index.html` (SPA fallback for Vue Router)
- This mount is added **after** API routers, so `/api/*` routes take priority

This is only active when `SERVE_STATIC=true` is set in the systemd service environment. Development and production (nginx) deployments are unaffected.

## Verify Deployment

```bash
# Check service status
sudo systemctl status cloudflared gunicorn llm-worker redis-server

# Check application logs
sudo tail -f /var/log/atlas/gunicorn-access.log
sudo tail -f /var/log/atlas/gunicorn-error.log

# Check tunnel status
sudo journalctl -u cloudflared -f

# Test locally (bypasses tunnel)
curl -s http://localhost:8000/api/health | python3 -m json.tool

# Check firewall
sudo ufw status
```

## Troubleshooting

### Tunnel not connecting

```bash
# Check cloudflared logs
sudo journalctl -u cloudflared -n 50

# Verify token is correct
sudo systemctl cat cloudflared | grep token
```

Common causes:
- Invalid or expired tunnel token (regenerate in Cloudflare dashboard)
- Outbound HTTPS blocked (cloudflared needs port 443 outbound)
- DNS CNAME not pointing to the tunnel

### Static files not loading

```bash
# Verify frontend was built
ls -la /opt/atlas/frontend/dist/

# Check SERVE_STATIC is set
sudo systemctl cat gunicorn | grep SERVE_STATIC

# Check gunicorn logs for static file mount
sudo grep -i "static" /var/log/atlas/gunicorn-error.log
```

### Service startup failures

```bash
# Check individual service logs
sudo journalctl -u gunicorn --no-pager -n 50
sudo journalctl -u llm-worker --no-pager -n 50
sudo journalctl -u cloudflared --no-pager -n 50

# Verify environment file is readable
cat /opt/atlas/config/.env.production
```

### LAN fallback

If the tunnel goes down, the application is still accessible on the local network:

```
http://localhost:8000
```

This bypasses Cloudflare entirely and connects directly to Gunicorn.

## Security Notes

- No ports are exposed to the internet; all traffic flows through Cloudflare's edge
- Zero Trust Access policies (SSO, MFA, device posture) are configured in the Cloudflare dashboard, not on the server
- UFW denies all incoming connections by default
- Redis is authenticated via password extracted from `REDIS_URL`
- The tunnel token is the primary credential -- treat it like a private key
