#!/bin/bash

# Remote staging upgrade script with minimal downtime
# Usage: upgrade_remote.sh
# Reads STAGING_HOST (and optional STAGING_USER) from config/.env.staging or current environment.
# Requires: local config/.env.staging present.

set -e

# Ensure env file exists and load it
if [ -f "config/.env.staging" ]; then
  # shellcheck disable=SC1091
  source config/.env.staging
else
  echo "ERROR: config/.env.staging file not found!"
  exit 1
fi

# Read host/user
STAGING_HOST=${STAGING_HOST}
SSH_USER=${STAGING_USER:-atlas_deploy}

if [ -z "$STAGING_HOST" ]; then
  echo "ERROR: STAGING_HOST is not set in config/.env.staging"
  exit 1
fi

echo "🚀 Starting REMOTE staging upgrade on $STAGING_HOST (user: $SSH_USER)..."

# Copy env file to remote tmp
scp -o StrictHostKeyChecking=no config/.env.staging "$SSH_USER@$STAGING_HOST:/tmp/.env.staging"

# Run remote commands via SSH
ssh -o StrictHostKeyChecking=no "$SSH_USER@$STAGING_HOST" bash -s <<'EOSSH'
set -e
APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"
APP_DIR_NEW="${APP_DIR}_new"
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"
GIT_BRANCH="main"

# Load env
if [ ! -f /tmp/.env.staging ]; then
  echo "Missing /tmp/.env.staging on remote"
  exit 1
fi
source /tmp/.env.staging

# Extract domain
if [ -z "${VITE_API_URL}" ]; then
  echo "VITE_API_URL not set in env file"
  exit 1
fi
DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||')
echo "Using domain: $DOMAIN"

# Prune old backups (keep the 2 most recent)
echo "Pruning old backups..."
sudo ls -1dt "${APP_DIR}_old_"* 2>/dev/null | tail -n +3 | xargs -r sudo rm -rf || true

# Prepare new dir
sudo rm -rf "$APP_DIR_NEW" || true
sudo mkdir -p "$APP_DIR_NEW"
sudo chown -R "$(whoami):$(whoami)" "$APP_DIR_NEW"

cd "$APP_DIR_NEW"

git clone -b "$GIT_BRANCH" "$GITHUB_REPO" .
git lfs pull

# Move env file
mv /tmp/.env.staging config/.env.staging

# -----------------------------------------------------------------
# Ensure Node version matches frontend/.nvmrc (same as deploy script)
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
  if [ -f frontend/.nvmrc ]; then
    TARGET_NODE=$(cat frontend/.nvmrc | tr -d 'v\r\n')
    nvm install "$TARGET_NODE"
    nvm use "$TARGET_NODE"
  fi
fi

# -----------------------------------------------------------------
# Generate frontend environment files
export ENVIRONMENT=staging
chmod +x config/generate_vue_files.sh
./config/generate_vue_files.sh

# Update URLs
sed -i "s#VITE_API_URL=.*#VITE_API_URL=https://$DOMAIN#" config/.env.staging
sed -i "s#CORS_ORIGINS=.*#CORS_ORIGINS=https://$DOMAIN#" config/.env.staging
sed -i "s#API_BASE_URL=.*#API_BASE_URL=https://$DOMAIN/api#" config/.env.staging
sed -i "s#WS_BASE_URL=.*#WS_BASE_URL=wss://$DOMAIN/ws#" config/.env.staging

echo "Environment file updated"

# Python env
python3.10 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt gunicorn

# Prepare embedding model if using default model
EMBEDDING_MODEL=$(grep '^EMBEDDING_MODEL=' "config/.env.staging" | cut -d '=' -f 2- | tr -d '"')
if [ "$EMBEDDING_MODEL" = "Livingwithmachines/bert_1890_1900" ]; then
  echo "Preparing default embedding model..."
  python create/prepare_model.py
else
  echo "Skipping model preparation - using custom model: $EMBEDDING_MODEL"
fi

# Build frontend
cd frontend
npm install
npm run build
cd ..

# Generate service file
cat > gunicorn.service <<EOL
[Unit]
Description=Gunicorn instance for $APP_NAME (staging)
After=network.target

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
EnvironmentFile=$APP_DIR/config/.env.staging
ExecStart=$APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Swap directories
sudo systemctl stop gunicorn || true
sudo mv "$APP_DIR" "${APP_DIR}_old_$(date +%s)" || true
sudo mv "$APP_DIR_NEW" "$APP_DIR"

sudo cp "$APP_DIR/gunicorn.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn

echo "✅ Remote staging upgrade complete: https://$DOMAIN"
EOSSH