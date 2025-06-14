#!/bin/bash

# Production upgrade script with minimal downtime
set -euo pipefail
trap 'echo "❌ Upgrade failed at ${BASH_SOURCE[0]}:${LINENO}"; exit 1' ERR

# Region configuration (override with AWS_REGION env var if set)
REGION="${AWS_REGION:-us-west-1}"

# AWS profile (for SSO or named credentials)
PROFILE_OPTION=""
if [ -n "$AWS_PROFILE" ]; then
  PROFILE_OPTION="--profile $AWS_PROFILE"
fi

# ---------------------------------------------------------------------
# Load environment variables early so we can use PRODUCTION_HOST if set
if [ -f "config/.env.production" ]; then
  # shellcheck disable=SC1091
  source config/.env.production
fi

if [ -z "$PRODUCTION_HOST" ]; then
  # No PRODUCTION_HOST specified – fall back to AWS discovery
  set +e
  INSTANCE_IP=$(aws ec2 describe-instances $PROFILE_OPTION --region "$REGION" \
      --filters "Name=tag:Name,Values=atlas-prod-server" "Name=instance-state-name,Values=running" \
      --query 'Reservations[0].Instances[0].PublicIpAddress' \
      --output text 2>&1)
  AWS_RC=$?
  set -e

  if [ $AWS_RC -ne 0 ]; then
    echo "ERROR: AWS CLI returned an error while trying to look up the production instance:\n$INSTANCE_IP"
    echo "\nMost common cause: credentials not available in this shell."
    echo "\nTo fix:"
    echo "  0. Find your configured profiles: aws configure list-profiles"
    echo "  1. Authenticate with AWS SSO (if you use SSO):"
    echo "  2. Export your profile for this shell:"
    echo "       export AWS_PROFILE=<your-profile-name>"
    echo "  3. (Optional) export region if different):"
    echo "       export AWS_REGION=$REGION"
    echo "  4. Re-run make up"
    exit 1
  fi

  # Trim possible quotes/newlines from INSTANCE_IP
  INSTANCE_IP=$(echo "$INSTANCE_IP" | tr -d '"')

  if [ -z "$INSTANCE_IP" ] || [ "$INSTANCE_IP" = "None" ]; then
    echo "ERROR: Could not find a running EC2 instance tagged atlas-prod in region $REGION."
    exit 1
  fi
else
  INSTANCE_IP="$PRODUCTION_HOST"
  echo "Using PRODUCTION_HOST from .env.production: $INSTANCE_IP"
fi
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

# 3. Copy environment file to new location
echo "Copying environment file..."
scp -i $SSH_KEY config/.env.production ${SSH_USER}@${INSTANCE_IP}:/tmp/.env.production

# 4. Run upgrade on remote server
echo "Running upgrade on production server..."
ssh -i $SSH_KEY ${SSH_USER}@${INSTANCE_IP} << 'ENDSSH'
# Configuration
APP_NAME="atlas"
APP_DIR="/opt/atlas"
APP_DIR_NEW="${APP_DIR}_new"
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"
GIT_BRANCH="main"

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

echo "Performing quick switch..."
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
  echo "ERROR: Gunicorn failed to start. Check journalctl -u gunicorn for details."
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
sudo systemctl restart nginx
if ! sudo systemctl is-active --quiet nginx; then
  echo "ERROR: Nginx failed to restart. Check journalctl -u nginx for details."
  exit 1
fi
echo "✅ Nginx restarted successfully"
ENDSSH

echo "✅ Upgrade complete!"
echo "Access at: https://$DOMAIN" 