# Cloudflare Deployment

## ADDED Requirements

### Requirement: Cloudflare Tunnel Deployment Script
The system MUST provide a deployment script that installs and configures ATLAS behind a Cloudflare Zero Trust Tunnel with no publicly exposed ports.

#### Scenario: Successful deployment
- **WHEN** `make cf` is run with a valid environment file (e.g. `config/.env.production`) containing CLOUDFLARE_TUNNEL_TOKEN and CLOUDFLARE_TUNNEL_NAME
- **THEN** the script installs system dependencies (Python, Redis, cloudflared)
- **AND** creates a Python virtual environment with locked dependencies
- **AND** builds the Vue.js frontend
- **AND** configures Redis with authentication
- **AND** creates systemd services for Gunicorn, LLM worker, and cloudflared
- **AND** starts all services
- **AND** the application is accessible via the Cloudflare Tunnel hostname

#### Scenario: Missing environment file
- **WHEN** `make cf` is run without a valid environment file (e.g. `config/.env.production`)
- **THEN** the script exits with an error message indicating the missing file

#### Scenario: Missing required environment variables
- **WHEN** the environment file exists but lacks CLOUDFLARE_TUNNEL_TOKEN or CLOUDFLARE_TUNNEL_NAME
- **THEN** the script exits with an error identifying the missing variable

### Requirement: No Exposed Ports
The Cloudflare deployment MUST NOT expose any ports to the public internet. All services MUST bind exclusively to localhost (127.0.0.1).

#### Scenario: Service binding
- **WHEN** the deployment is complete
- **THEN** Gunicorn binds to 127.0.0.1:8000
- **AND** Redis binds to 127.0.0.1:6379
- **AND** no nginx or other reverse proxy listens on public interfaces
- **AND** cloudflared creates outbound-only connections to Cloudflare edge

### Requirement: No Nginx Dependency
The Cloudflare deployment MUST NOT require nginx. Gunicorn MUST serve both the FastAPI API and Vue.js static assets.

#### Scenario: Static asset serving
- **WHEN** a request for a static frontend asset arrives via the tunnel
- **THEN** Gunicorn serves the file from the Vue.js dist/ directory
- **AND** appropriate Cache-Control headers are set for edge caching

#### Scenario: SPA routing fallback
- **WHEN** a request for a non-API, non-static path arrives
- **THEN** the system returns index.html to support Vue Router history mode

### Requirement: No SSL Certificate Management
The Cloudflare deployment MUST NOT manage SSL certificates. TLS termination is handled by Cloudflare's edge network.

#### Scenario: TLS handling
- **WHEN** the deployment is complete
- **THEN** no SSL certificates exist on the origin server for this deployment
- **AND** no certbot or openssl commands are executed
- **AND** traffic between cloudflared and Cloudflare edge uses Cloudflare-managed encryption

### Requirement: Cloudflared Systemd Service
The system MUST run `cloudflared` as a systemd service with automatic restart on failure.

#### Scenario: Service configuration
- **WHEN** the deployment script creates the cloudflared service
- **THEN** the service uses the tunnel token from the environment file
- **AND** the service is enabled to start on boot
- **AND** the service restarts automatically on failure with a 5-second delay

#### Scenario: Ingress routing
- **WHEN** cloudflared receives traffic from the Cloudflare edge
- **THEN** HTTP and WebSocket requests are routed to http://127.0.0.1:8000
- **AND** unmatched hostnames receive a 404 response

### Requirement: Graceful Stop
The system MUST provide a script to gracefully stop all Cloudflare deployment services.

#### Scenario: Graceful shutdown
- **WHEN** `make scf` is executed
- **THEN** the cloudflared tunnel is stopped first
- **AND** the LLM worker is stopped with time for in-flight requests
- **AND** Gunicorn is stopped
- **AND** Redis is stopped last
- **AND** systemd is reloaded

### Requirement: Clean Removal
The system MUST provide a script to completely remove the Cloudflare deployment.

#### Scenario: Full cleanup
- **WHEN** `make dcf` is executed and the operator confirms
- **THEN** all systemd services (gunicorn, llm-worker, cloudflared) are stopped and disabled
- **AND** service files are removed
- **AND** the application directory is removed
- **AND** log files are removed
- **AND** the cloudflared configuration file is removed

### Requirement: UFW Firewall Hardening
The deployment script MUST configure UFW to deny all incoming connections, enforcing zero-trust at the OS level as defence in depth.

#### Scenario: Firewall configured
- **WHEN** the deployment script runs
- **THEN** UFW is configured to deny all incoming traffic
- **AND** UFW is configured to allow all outgoing traffic
- **AND** outbound HTTPS (443/tcp) and DNS (53) are explicitly allowed
- **AND** no inbound SSH rule is added automatically
- **AND** the operator is warned about SSH implications before UFW is enabled

#### Scenario: UFW not available
- **WHEN** the deployment script runs on a system without UFW
- **THEN** a warning is logged that firewall hardening was skipped
- **AND** the deployment continues without UFW configuration

### Requirement: Production Environment Configuration
The deployment MUST load all settings (application config and Cloudflare tunnel vars) from `config/.env.production`. Staging is a localhost deployment and does not use Cloudflare tunnels.

#### Scenario: Default deployment
- **WHEN** `make cf` is run
- **THEN** the script loads `config/.env.production`
- **AND** the environment file contains CLOUDFLARE_TUNNEL_TOKEN and CLOUDFLARE_TUNNEL_NAME alongside all other application settings

### Requirement: Cloud-Agnostic Deployment
The Cloudflare deployment MUST NOT assume any specific cloud provider. The script MUST work on any Linux system with apt, systemd, and outbound HTTPS connectivity.

#### Scenario: Generic Linux VM
- **WHEN** the deployment script runs on a generic Linux VM
- **THEN** no AWS, GCP, or Azure CLI commands are executed
- **AND** no cloud-provider-specific APIs are called
- **AND** the only requirements are apt package manager, systemd, and outbound HTTPS

### Requirement: Isolation from Existing Deployments
The Cloudflare deployment MUST NOT modify any files in `deploy/production/`, `deploy/staging/`, or `deploy/dev/`.

#### Scenario: Existing scripts unchanged
- **WHEN** the Cloudflare deployment is implemented
- **THEN** `deploy/production/` contains no modifications
- **AND** `deploy/staging/` contains no modifications
- **AND** `deploy/dev/` contains no modifications
- **AND** `make p`, `make s`, `make b`, `make f` continue to work as before
