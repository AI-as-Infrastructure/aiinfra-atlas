# Cloudflare Zero Trust Tunnel Deployment

Deploy ATLAS behind a Cloudflare Zero Trust Tunnel with no exposed ports and no SSL certificate management.

## Deployment Checklist

End-to-end sequence for a fresh deployment. Each step references the detailed section below.

### 1. Cloudflare dashboard

- [ ] Create a Cloudflare Tunnel (Networks > Tunnels > Create, type: Cloudflared) and copy the token
- [ ] Add public hostname route for the app (`http://localhost:80`) -- see [Tunnel setup](#cloudflare-zero-trust-tunnel)
- [ ] Add public hostname route for SSH (`ssh://localhost:22`) if needed
- [ ] Verify DNS CNAME records were auto-created for each route
- [ ] Set SSL/TLS mode to **Full** (SSL/TLS > Overview) -- see [Dashboard assumptions](#cloudflare-dashboard-assumptions)
- [ ] Create a Cloudflare Access application for the app domain -- see [Cloudflare Access](#cloudflare-access-authentication)
- [ ] Create an Allow policy with your identity rules (emails, domain, IdP)
- [ ] Note the **Application Audience (AUD) tag** and **Team domain** for JWT validation
- [ ] Optionally create a separate Access application for SSH with tighter policies

### 2. Server prerequisites

- [ ] Install system packages (Python 3.10, Redis, Nginx, etc.) -- see [System packages](#system-packages)
- [ ] Install cloudflared -- see [cloudflared](#cloudflared)
- [ ] Install the tunnel connector: `sudo cloudflared service install <token>` -- see [Cloudflare Zero Trust tunnel](#cloudflare-zero-trust-tunnel)
- [ ] Verify tunnel is running: `sudo systemctl status cloudflared`
- [ ] Configure Redis authentication -- see [Redis authentication](#redis-authentication)
- [ ] Configure UFW firewall (deny all incoming, allow outbound 443/53) -- see [Firewall](#firewall)

### 3. Application configuration

- [ ] Clone the repository to `/opt/atlas`
- [ ] Copy `config/.env.template` to `config/.env.production`
- [ ] Set required variables (`AUTH_METHOD=cloudflare`, tunnel token, `VITE_API_URL`, `REDIS_URL`, etc.) -- see [Configuration](#configuration)
- [ ] Set JWT validation variables (`CLOUDFLARE_TEAM_DOMAIN`, `CLOUDFLARE_ACCESS_AUD`) -- see [JWT validation](#configuring-jwt-validation-defence-in-depth)
- [ ] Generate `requirements.lock` if needed (`make l`)

### 4. Deploy

- [ ] Run `make cf` -- see [Deployment](#deployment)

### 5. Verify

- [ ] Check all services are running -- see [Verify Deployment](#verify-deployment)
- [ ] Test backend directly: `curl -s http://127.0.0.1:8000/api/health`
- [ ] Test full path: open `https://YOUR_DOMAIN` in a browser (should see Access login gate)
- [ ] Verify firewall: `sudo ufw status` (no incoming ports open)

## Architecture

```
Internet -> Cloudflare Edge (TLS, WAF, DDoS)
         -> Zero Trust Access (SSO/MFA policies)
         -> cloudflared tunnel (outbound-only from server)
         -> Nginx (127.0.0.1:80, localhost-only reverse proxy)
         -> static files (frontend/dist) | proxy /api /ws -> Gunicorn (127.0.0.1:8000)
```

Key differences from the [production deployment](production.md):

| | Production | Cloudflare Tunnel |
|---|---|---|
| Reverse proxy | Nginx (public, SSL) | Nginx (localhost-only, no SSL) |
| SSL | Let's Encrypt | Cloudflare Edge |
| Firewall | Ports 80/443 open | All incoming denied |
| Static files | Nginx | Nginx |
| Services (deploy-managed) | 4 (nginx, gunicorn, llm-worker, redis) | 3 (nginx, gunicorn, llm-worker) + cloudflared (operator-managed) + redis |

## Server Prerequisites

The deploy script assumes the server is already set up and hardened. Install and configure the following before running `make cf`:

### System packages

```bash
sudo apt install -y python3.10 python3.10-venv python3.10-dev git-lfs redis-server nginx curl build-essential make tmux
```

### cloudflared

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared
```

### Redis authentication

Configure Redis with a password matching the `REDIS_URL` in your application env file:

```bash
# Extract password from your REDIS_URL (e.g. redis://:mypassword@localhost:6379/1)
sudo sed -i "/^#* *requirepass /d" /etc/redis/redis.conf
sudo bash -c "echo 'requirepass YOUR_REDIS_PASSWORD' >> /etc/redis/redis.conf"
sudo systemctl restart redis-server
```

### Firewall

Configure UFW (or equivalent) according to your security requirements. The deploy script does not modify firewall rules. At minimum, ensure outbound HTTPS (443) and DNS (53) are allowed for cloudflared.

### Cloudflare Zero Trust tunnel

The cloudflared tunnel is **operator-managed** -- the deploy script (`make cf`) does not create, modify, or restart the cloudflared service. This prevents application deploys from breaking SSH access through the tunnel.

1. Go to [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com/) > Networks > Tunnels
2. Create a new tunnel (type: **Cloudflared**)
3. Add **public hostname routes** for each service:

| Route | Subdomain | Domain | Path | Service | Description |
|-------|-----------|--------|------|---------|-------------|
| ATLAS app | `atlas-hansard` | `yourdomain.org` | *(empty)* | `http://localhost:80` | Main application (via Nginx) |
| SSH web | `ssh-web` | `yourdomain.org` | *(empty)* | `ssh://localhost:22` | Browser-based SSH (Cloudflare renders terminal) |

For each route, go to the tunnel's **Public Hostname** tab and click **Add a public hostname**. Set the subdomain, domain, and service URL as above.

4. **Install the connector on the server** using the command from the dashboard:

```bash
sudo cloudflared service install <token>
```

This registers the connector, stores credentials, and creates a systemd service that starts on boot. The token from this command is also used as `CLOUDFLARE_TUNNEL_TOKEN` in the env file.

5. Verify the tunnel is running:

```bash
sudo systemctl status cloudflared
```

**DNS records**: Each public hostname route automatically creates a CNAME record in Cloudflare DNS pointing the subdomain to the tunnel. Verify these exist in your domain's DNS settings.

**Important**: Do not create a local `/etc/cloudflared/config.yml` file. Token-based tunnels are configured entirely via the dashboard. A local config file would override dashboard routes and break non-HTTP services (like SSH).

## Configuration

All settings (application config and Cloudflare tunnel vars) live in a single environment file. Copy `config/.env.template` and set the values for your environment.

Required variables:
- `AUTH_METHOD=cloudflare` - enables Cloudflare Access header-based identity
- `CLOUDFLARE_TUNNEL_TOKEN` - from the Cloudflare Zero Trust dashboard
- `CLOUDFLARE_TUNNEL_NAME` - tunnel name for identification
- `VITE_API_URL` - your public domain (e.g. `https://atlas.example.com`)
- `REDIS_URL` - Redis connection string (e.g. `redis://:password@localhost:6379/1`)
- `ENVIRONMENT` - deployment environment name

Optional (defence-in-depth):
- `CLOUDFLARE_TEAM_DOMAIN` - team domain for JWT validation (Settings > Custom Pages > Team domain)
- `CLOUDFLARE_ACCESS_AUD` - application audience tag (Access > Applications > your app > Overview)
- `RATE_LIMIT_PER_MINUTE` - rate limit for query endpoints (default: 60)

See [Configuration Guide](configuration.md) for full details on all application settings.

## Deployment

Clone the repository to `/opt/atlas` on the target server.

The deploy script does **not** restart cloudflared, so SSH tunnel sessions are not interrupted. Running inside `tmux` is recommended for long deploys in case of network issues:

```bash
tmux
cd /opt/atlas
make cf
```

If your SSH session drops mid-deploy, reconnect and reattach with `tmux attach`.

The script will:
1. Check server prerequisites (Python 3.10, Redis, Nginx, cloudflared running)
2. Set up Python venv and install from `requirements.lock`
3. Install Node.js via nvm and build the Vue.js frontend
4. Configure Nginx as a localhost-only reverse proxy (static files + API/WS proxy)
5. Create systemd services (gunicorn, llm-worker)
6. Start application services and run health checks

The script does **not** install system packages, configure the firewall, set up Redis authentication, or manage the cloudflared service -- these are server prerequisites handled by the operator.

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

`make scf` stops application services in dependency order (cloudflared is **not** stopped -- it is operator-managed and may serve SSH access):
1. nginx (site goes offline)
2. llm-worker (10-second wait for in-flight LLM requests)
3. gunicorn (stop API)
4. redis-server (stop last, preserves data)

### Cleanup

`make dcf` removes:
- systemd services (gunicorn, llm-worker)
- Nginx site configuration
- Application directory (`/opt/atlas`)
- Logs (`/var/log/atlas`)

Does **not** remove:
- cloudflared (operator-managed; uninstall with `sudo cloudflared service uninstall`)
- Nginx package (uninstall manually if needed)
- UFW firewall rules (manage with `sudo ufw status`)
- Cloudflare tunnel in the dashboard (delete manually)
- Redis data

## Static File Serving

Static files are served by Nginx from `frontend/dist/`, the same pattern as the production deployment. Nginx runs as a localhost-only reverse proxy (`127.0.0.1:80`) between cloudflared and Gunicorn:

- `/*` -- static files from `frontend/dist/` with SPA fallback (`try_files` to `index.html`)
- `/api/*` -- proxied to Gunicorn on `127.0.0.1:8000`
- `/ws/*` -- proxied with WebSocket upgrade to Gunicorn on `127.0.0.1:8000`

### Cache headers

- `index.html` is served with `Cache-Control: no-cache, no-store, must-revalidate` to prevent Cloudflare from caching a stale entry point. This is critical because `index.html` references hashed asset bundles that change on each build.
- Hashed assets (JS, CSS, images, fonts) are served with `expires 30d` and `Cache-Control: public, no-transform`, allowing Cloudflare edge caching.

## Verify Deployment

```bash
# Check service status
sudo systemctl status cloudflared nginx gunicorn llm-worker redis-server

# Check application logs
sudo tail -f /var/log/atlas/gunicorn-access.log
sudo tail -f /var/log/atlas/gunicorn-error.log

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Check tunnel status
sudo journalctl -u cloudflared -f

# Test backend directly (bypasses nginx and tunnel)
curl -s http://127.0.0.1:8000/api/health | python3 -m json.tool

# Test via tunnel (full path through Cloudflare edge)
curl -s https://YOUR_DOMAIN/api/health | python3 -m json.tool

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
- Invalid or expired tunnel token (regenerate in Cloudflare dashboard and reinstall with `sudo cloudflared service install <new-token>`)
- Outbound HTTPS blocked (cloudflared needs port 443 outbound)
- DNS CNAME not pointing to the tunnel

### Static files not loading

```bash
# Verify frontend was built
ls -la /opt/atlas/frontend/dist/

# Check Nginx config is valid
sudo nginx -t

# Check Nginx is serving the site
sudo ls -la /etc/nginx/sites-enabled/

# Check Nginx logs
sudo tail -20 /var/log/nginx/error.log
```

### Service startup failures

```bash
# Check individual service logs
sudo journalctl -u nginx --no-pager -n 50
sudo journalctl -u gunicorn --no-pager -n 50
sudo journalctl -u llm-worker --no-pager -n 50
sudo journalctl -u cloudflared --no-pager -n 50

# Verify environment file is readable (includes Cloudflare tunnel vars)
cat /opt/atlas/config/.env.production
```

### Localhost access

Direct localhost access is blocked by nginx origin verification. Nginx rejects requests without a `Cf-Ray` header (which only Cloudflare adds), so `curl http://localhost` returns 403.

To diagnose the backend when the tunnel is down, query Gunicorn directly (bypassing nginx):

```bash
curl -s http://127.0.0.1:8000/api/health | python3 -m json.tool
```

If you need full nginx-proxied access for debugging, temporarily comment out the `Cf-Ray` check in `/etc/nginx/sites-available/atlas` and reload nginx. Restore it when done.

## Cloudflare Access (Authentication)

Cloudflare Access puts an authentication layer in front of the ATLAS application at the Cloudflare edge. Users must authenticate before any request reaches the origin server. This is configured entirely in the Cloudflare dashboard -- the deploy script does not manage Access policies.

### Setting up Cloudflare Access

1. Go to [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com/) > Access > Applications
2. Click **Add an application** > **Self-hosted**

#### ATLAS application policy

| Setting | Value |
|---------|-------|
| Application name | `ATLAS Hansard` (or your preferred name) |
| Session duration | `24 hours` (adjust for your use case) |
| Application domain | `atlas-hansard.yourdomain.org` |

3. Under **Policies**, create an **Allow** policy:
   - **Policy name**: e.g. `Allow research team`
   - **Include rule**: Use one of:
     - **Emails**: List specific email addresses
     - **Emails ending in**: e.g. `@youruniversity.edu` for institutional access
     - **Access groups**: Pre-defined groups from your identity provider
   - **Authentication method**: Select identity providers (e.g. One-time PIN, Google, GitHub, SAML)

4. Under **Settings** (optional):
   - Enable **CORS bypass** if needed for API testing tools
   - Set **Cookie same-site attribute** to `Lax`

#### SSH application policy

| Setting | Value |
|---------|-------|
| Application name | `SSH Web Access` |
| Session duration | `1 hour` (shorter for SSH) |
| Application domain | `ssh-web.yourdomain.org` |
| Application type | Self-hosted |

5. Under **Policies**, create an **Allow** policy with more restrictive access (e.g. specific admin emails only)
6. Under **Settings**, enable **Browser rendering** for SSH (this renders the terminal in the browser)

### Configuring JWT validation (defence-in-depth)

Once Cloudflare Access is set up, configure JWT validation on the backend for defence-in-depth. This verifies that requests actually passed through Cloudflare Access (not spoofed headers).

1. In the Zero Trust dashboard, go to **Settings** > **Custom Pages** and note your **Team domain** (e.g. `yourteam.cloudflareaccess.com`)
2. Go to **Access** > **Applications** > your ATLAS app > **Overview** and copy the **Application Audience (AUD) tag**
3. Add both to your `.env.production`:

```bash
CLOUDFLARE_TEAM_DOMAIN="yourteam.cloudflareaccess.com"
CLOUDFLARE_ACCESS_AUD="your-application-audience-tag"
```

When both are set, the backend validates `Cf-Access-Jwt-Assertion` JWT headers using Cloudflare's public keys (RS256). Requests without a valid JWT are rejected with 401. When unset, the backend falls back to trusting the `Cf-Access-Authenticated-User-Email` header (safe when the origin is unreachable outside the tunnel, but JWT validation is recommended).

See [Authentication](authentication.md) for details on how the backend processes Cloudflare identity.

### Cloudflare dashboard assumptions

The deploy script assumes the following are configured in the Cloudflare dashboard (not on the server):

| Component | Where to configure | What to set |
|-----------|-------------------|-------------|
| Tunnel routes | Networks > Tunnels > your tunnel > Public Hostname | HTTP route to `localhost:80`, SSH route to `localhost:22` |
| Access policies | Access > Applications | Allow/deny rules, identity providers, session duration |
| DNS records | DNS > Records | CNAME records for each subdomain (auto-created by tunnel routes) |
| WAF rules | Security > WAF | Cloudflare-managed rulesets (enabled by default) |
| DDoS protection | Security > DDoS | Enabled by default on all Cloudflare plans |
| SSL/TLS mode | SSL/TLS > Overview | Set to **Full** (Cloudflare terminates TLS, connects to origin over HTTP via tunnel) |
| HSTS | SSL/TLS > Edge Certificates | Enable HSTS if desired (applied at edge, not by Nginx) |
| Caching | Caching > Configuration | Default caching respects Cache-Control headers from Nginx |

## Security Notes

- No ports are exposed to the internet; all traffic flows through Cloudflare's edge
- Nginx binds to `127.0.0.1:80` only -- not accessible from public network interfaces
- Nginx origin verification rejects requests without `Cf-Ray` header (blocks direct localhost access)
- Cloudflare Access JWT validation available as defence-in-depth (see above and [Authentication](authentication.md))
- Query endpoints are rate-limited (configurable via `RATE_LIMIT_PER_MINUTE`, default 60/min)
- CORS restricted to GET/POST/OPTIONS with explicit header allowlist
- Error messages sanitised -- no env var names or provider details leak to clients
- cloudflared is operator-managed (installed via `cloudflared service install`) -- the deploy script never modifies or restarts it, preserving SSH access during deploys
- Static files are served by Nginx (a battle-tested web server), not the application process
- Zero Trust Access policies (SSO, MFA, device posture) are configured in the Cloudflare dashboard, not on the server
- UFW denies all incoming connections by default; deploy script verifies port 8000 is not exposed
- Redis is authenticated via password extracted from `REDIS_URL`
- The tunnel token is the primary credential -- treat it like a private key
- Redeploying (`make cf`) restarts cloudflared, briefly disconnecting the tunnel (including SSH sessions)
