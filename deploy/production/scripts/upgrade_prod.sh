#!/bin/bash

# Production upgrade script with minimal downtime
set -euo pipefail
trap 'echo "❌ Upgrade failed at ${BASH_SOURCE[0]}:${LINENO}"; exit 1' ERR

# Direct SSH deployment – we assume PRODUCTION_HOST is defined in .env.production.
# All AWS lookup / profile logic has been removed for simplicity.

# ---------------------------------------------------------------------
# Load environment variables early so we can use PRODUCTION_HOST if set
if [ -f "config/.env.production" ]; then
  # shellcheck disable=SC1091
  source config/.env.production
fi

# Ensure PRODUCTION_HOST is provided
if [ -z "$PRODUCTION_HOST" ]; then
  echo "ERROR: PRODUCTION_HOST is not set in config/.env.production"
  exit 1
fi

INSTANCE_IP="$PRODUCTION_HOST"
echo "Using PRODUCTION_HOST from .env.production: $INSTANCE_IP"
# ---------------------------------------------------------------------

# Configuration
APP_NAME="atlas"
APP_DIR="/opt/atlas"
APP_DIR_NEW="${APP_DIR}_new"
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"
GIT_BRANCH="main"
SSH_KEY="$HOME/atlas-prod-key-west1.pem"
SSH_USER="${SSH_USER:-atlas_deploy}"

echo "🚀 Starting production upgrade with minimal downtime..."

# 1. Check for environment file
if [ ! -f "config/.env.production" ]; then
    echo "ERROR: config/.env.production file not found!"
    echo "Please create it from config/.env.development and modify as needed."
    exit 1
fi

# 2. Validate VITE_API_URL loaded from env file and derive DOMAIN
if [ -z "$VITE_API_URL" ]; then
    echo "ERROR: VITE_API_URL is not set or empty in .env.production"
    exit 1
fi

# Derive domain (strip protocol and trailing slash)
DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||; s|/$||')
echo "Using domain from VITE_API_URL: $DOMAIN"

# 3. Validate SSH connectivity and copy environment file
echo "Validating SSH connection..."
if [ ! -f "$SSH_KEY" ]; then
    echo "ERROR: SSH key not found at $SSH_KEY"
    exit 1
fi

# Test SSH connection
if ! ssh -i $SSH_KEY -o ConnectTimeout=10 -o BatchMode=yes ${SSH_USER}@${INSTANCE_IP} "echo 'SSH connection successful'"; then
    echo "ERROR: Cannot connect to ${SSH_USER}@${INSTANCE_IP} using key $SSH_KEY"
    exit 1
fi

echo "Copying environment file..."
scp -i $SSH_KEY config/.env.production ${SSH_USER}@${INSTANCE_IP}:/tmp/.env.production

# 4. Run upgrade on remote server with timeout
echo "Running upgrade on production server..."
timeout 1200 ssh -i $SSH_KEY -o ServerAliveInterval=30 -o ServerAliveCountMax=3 ${SSH_USER}@${INSTANCE_IP} << 'ENDSSH'
set -euo pipefail
trap 'echo "❌ Remote upgrade failed at line $LINENO"; exit 1' ERR

# Configuration
APP_NAME="atlas"
APP_DIR="/opt/atlas"
APP_DIR_NEW="${APP_DIR}_new"
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"
GIT_BRANCH="main"

echo "🔄 Starting remote upgrade process..."

# Pre-flight checks
echo "🔍 Running pre-flight checks..."
if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is not installed"
    exit 1
fi

if ! command -v python3.10 >/dev/null 2>&1; then
    echo "ERROR: python3.10 is not installed"
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm is not installed"
    exit 1
fi

if [ ! -f "/tmp/.env.production" ]; then
    echo "ERROR: Environment file was not copied successfully"
    exit 1
fi

echo "✅ Pre-flight checks passed"

echo "Setting up new application directory..."
sudo mkdir -p $APP_DIR_NEW
sudo chown -R $(whoami):$(whoami) $APP_DIR_NEW

echo "Cloning fresh repository..."
git clone -b $GIT_BRANCH $GITHUB_REPO $APP_DIR_NEW
cd $APP_DIR_NEW
git lfs pull

echo "Copying environment file..."
sudo cp /tmp/.env.production $APP_DIR_NEW/config/.env.production
sudo rm /tmp/.env.production
# Derive DOMAIN from env file now that it's in place
DOMAIN=$(grep '^VITE_API_URL=' $APP_DIR_NEW/config/.env.production | sed -E 's|^VITE_API_URL=https?://||; s|/$||')

# Update URLs in the environment file to use the actual domain
echo "Updating environment URLs for production deployment..."
sed -i 's#VITE_API_URL=.*#VITE_API_URL=https://'"$DOMAIN"'#' $APP_DIR_NEW/config/.env.production
sed -i 's#CORS_ORIGINS=.*#CORS_ORIGINS=https://'"$DOMAIN"'#' $APP_DIR_NEW/config/.env.production
sed -i 's#API_BASE_URL=.*#API_BASE_URL=https://'"$DOMAIN"'/api#' $APP_DIR_NEW/config/.env.production
sed -i 's#WS_BASE_URL=.*#WS_BASE_URL=wss://'"$DOMAIN"'/ws#' $APP_DIR_NEW/config/.env.production

echo "✅ Environment file updated with domain: $DOMAIN"

# -----------------------------------------------------------------
# Load environment variables so they are available for subsequent steps (e.g. Redis)
set -a
source "$APP_DIR_NEW/config/.env.production"
set +a


# -----------------------------------------------------------------
# Ensure Node.js version matches frontend/.nvmrc (same as deploy script)
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
    TARGET_NODE="22.14.0"
    if [ -f frontend/.nvmrc ]; then
        TARGET_NODE=$(cat frontend/.nvmrc | tr -d 'v\r\n')
    fi
    echo "Target Node.js version: $TARGET_NODE"
    nvm install "$TARGET_NODE"
    nvm alias default "$TARGET_NODE"
    nvm use "$TARGET_NODE"
    CURRENT_NODE=$(node -v)
    if [[ "$CURRENT_NODE" != "v$TARGET_NODE" ]]; then
        echo "ERROR: Node.js version mismatch! Found $CURRENT_NODE expected v$TARGET_NODE"
        exit 1
    fi
fi

# -----------------------------------------------------------------
# Generate frontend environment files so VITE_ variables are respected
export ENVIRONMENT=production
chmod +x config/generate_vue_files.sh
./config/generate_vue_files.sh

echo "Setting up Python environment..."
cd $APP_DIR_NEW

# Always create fresh venv to avoid disk space issues from copying
echo "📦 Creating fresh Python environment..."
python3.10 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt gunicorn

echo "Checking embedding model configuration..."
EMBEDDING_MODEL=$(grep "^EMBEDDING_MODEL=" "$APP_DIR_NEW/config/.env.production" | cut -d '"' -f 2)
if [ "$EMBEDDING_MODEL" = "Livingwithmachines/bert_1890_1900" ]; then
    echo "Preparing default embedding model..."
    python create/prepare_model.py
else
    echo "Skipping model preparation - using custom model: $EMBEDDING_MODEL"
fi

echo "Building frontend..."
cd $APP_DIR_NEW/frontend
npm install
npm run build
cd ..

# Configure Redis with authentication
echo "Configuring Redis..."
if [ -n "$REDIS_PASSWORD" ]; then
  sudo sed -i '/^#* *requirepass /d' /etc/redis/redis.conf
  sudo bash -c "echo 'requirepass $REDIS_PASSWORD' >> /etc/redis/redis.conf"
  sudo systemctl enable redis-server
  sudo systemctl restart redis-server
  if ! sudo systemctl is-active --quiet redis-server; then
    echo "ERROR: Redis failed to start"
    exit 1
  fi
  echo "✅ Redis configured and running"
else
  echo "WARNING: REDIS_PASSWORD not set, skipping Redis authentication setup"
fi

echo "Configuring services..."
# Create service files in new directory
cat > $APP_DIR_NEW/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
EnvironmentFile=$APP_DIR/config/.env.production

ExecStart=$APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

echo "Pruning old backups (keeping only 1)..."
sudo ls -1dt "${APP_DIR}_old_"* 2>/dev/null | tail -n +2 | xargs -r sudo rm -rf || true

# Perform quick switch..."
# Stop old services
sudo systemctl stop gunicorn || true
# wait up to 15s for full shutdown
for i in {1..15}; do
  sudo systemctl is-active --quiet gunicorn || break
  sleep 1
done
sudo systemctl reset-failed gunicorn || true
pkill -u "$(whoami)" -f 'gunicorn.*backend.app' || true

# Move new directory to production location
sudo mv "$APP_DIR" "${APP_DIR}_old_$(date +%s)" || true
sudo mv "$APP_DIR_NEW" "$APP_DIR"

# Update service files
sudo cp $APP_DIR/gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload

# Ensure Gunicorn executable exists before starting
if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
  echo "ERROR: $APP_DIR/.venv/bin/python not found. Aborting upgrade."
  exit 1
fi

# Optional short wait to ensure FS sync
sleep 2

# Start Gunicorn service
sudo systemctl enable gunicorn
sudo systemctl start gunicorn

# Verify service is running
echo "Verifying Gunicorn service..."
if ! sudo systemctl is-active --quiet gunicorn; then
  echo "❌ ERROR: Gunicorn failed to start"
  echo "🔄 Attempting rollback..."
  
  # Find the most recent backup
  LATEST_BACKUP=$(ls -1dt "${APP_DIR}_old_"* 2>/dev/null | head -n 1)
  if [ -n "$LATEST_BACKUP" ]; then
    echo "Rolling back to: $LATEST_BACKUP"
    sudo systemctl stop gunicorn || true
    sudo mv "$APP_DIR" "${APP_DIR}_failed_$(date +%s)"
    sudo mv "$LATEST_BACKUP" "$APP_DIR"
    sudo systemctl start gunicorn
    
    if sudo systemctl is-active --quiet gunicorn; then
      echo "✅ Rollback successful - service restored"
    else
      echo "❌ Rollback failed - manual intervention required"
    fi
  else
    echo "❌ No backup found for rollback"
  fi
  
  echo "Check logs: journalctl -u gunicorn -n 50"
  exit 1
fi
echo "✅ Gunicorn is running"

# Restart Nginx to clear WebSocket connection state and pick up any changes
echo "Validating Nginx configuration..."
sudo nginx -t
if [ $? -ne 0 ]; then
  echo "ERROR: nginx configuration test failed"
  exit 1
fi

echo "Restarting Nginx for WebSocket connections..."

# Check if nginx is currently running
if sudo systemctl is-active --quiet nginx; then
  echo "Nginx is running, performing graceful restart..."
  # Try reload first (safer than restart)
  if sudo systemctl reload nginx; then
    echo "✅ Nginx reloaded successfully"
  else
    echo "Reload failed, attempting full restart..."
    sudo systemctl stop nginx
    sleep 2
    sudo systemctl start nginx
  fi
else
  echo "Nginx is not running, starting service..."
  sudo systemctl start nginx
fi

# Verify nginx is running
if ! sudo systemctl is-active --quiet nginx; then
  echo "❌ ERROR: Nginx failed to start/restart"
  echo ""
  echo "=== Nginx Status ==="
  sudo systemctl status nginx --no-pager -l
  echo ""
  echo "=== Recent Nginx Logs ==="
  sudo journalctl -u nginx -n 30 --no-pager
  echo ""
  echo "=== Port Usage ==="
  sudo netstat -tlnp | grep :80
  sudo netstat -tlnp | grep :443
  echo ""
  echo "=== Nginx Config Test ==="
  sudo nginx -t
  echo ""
  echo "=== Disk Space ==="
  df -h /
  echo ""
  echo "=== Nginx Process Check ==="
  ps aux | grep nginx
  exit 1
fi

echo "✅ Nginx is running successfully"
ENDSSH

echo "✅ Upgrade complete!"
echo "Access at: https://$DOMAIN" 