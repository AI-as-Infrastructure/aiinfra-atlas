# Cloudflare Deployment

## MODIFIED Requirements

### Requirement: No Nginx Dependency
The Cloudflare deployment MUST use Nginx as a localhost-only reverse proxy to serve static assets and proxy API/WebSocket traffic to Gunicorn. Nginx MUST NOT listen on public interfaces.

#### Scenario: Nginx serves static assets
- **WHEN** a request for a static frontend asset arrives via the tunnel
- **THEN** cloudflared routes it to Nginx on 127.0.0.1:80
- **AND** Nginx serves the file from the Vue.js dist/ directory
- **AND** Gunicorn does not handle static file requests

#### Scenario: Nginx proxies API traffic
- **WHEN** a request for `/api` arrives via the tunnel
- **THEN** Nginx proxies the request to Gunicorn on 127.0.0.1:8000
- **AND** proxy headers (X-Real-IP, X-Forwarded-For, X-Forwarded-Proto) are set

#### Scenario: Nginx proxies WebSocket traffic
- **WHEN** a WebSocket upgrade request for `/ws` arrives via the tunnel
- **THEN** Nginx proxies the upgrade to Gunicorn on 127.0.0.1:8000
- **AND** the connection is upgraded to WebSocket protocol

#### Scenario: SPA routing fallback
- **WHEN** a request for a non-API, non-static path arrives
- **THEN** Nginx returns index.html to support Vue Router history mode

#### Scenario: Nginx binds to localhost only
- **WHEN** the deployment is complete
- **THEN** Nginx listens on 127.0.0.1:80 only
- **AND** Nginx is not accessible from any public network interface
- **AND** UFW firewall rules remain deny-all-incoming

### Requirement: No SSL Certificate Management
The Cloudflare deployment MUST NOT manage SSL certificates. TLS termination is handled by Cloudflare's edge network. Nginx MUST NOT be configured with SSL.

#### Scenario: TLS handling
- **WHEN** the deployment is complete
- **THEN** no SSL certificates exist on the origin server for this deployment
- **AND** no certbot or openssl commands are executed
- **AND** Nginx listens on HTTP (port 80) only, not HTTPS
- **AND** traffic between cloudflared and Cloudflare edge uses Cloudflare-managed encryption

## ADDED Requirements

### Requirement: Static Asset Cache Control for Cloudflare Edge
The deployment MUST configure cache headers to prevent Cloudflare from caching `index.html` while allowing long-lived caching of hashed assets.

#### Scenario: index.html not cached at edge
- **WHEN** Cloudflare edge requests index.html from the origin
- **THEN** the response includes `Cache-Control: no-cache, no-store, must-revalidate`
- **AND** Cloudflare does not serve a stale index.html to clients

#### Scenario: Hashed assets cached at edge
- **WHEN** Cloudflare edge requests a hashed asset (JS, CSS with content hash in filename)
- **THEN** the response includes `Cache-Control: public, no-transform` with a 30-day expiry
- **AND** Cloudflare caches the asset at the edge for subsequent requests

### Requirement: No Application-Layer Static File Serving
The backend application (FastAPI/Gunicorn) MUST NOT serve static frontend assets. Static file serving MUST be handled exclusively by the reverse proxy.

#### Scenario: No SERVE_STATIC code in backend
- **WHEN** the backend application starts
- **THEN** no `StaticFiles` mount is registered for frontend assets
- **AND** no SPA fallback route exists in the application code
- **AND** the `SERVE_STATIC` environment variable has no effect on application behaviour

## MODIFIED Requirements

### Requirement: Cloudflared Systemd Service
The system MUST run `cloudflared` as a systemd service with automatic restart on failure.

#### Scenario: Service configuration
- **WHEN** the deployment script creates the cloudflared service
- **THEN** the service uses the tunnel token from the environment file
- **AND** the service is enabled to start on boot
- **AND** the service restarts automatically on failure with a 5-second delay

#### Scenario: Ingress routing
- **WHEN** cloudflared receives traffic from the Cloudflare edge
- **THEN** HTTP and WebSocket requests are routed to Nginx on http://127.0.0.1:80
- **AND** unmatched hostnames receive a 404 response

### Requirement: Graceful Stop
The system MUST provide a script to gracefully stop all Cloudflare deployment services.

#### Scenario: Graceful shutdown
- **WHEN** `make scf` is executed
- **THEN** the cloudflared tunnel is stopped first
- **AND** Nginx is stopped second
- **AND** the LLM worker is stopped with time for in-flight requests
- **AND** Gunicorn is stopped
- **AND** Redis is stopped last
- **AND** systemd is reloaded

### Requirement: Clean Removal
The system MUST provide a script to completely remove the Cloudflare deployment.

#### Scenario: Full cleanup
- **WHEN** `make dcf` is executed and the operator confirms
- **THEN** all systemd services (gunicorn, llm-worker, cloudflared, nginx) are stopped and disabled
- **AND** service files are removed
- **AND** the Nginx site configuration and symlink are removed
- **AND** the application directory is removed
- **AND** log files are removed
- **AND** the cloudflared configuration file is removed

### Requirement: Cloudflare Tunnel Deployment Script
The system MUST provide a deployment script that installs and configures ATLAS behind a Cloudflare Zero Trust Tunnel with no publicly exposed ports.

#### Scenario: Successful deployment
- **WHEN** `make cf` is run with a valid `config/.env.cloudflare` containing CLOUDFLARE_TUNNEL_TOKEN and CLOUDFLARE_TUNNEL_NAME
- **THEN** the script installs system dependencies (Python, Redis, Nginx, cloudflared)
- **AND** creates a Python virtual environment with locked dependencies
- **AND** builds the Vue.js frontend
- **AND** configures Redis with authentication
- **AND** deploys the Nginx reverse proxy configuration (localhost-only)
- **AND** creates systemd services for Nginx, Gunicorn, LLM worker, and cloudflared
- **AND** starts all services
- **AND** the application is accessible via the Cloudflare Tunnel hostname

#### Scenario: Missing environment file
- **WHEN** `make cf` is run without `config/.env.cloudflare`
- **THEN** the script exits with an error message indicating the missing file

#### Scenario: Missing required environment variables
- **WHEN** `config/.env.cloudflare` exists but lacks CLOUDFLARE_TUNNEL_TOKEN or CLOUDFLARE_TUNNEL_NAME
- **THEN** the script exits with an error identifying the missing variable
