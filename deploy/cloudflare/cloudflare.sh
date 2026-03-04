#!/bin/bash
#=============================================================================
# ATLAS CLOUDFLARE ZERO TRUST TUNNEL DEPLOYMENT
#=============================================================================
#
# PURPOSE:
#   Deploys ATLAS behind a Cloudflare Zero Trust Tunnel with no exposed ports.
#   Replaces SSL certificate management with cloudflared tunnels.
#   Nginx (localhost-only) serves static files and proxies API/WS to Gunicorn.
#
# USAGE:
#   Run from the atlas project root on the target server:
#   make cf                          # uses config/.env.cloudflare
#   make cf CLOUDFLARE_ENV=staging   # uses config/.env.cloudflare-staging
#   make cf CLOUDFLARE_ENV=production # uses config/.env.cloudflare-production
#
# PREREQUISITES:
#   - Tunnel created in Cloudflare Zero Trust dashboard
#   - Tunnel token copied to config/.env.cloudflare (CLOUDFLARE_TUNNEL_TOKEN)
#   - DNS record (CNAME) pointing your domain to the tunnel ID
#   - Ubuntu/Debian with apt, systemd, and outbound HTTPS connectivity
#   - User must have sudo privileges
#   - If you need SSH access, run 'sudo ufw allow ssh' BEFORE this script
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

# Determine which Cloudflare env file to use
CLOUDFLARE_ENV="${CLOUDFLARE_ENV:-}"
if [ -n "$CLOUDFLARE_ENV" ]; then
    CF_ENV_FILE="config/.env.cloudflare-${CLOUDFLARE_ENV}"
else
    CF_ENV_FILE="config/.env.cloudflare"
fi

# Also load the main application env file
# CLOUDFLARE_ENV maps to application ENVIRONMENT for .env loading
if [ -n "$CLOUDFLARE_ENV" ]; then
    APP_ENV_FILE="config/.env.${CLOUDFLARE_ENV}"
else
    APP_ENV_FILE="config/.env.production"
fi

# ---- LOAD CLOUDFLARE ENVIRONMENT ----
if [ ! -f "$CF_ENV_FILE" ]; then
    echo "ERROR: $CF_ENV_FILE not found!"
    echo "Create it with at minimum:"
    echo "  CLOUDFLARE_TUNNEL_TOKEN=\"your-tunnel-token\""
    echo "  CLOUDFLARE_TUNNEL_NAME=\"your-tunnel-name\""
    echo ""
    echo "See config/.env.template for reference."
    exit 1
fi

echo "Loading Cloudflare config from $CF_ENV_FILE"
set -a
source "$CF_ENV_FILE"
set +a

# ---- LOAD APPLICATION ENVIRONMENT ----
if [ ! -f "$APP_ENV_FILE" ]; then
    echo "ERROR: $APP_ENV_FILE not found!"
    echo "This file contains application settings (LLM keys, Redis, telemetry, etc.)"
    exit 1
fi

echo "Loading application config from $APP_ENV_FILE"
set -a
source "$APP_ENV_FILE"
set +a

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
    echo "Set these in $CF_ENV_FILE (Cloudflare vars) and $APP_ENV_FILE (app vars)"
    exit 1
fi

echo "All required variables validated"

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

# ---- INSTALL SYSTEM DEPENDENCIES ----
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev git-lfs redis-server nginx curl build-essential make

# ---- INSTALL CLOUDFLARED ----
echo "Installing cloudflared..."
if ! command -v cloudflared &> /dev/null; then
    # Add Cloudflare GPG key and repository
    sudo mkdir -p --mode=0755 /usr/share/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
    echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
    sudo apt update
    sudo apt install -y cloudflared
    echo "cloudflared installed successfully"
else
    echo "cloudflared already installed: $(cloudflared --version)"
fi

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

# ---- REDIS CONFIGURATION ----
echo "Configuring Redis with authentication..."
REDIS_PASSWORD=$(echo "$REDIS_URL" | sed -n 's/.*redis:\/\/:\([^@]*\)@.*/\1/p')
if [ -z "$REDIS_PASSWORD" ]; then
    echo "ERROR: Could not extract Redis password from REDIS_URL"
    echo "Expected format: REDIS_URL=redis://:password@localhost:6379/1"
    exit 1
fi

sudo sed -i "/^#* *requirepass /d" /etc/redis/redis.conf
sudo bash -c "echo 'requirepass $REDIS_PASSWORD' >> /etc/redis/redis.conf"
sudo systemctl enable redis-server
sudo systemctl restart redis-server

# ---- NODE.JS AND FRONTEND BUILD ----
echo "Setting up Node.js environment..."
TARGET_NODE="22.14.0"
if [ -f "$APP_DIR/frontend/.nvmrc" ]; then
    TARGET_NODE=$(cat "$APP_DIR/frontend/.nvmrc" | tr -d 'v\r\n')
fi

# Remove system nodejs to avoid conflicts
sudo apt remove -y nodejs npm 2>/dev/null || true

# Install nvm if not present
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "Installing nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
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
After=network.target redis-server.service
Requires=redis-server.service

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

# ---- UFW FIREWALL ----
echo ""
echo "========================================"
echo "  FIREWALL CONFIGURATION"
echo "========================================"
echo ""
echo "This script will configure UFW to deny ALL incoming connections."
echo "Only outbound traffic (HTTPS for cloudflared, DNS) will be allowed."
echo ""
echo "WARNING: If you need SSH access, ensure you have added an SSH rule"
echo "BEFORE running this script:  sudo ufw allow ssh"
echo ""

if command -v ufw &> /dev/null; then
    # Check if SSH is already allowed
    if sudo ufw status | grep -q "22/tcp.*ALLOW"; then
        echo "SSH rule detected -- SSH access will be preserved."
    else
        echo "NOTE: No SSH rule detected. SSH will be blocked after UFW is enabled."
        echo "      If you need SSH, press Ctrl+C now and run: sudo ufw allow ssh"
        echo "      Continuing in 10 seconds..."
        sleep 10
    fi

    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow out 443/tcp comment "cloudflared outbound to Cloudflare edge"
    sudo ufw allow out 53 comment "DNS resolution"
    sudo ufw --force enable
    echo "UFW configured: deny incoming, allow outgoing"
else
    echo "WARNING: UFW not found. Skipping firewall configuration."
    echo "Install UFW manually: sudo apt install ufw"
fi

# ---- SET PERMISSIONS AND START SERVICES ----
echo "Setting permissions and starting services..."
sudo chown -R $DEPLOY_USER:$DEPLOY_USER $APP_DIR /var/log/$APP_NAME
sudo systemctl daemon-reload
sudo systemctl enable redis-server nginx gunicorn llm-worker cloudflared
sudo systemctl restart redis-server
sudo systemctl restart gunicorn
sudo systemctl restart llm-worker
sudo systemctl restart nginx
sudo systemctl restart cloudflared

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

echo ""
echo "====================================="
echo "  Deployment complete!"
echo "====================================="
echo "  Tunnel:    $CLOUDFLARE_TUNNEL_NAME"
echo "  Domain:    $DOMAIN"
echo "  Nginx:     127.0.0.1:80 (static files + proxy)"
echo "  Backend:   127.0.0.1:8000 (API only, no exposed ports)"
echo "  Firewall:  UFW deny incoming, allow outgoing"
echo ""
echo "  Manage Zero Trust policies in the Cloudflare dashboard."
echo "  LAN fallback: http://localhost:80 (if tunnel is down)"
echo ""
echo "  Stop:   make scf"
echo "  Clean:  make dcf"
echo "====================================="
