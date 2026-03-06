# Cloudflare Zero Trust Tunnel Deployment

Deploy ATLAS behind a Cloudflare Zero Trust Tunnel with no exposed ports and no SSL certificate management.

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
| Services | 4 (nginx, gunicorn, llm-worker, redis) | 5 (cloudflared, nginx, gunicorn, llm-worker, redis) |

## Server Prerequisites

The deploy script assumes the server is already set up and hardened. Install and configure the following before running `make cf`:

### System packages

```bash
sudo apt install -y python3.10 python3.10-venv python3.10-dev git-lfs redis-server nginx curl build-essential make
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

1. Go to [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com/) > Networks > Tunnels
2. Create a new tunnel (type: Cloudflared)
3. Copy the tunnel token
4. Add a public hostname pointing your domain to `http://localhost:80`

## Configuration

All settings (application config and Cloudflare tunnel vars) live in a single environment file. Copy `config/.env.template` and set the values for your environment.

Required variables:
- `AUTH_METHOD=cloudflare` - enables Cloudflare Access header-based identity
- `CLOUDFLARE_TUNNEL_TOKEN` - from the Cloudflare Zero Trust dashboard
- `CLOUDFLARE_TUNNEL_NAME` - tunnel name for identification
- `VITE_API_URL` - your public domain (e.g. `https://atlas.example.com`)
- `REDIS_URL` - Redis connection string (e.g. `redis://:password@localhost:6379/1`)
- `ENVIRONMENT` - deployment environment name

See [Configuration Guide](configuration.md) for full details on all application settings.

## Deployment

Clone the repository to `/opt/atlas` on the target server, then:

```bash
cd /opt/atlas
make cf
```

The script will:
1. Check server prerequisites (Python 3.10, Redis, Nginx, cloudflared)
2. Set up Python venv and install from `requirements.lock`
3. Install Node.js via nvm and build the Vue.js frontend
4. Configure Nginx as a localhost-only reverse proxy (static files + API/WS proxy)
5. Generate `/etc/cloudflared/config.yml`
6. Create systemd services (gunicorn, llm-worker, cloudflared)
7. Start services and run health checks

The script does **not** install system packages, configure the firewall, or set up Redis authentication -- these are server prerequisites handled by the operator.

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
2. nginx (stop reverse proxy)
3. llm-worker (10-second wait for in-flight LLM requests)
4. gunicorn (stop API)
5. redis-server (stop last, preserves data)

### Cleanup

`make dcf` removes:
- systemd services (gunicorn, llm-worker, cloudflared)
- Nginx site configuration
- Application directory (`/opt/atlas`)
- Logs (`/var/log/atlas`)
- cloudflared config (`/etc/cloudflared/config.yml`)

Does **not** remove:
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

# Test locally (bypasses tunnel, goes through Nginx)
curl -s http://localhost:80/api/health | python3 -m json.tool

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

### LAN fallback

If the tunnel goes down, the application is still accessible on the local network:

```
http://localhost:80
```

This bypasses Cloudflare entirely and connects directly to Nginx, which proxies to Gunicorn.

## Security Notes

- No ports are exposed to the internet; all traffic flows through Cloudflare's edge
- Nginx binds to `127.0.0.1:80` only -- not accessible from public network interfaces
- Static files are served by Nginx (a battle-tested web server), not the application process
- Zero Trust Access policies (SSO, MFA, device posture) are configured in the Cloudflare dashboard, not on the server
- UFW denies all incoming connections by default
- Redis is authenticated via password extracted from `REDIS_URL`
- The tunnel token is the primary credential -- treat it like a private key
