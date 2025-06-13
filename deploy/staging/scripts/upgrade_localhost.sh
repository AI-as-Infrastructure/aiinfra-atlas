#!/bin/bash

# Staging LOCAL upgrade script with minimal downtime
# This script runs on the staging machine itself (no SSH)
set -e

# Configuration
APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"  # Local staging path
APP_DIR_NEW="${APP_DIR}_new"
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"
GIT_BRANCH="main"

echo "🚀 Starting LOCAL staging upgrade with minimal downtime..."

# 1. Check for environment file
if [ ! -f "config/.env.staging" ]; then
    echo "ERROR: config/.env.staging file not found!"
    echo "Please create it from config/.env.development and modify as needed."
    exit 1
fi

# 2. Extract domain from VITE_API_URL
VITE_API_URL=$(grep "^VITE_API_URL=" "config/.env.staging" | cut -d '"' -f 2)
if [ -z "$VITE_API_URL" ]; then
    echo "ERROR: VITE_API_URL variable is not set in .env.staging"
    exit 1
fi
DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||')
echo "Using domain: $DOMAIN"

# 3. Create new directory
sudo mkdir -p "$APP_DIR_NEW"
sudo chown -R "$USER:$USER" "$APP_DIR_NEW"

# 4. Clone fresh repository
cd /tmp
rm -rf "$APP_DIR_NEW" || true
git clone -b "$GIT_BRANCH" "$GITHUB_REPO" "$APP_DIR_NEW"
cd "$APP_DIR_NEW"
git lfs pull

# 5. Copy environment file
cp "$OLDPWD/config/.env.staging" "config/.env.staging"

# Update URLs in environment file
sed -i "s#VITE_API_URL=.*#VITE_API_URL=https://$DOMAIN#" config/.env.staging
sed -i "s#CORS_ORIGINS=.*#CORS_ORIGINS=https://$DOMAIN#" config/.env.staging
sed -i "s#API_BASE_URL=.*#API_BASE_URL=https://$DOMAIN/api#" config/.env.staging
sed -i "s#WS_BASE_URL=.*#WS_BASE_URL=wss://$DOMAIN/ws#" config/.env.staging

echo "✅ Environment updated"

# 6. Setup Python env
python3.10 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt gunicorn

# 7. Prepare embedding model if needed
EMBEDDING_MODEL=$(grep "^EMBEDDING_MODEL=" "config/.env.staging" | cut -d '"' -f 2)
if [ "$EMBEDDING_MODEL" = "Livingwithmachines/bert_1890_1900" ]; then
  python create/prepare_model.py
fi

# 8. Build frontend
cd frontend
npm install
npm run build
cd ..

# 9. Generate systemd service file inside new dir
cat > gunicorn.service <<EOL
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
EnvironmentFile=$APP_DIR/config/.env.staging
ExecStart=$APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# 10. Quick switch
sudo systemctl stop gunicorn || true
sudo mv "$APP_DIR" "${APP_DIR}_old_$(date +%s)" || true
sudo mv "$APP_DIR_NEW" "$APP_DIR"

sudo cp "$APP_DIR/gunicorn.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn

echo "✅ Local staging upgrade complete at https://$DOMAIN" 