# cloudflare-deployment Specification

## Purpose
TBD - created by archiving change add-cloudflare-tunnel-deployment. Update Purpose after archive.
## Requirements
### Requirement: Cloudflare Tunnel Deployment Script
The system MUST provide a deployment script that installs and configures ATLAS behind a Cloudflare Zero Trust Tunnel with no publicly exposed ports.

#### Scenario: Successful deployment
- **WHEN** `make cf` is run with a valid environment file (e.g. `config/.env.production`) containing CLOUDFLARE_TUNNEL_TOKEN and CLOUDFLARE_TUNNEL_NAME
- **THEN** the script installs system dependencies (Python, Redis, Nginx, cloudflared)
- **AND** creates a Python virtual environment with locked dependencies
- **AND** builds the Vue.js frontend
- **AND** configures Redis with authentication
- **AND** deploys the Nginx reverse proxy configuration (localhost-only)
- **AND** creates systemd services for Nginx, Gunicorn, LLM worker, and cloudflared
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

### Requirement: SSH Tunnel Route Access Control
Every tunnel public hostname route that forwards to an SSH service MUST be covered
by a Cloudflare Access application for that exact hostname. A deployment with an
SSH route and no corresponding Access application MUST be treated as
misconfigured, because the route is a path through Cloudflare's edge to the host's
SSH port and neither the tunnel's outbound-only connection nor a deny-all UFW
policy restricts who may traverse it.

#### Scenario: SSH route without an Access application
- **GIVEN** a tunnel route of the form `ssh://localhost:22`
- **WHEN** no Access application covers that hostname
- **THEN** the deployment SHALL be considered misconfigured
- **AND** the hostname SHALL be reachable by any client that knows it, with the
  host's own sshd configuration as the only remaining control

#### Scenario: Operator verifies Access coverage
- **WHEN** an operator checks whether an SSH hostname is protected
- **THEN** a protected hostname SHALL be distinguishable from an unprotected one by
  a check whose result does not depend on the application's type: a request to
  `https://<hostname>/.well-known/cloudflare-access-protected-resource/` returns
  `200` when an Access application covers the hostname and `404` when none does
- **AND** `cloudflared access login <url>` SHALL resolve the Access application for
  a protected hostname — including a TCP/SSH route — and SHALL report that no
  Access application was found for an unprotected one
- **AND** a check resting solely on whether an unauthenticated request is
  redirected to the Access login endpoint SHALL NOT be treated as sufficient,
  because that behaviour varies by application type

#### Scenario: Redirect-based verification applied to an SSH route
- **GIVEN** an SSH route covered by an Access application, with browser rendering
  disabled
- **WHEN** an unauthenticated HTTP request is made to that hostname
- **THEN** the response SHALL be `403` with no redirect, rather than the `302` to
  the Access login endpoint that an HTTP-type application returns
- **AND** a verification procedure treating "no redirect" as "not protected" SHALL
  therefore report a false negative on a correctly protected SSH route
- **AND** such a procedure SHALL NOT be relied on as the sole evidence of coverage

### Requirement: Independent Access Control Per SSH Route
Each SSH route MUST be an independent unit of access control: its own Access
application, its own policy, and its own service token. No Access application,
policy, or credential SHALL be shared between two SSH routes, so that revoking,
rotating or misconfiguring the credentials of one route cannot affect access to
another.

#### Scenario: Credential revoked on one route
- **GIVEN** two hosts each reachable through their own SSH route
- **WHEN** the service token for one route is revoked or rotated
- **THEN** access to the other route SHALL be unaffected

#### Scenario: Policy change on one route
- **GIVEN** two hosts each reachable through their own SSH route
- **WHEN** the Access policy for one route is changed or its application deleted
- **THEN** the other route's policy SHALL remain in force and independently
  verifiable

### Requirement: Service Token Authentication For Unattended Forwards
An unattended local forward (`cloudflared access tcp`) used by a native SSH client
MUST authenticate with an Access service token, supplied as
`TUNNEL_SERVICE_TOKEN_ID` and `TUNNEL_SERVICE_TOKEN_SECRET` or the equivalent
flags. It MUST NOT depend on an interactive `cloudflared access login` token,
because a background or hidden forward cannot prompt for re-authentication when
that token expires with the application's session duration.

#### Scenario: Forward runs unattended across a session expiry
- **GIVEN** a forward configured with a service token
- **WHEN** the Access application's session duration elapses
- **THEN** the forward SHALL continue to authenticate without operator interaction

#### Scenario: Forward started without a token against a protected route
- **GIVEN** an SSH route covered by an Access application
- **WHEN** a forward is started with no service token
- **THEN** the forward SHALL fail rather than serve an unauthenticated listener
- **AND** the failure SHALL be recorded where an operator can read it, rather than
  surfacing only as a connection refused at the SSH client

### Requirement: Accurate Edge Security Documentation
Deployment documentation MUST NOT describe the SSH Access application as optional,
and MUST distinguish between having no inbound listening ports and being
authenticated at Cloudflare's edge. Documentation describing an SSH route MUST
state which client flows it serves, and MUST NOT imply browser rendering is
enabled when it is a separate setting.

#### Scenario: Reader follows the deployment checklist completely
- **WHEN** an operator completes every checklist step in the deployment guide
- **THEN** no SSH route SHALL be left without an Access application

#### Scenario: Reader consults the security notes
- **WHEN** an operator reads the security notes to establish the deployment's posture
- **THEN** the notes SHALL state that Zero Trust policies apply only to hostnames
  covered by an Access application
- **AND** SHALL NOT imply that the absence of inbound ports authenticates SSH

#### Scenario: Documentation describes how to verify coverage
- **WHEN** deployment documentation gives a procedure for verifying that an SSH
  hostname is protected
- **THEN** the procedure SHALL work for a TCP/SSH route and not only for an
  HTTP-type application
- **AND** it SHALL NOT present a redirect-only check as sufficient for an SSH route
