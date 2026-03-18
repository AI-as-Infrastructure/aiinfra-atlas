#!/bin/bash
#=============================================================================
# ATLAS CLOUDFLARE ZERO TRUST TUNNEL DEPLOYMENT
#=============================================================================
#
# PURPOSE:
#   Deploys the ATLAS application behind a Cloudflare Zero Trust Tunnel.
#   Assumes the server is already set up with required system packages,
#   firewall, and security hardening.
#
# USAGE:
#   Run from the atlas project root on the target server:
#   make cf    # uses config/.env.production
#
# SERVER PREREQUISITES (installed/configured by the operator):
#   - Ubuntu/Debian with apt, systemd
#   - Python 3.10, python3.10-venv, python3.10-dev
#   - Redis server (running, with authentication configured)
#   - Nginx
#   - cloudflared
#   - nvm and Node.js (or script will install nvm)
#   - git-lfs, curl, build-essential, make
#   - UFW or equivalent firewall (configured by operator)
#   - Cloudflare Zero Trust tunnel created in dashboard
#   - DNS record (CNAME) pointing your domain to the tunnel
#
# ARCHITECTURE:
#   Internet -> Cloudflare Edge (TLS, WAF, DDoS) -> Zero Trust Access (SSO/MFA)
#   -> cloudflared tunnel (outbound-only) -> Nginx (127.0.0.1:80)
#   -> static files (frontend/dist) | proxy /api /ws -> Gunicorn (127.0.0.1:8000)
#
#=============================================================================

set -e

# ---- CONFIGURATION ----
APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"
DEPLOY_USER=$(whoami)

# All settings (app config + Cloudflare tunnel vars) live in config/.env.production.
APP_ENV_FILE="config/.env.production"

# ---- LOAD ENVIRONMENT ----
if [ ! -f "$APP_ENV_FILE" ]; then
    echo "ERROR: $APP_ENV_FILE not found!"
    echo "This file must contain application settings AND Cloudflare tunnel vars."
    echo "Copy config/.env.template as a starting point and set:"
    echo "  AUTH_METHOD=cloudflare"
    echo "  CLOUDFLARE_TUNNEL_TOKEN=\"your-tunnel-token\""
    echo "  CLOUDFLARE_TUNNEL_NAME=\"your-tunnel-name\""
    exit 1
fi

echo "Loading config from $APP_ENV_FILE"
set -a
source "$APP_ENV_FILE"
set +a
echo "AUTH_METHOD: $AUTH_METHOD"

# ---- VALIDATE REQUIRED VARIABLES ----
echo "Validating required environment variables..."
MISSING=""

[ -z "$CLOUDFLARE_TUNNEL_TOKEN" ] || [ "$CLOUDFLARE_TUNNEL_TOKEN" = "<DEFAULT>" ] && MISSING="$MISSING CLOUDFLARE_TUNNEL_TOKEN"
[ -z "$CLOUDFLARE_TUNNEL_NAME" ] && MISSING="$MISSING CLOUDFLARE_TUNNEL_NAME"
[ -z "$VITE_API_URL" ] && MISSING="$MISSING VITE_API_URL"
[ -z "$REDIS_URL" ] && MISSING="$MISSING REDIS_URL"
[ -z "$ENVIRONMENT" ] && MISSING="$MISSING ENVIRONMENT"

if [ -n "$MISSING" ]; then
    echo "ERROR: Missing required environment variables:$MISSING"
    echo ""
    echo "Set these in $APP_ENV_FILE (see config/.env.template for reference)"
    exit 1
fi

echo "All required variables validated"

# ---- CHECK SERVER PREREQUISITES ----
echo "Checking server prerequisites..."
PREREQ_MISSING=""

command -v python3.10 &>/dev/null || PREREQ_MISSING="$PREREQ_MISSING python3.10"
command -v redis-server &>/dev/null || PREREQ_MISSING="$PREREQ_MISSING redis-server"
command -v nginx &>/dev/null || PREREQ_MISSING="$PREREQ_MISSING nginx"
command -v cloudflared &>/dev/null || PREREQ_MISSING="$PREREQ_MISSING cloudflared"
command -v git-lfs &>/dev/null || PREREQ_MISSING="$PREREQ_MISSING git-lfs"
command -v curl &>/dev/null || PREREQ_MISSING="$PREREQ_MISSING curl"
command -v make &>/dev/null || PREREQ_MISSING="$PREREQ_MISSING make"

if [ -n "$PREREQ_MISSING" ]; then
    echo "ERROR: Missing required system packages:$PREREQ_MISSING"
    echo ""
    echo "Install them before running this script. See docs/cloudflare.md for details."
    exit 1
fi

# Check Redis is running
if ! systemctl is-active --quiet redis-server 2>/dev/null; then
    echo "ERROR: Redis is not running. Start it first: sudo systemctl start redis-server"
    exit 1
fi

echo "All prerequisites satisfied"

# Extract domain from VITE_API_URL
DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||')
echo ""
echo "=== Cloudflare Tunnel Deployment ==="
echo "  Tunnel name:  $CLOUDFLARE_TUNNEL_NAME"
echo "  Domain:       $DOMAIN"
echo "  App dir:      $APP_DIR"
echo "  User:         $DEPLOY_USER"
echo "  Environment:  $ENVIRONMENT"
echo "====================================="
echo ""

# ---- VERIFY DIRECTORY ----
if [ ! -f "config/.env.template" ]; then
    echo "ERROR: This script must be run from the atlas project root"
    exit 1
fi

CURRENT_DIR=$(pwd)
if [ "$CURRENT_DIR" != "$APP_DIR" ]; then
    echo "ERROR: This script must be run from $APP_DIR"
    echo "Current directory: $CURRENT_DIR"
    echo "Clone the repository to $APP_DIR and run from there"
    exit 1
fi

# ---- PYTHON ENVIRONMENT ----
echo "Setting up Python environment..."
python3.10 -m venv $APP_DIR/.venv
source $APP_DIR/.venv/bin/activate
pip install --upgrade pip

if [ ! -f "$APP_DIR/config/requirements.lock" ]; then
    echo "ERROR: $APP_DIR/config/requirements.lock not found. Run 'make l' to generate it."
    exit 1
fi

echo "Installing from requirements.lock..."
pip install -r $APP_DIR/config/requirements.lock

# Set up Python package structure
echo "Setting up Python package structure..."
mkdir -p $APP_DIR/backend
touch $APP_DIR/backend/__init__.py
echo "$APP_DIR" > $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth
chmod 644 $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth

# ---- NODE.JS AND FRONTEND BUILD ----
echo "Setting up Node.js environment..."
TARGET_NODE="22.14.0"
if [ -f "$APP_DIR/frontend/.nvmrc" ]; then
    TARGET_NODE=$(cat "$APP_DIR/frontend/.nvmrc" | tr -d 'v\r\n')
fi

# Install nvm if not present
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "Installing nvm..."
    # Download nvm installer to a temp file, then execute (avoids curl|bash pipe)
    NVM_INSTALLER=$(mktemp)
    curl -o "$NVM_INSTALLER" https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh
    bash "$NVM_INSTALLER"
    rm -f "$NVM_INSTALLER"
fi

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

if command -v nvm &> /dev/null; then
    nvm install $TARGET_NODE
    nvm use $TARGET_NODE
    nvm alias default $TARGET_NODE

    node_version=$(node -v)
    if [[ "$node_version" != "v$TARGET_NODE" ]]; then
        echo "ERROR: Node.js version mismatch! Found $node_version but need v$TARGET_NODE"
        exit 1
    fi
    echo "Node.js $TARGET_NODE installed and activated"
else
    echo "ERROR: nvm failed to load"
    exit 1
fi

# Check models directory
echo "Checking model directory..."
if [ ! -d "$APP_DIR/models" ] || [ -z "$(ls -A $APP_DIR/models 2>/dev/null)" ]; then
    echo "Models directory missing or empty. Generating models..."
    cd $APP_DIR
    . .venv/bin/activate
    python create/prepare_model.py
    echo "Models generated successfully"
else
    echo "Models directory found"
fi

# Check retriever
if [ ! -f "$APP_DIR/backend/retrievers/hansard_retriever.py" ]; then
    echo "Generating retriever..."
    cd $APP_DIR
    bash utils/scripts/create_retriever.sh
    echo "Retriever generated"
else
    echo "Retriever already exists"
fi

# Set up frontend environment
echo "Setting up frontend environment..."
cd $APP_DIR
if [ -f "$APP_DIR/config/generate_vue_files.sh" ]; then
    chmod +x $APP_DIR/config/generate_vue_files.sh
    $APP_DIR/config/generate_vue_files.sh
    echo "Frontend environment configured"
else
    echo "ERROR: config/generate_vue_files.sh not found"
    exit 1
fi

# Build frontend
if [ -d "$APP_DIR/frontend" ]; then
    echo "Building frontend..."
    cd $APP_DIR/frontend
    export NODE_OPTIONS="--max_old_space_size=4096"
    npm install && npm run build

    if [ -d "$APP_DIR/frontend/dist" ]; then
        echo "Frontend built successfully"
    else
        echo "ERROR: Frontend build failed"
        exit 1
    fi
else
    echo "ERROR: frontend directory not found"
    exit 1
fi

cd $APP_DIR

# ---- CLOUDFLARED CONFIGURATION ----
echo "Configuring cloudflared..."
sudo mkdir -p /etc/cloudflared

cat > /tmp/cloudflared-config.yml << EOL
# Cloudflare Tunnel configuration for ATLAS
# Tunnel name: $CLOUDFLARE_TUNNEL_NAME
# All traffic routes through a single HTTP ingress to Nginx.
# Nginx serves static files and proxies API/WS to Gunicorn.

tunnel: $CLOUDFLARE_TUNNEL_NAME
ingress:
  - service: http://localhost:80
EOL

sudo mv /tmp/cloudflared-config.yml /etc/cloudflared/config.yml
sudo chmod 644 /etc/cloudflared/config.yml
echo "cloudflared config written to /etc/cloudflared/config.yml"

# ---- NGINX CONFIGURATION ----
echo "Configuring Nginx (localhost-only reverse proxy)..."
SERVER_NAME="$DOMAIN"

# Generate config from template
sed -e "s|\$SERVER_NAME|$SERVER_NAME|g" \
    -e "s|\$APP_DIR|$APP_DIR|g" \
    deploy/cloudflare/nginx-cloudflare.conf.template > /tmp/atlas-cloudflare.conf

sudo mv /tmp/atlas-cloudflare.conf /etc/nginx/sites-available/$APP_NAME
sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/$APP_NAME

# Remove default site to avoid port conflicts
sudo rm -f /etc/nginx/sites-enabled/default

# Validate config
sudo nginx -t
echo "Nginx configured: 127.0.0.1:80 -> static files + proxy to 127.0.0.1:8000"

# ---- SYSTEMD SERVICES ----
echo "Creating systemd services..."
sudo mkdir -p /var/log/$APP_NAME

# Gunicorn service (API only -- Nginx serves static files)
cat > /tmp/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for $APP_NAME (Cloudflare Tunnel)
After=network.target redis-server.service cloudflared.service
Requires=redis-server.service cloudflared.service

[Service]
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
EnvironmentFile=$APP_DIR/$APP_ENV_FILE
ExecStart=/bin/bash -c 'source $APP_DIR/$APP_ENV_FILE && $APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w \${GUNICORN_WORKERS:-16} -b 127.0.0.1:8000 --max-requests \${GUNICORN_MAX_REQUESTS:-3000} --max-requests-jitter \${GUNICORN_MAX_REQUESTS_JITTER:-300} --timeout \${GUNICORN_TIMEOUT:-300} --keep-alive \${GUNICORN_KEEPALIVE:-30} --worker-tmp-dir /dev/shm --access-logfile /var/log/$APP_NAME/gunicorn-access.log --error-logfile /var/log/$APP_NAME/gunicorn-error.log'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

# LLM Worker service
cat > /tmp/llm-worker.service << EOL
[Unit]
Description=Atlas LLM Background Worker (Cloudflare Tunnel)
After=network.target redis-server.service
Requires=redis-server.service

[Service]
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
Environment="ENVIRONMENT=$ENVIRONMENT"
EnvironmentFile=$APP_DIR/$APP_ENV_FILE
Environment="WORKER_ID=cloudflare-worker-1"
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/backend/services/worker.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

# cloudflared service (token-based authentication)
cat > /tmp/cloudflared.service << EOL
[Unit]
Description=Cloudflare Tunnel for $APP_NAME
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/cloudflared tunnel --config /etc/cloudflared/config.yml run --token $CLOUDFLARE_TUNNEL_TOKEN
Restart=on-failure
RestartSec=5
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOL

# Install services
sudo mv /tmp/gunicorn.service /etc/systemd/system/
sudo mv /tmp/llm-worker.service /etc/systemd/system/
sudo mv /tmp/cloudflared.service /etc/systemd/system/

# ---- SET PERMISSIONS AND START SERVICES ----
echo "Setting permissions and starting services..."
sudo chown -R $DEPLOY_USER:$DEPLOY_USER $APP_DIR /var/log/$APP_NAME
sudo systemctl daemon-reload
sudo systemctl enable nginx gunicorn llm-worker cloudflared
sudo systemctl restart gunicorn
sudo systemctl restart llm-worker
sudo systemctl restart nginx
sudo systemctl restart cloudflared

# ---- PRE-FLIGHT: CLOUDFLARED CHECK ----
echo ""
echo "Verifying cloudflared tunnel is active before starting application services..."
sleep 3
if ! sudo systemctl is-active --quiet cloudflared; then
    echo "ERROR: cloudflared service failed to start. Gunicorn will not be accessible."
    echo "Check logs: journalctl -u cloudflared -n 50"
    exit 1
fi
echo "  cloudflared: running"

# ---- HEALTH CHECK ----
echo ""
echo "Checking service status..."
sleep 5

FAILED=""
for svc in redis-server nginx gunicorn llm-worker cloudflared; do
    if sudo systemctl is-active --quiet $svc; then
        echo "  $svc: running"
    else
        echo "  $svc: FAILED"
        FAILED="$FAILED $svc"
    fi
done

if [ -n "$FAILED" ]; then
    echo ""
    echo "WARNING: Some services failed to start:$FAILED"
    echo "Check logs: journalctl -u <service> -n 50"
    exit 1
fi

# ---- FIREWALL VERIFICATION ----
echo ""
echo "Checking firewall status..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | head -1)
    if echo "$UFW_STATUS" | grep -q "active"; then
        echo "  UFW: active"
        # Verify port 8000 is not exposed publicly
        if sudo ufw status | grep -q "8000.*ALLOW.*Anywhere"; then
            echo "  WARNING: Port 8000 is open in UFW. This should be localhost-only for Cloudflare deployments."
        else
            echo "  Port 8000: not exposed (correct for Cloudflare tunnel)"
        fi
    else
        echo "  WARNING: UFW is installed but not active. Enable UFW for defence-in-depth."
        echo "  Recommended: sudo ufw default deny incoming && sudo ufw default allow outgoing && sudo ufw enable"
    fi
else
    echo "  WARNING: UFW not found. Install and configure a firewall for defence-in-depth."
fi

echo ""
echo "====================================="
echo "  Deployment complete!"
echo "====================================="
echo "  Tunnel:    $CLOUDFLARE_TUNNEL_NAME"
echo "  Domain:    $DOMAIN"
echo "  Nginx:     127.0.0.1:80 (static files + proxy)"
echo "  Backend:   127.0.0.1:8000 (API only, no exposed ports)"
echo ""
echo "  Manage Zero Trust policies in the Cloudflare dashboard."
echo "  LAN fallback: http://localhost:80 (if tunnel is down)"
echo ""
echo "  Stop:   make scf"
echo "  Clean:  make dcf"
echo "====================================="
