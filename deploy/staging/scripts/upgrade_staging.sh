#!/bin/bash

# Staging upgrade script with minimal downtime
set -e

# Configuration
APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"  # For local staging
# APP_DIR="/home/${STAGING_USER}/atlas"  # For remote staging
APP_DIR_NEW="${APP_DIR}_new"
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"
GIT_BRANCH="main"

echo "🚀 Starting staging upgrade with minimal downtime..."

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
    echo "Please add VITE_API_URL=https://your-domain to your .env.staging file"
    exit 1
fi

# Extract domain from URL (remove https:// prefix if present)
DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||')
echo "Using domain from VITE_API_URL: $DOMAIN"

# 3. Create new directory
echo "Setting up new application directory..."
sudo mkdir -p $APP_DIR_NEW
sudo chown -R $USER:$USER $APP_DIR_NEW

# 4. Clone fresh repository
echo "Cloning fresh repository..."
git clone -b $GIT_BRANCH $GITHUB_REPO $APP_DIR_NEW
cd $APP_DIR_NEW
git lfs pull

# 5. Copy environment file
echo "Copying environment file..."
sudo cp -r "$APP_DIR/config/.env.staging" "$APP_DIR_NEW/config/.env.staging"

# Update URLs in the environment file to use the actual domain
echo "Updating environment URLs for staging deployment..."
sed -i 's#VITE_API_URL=.*#VITE_API_URL=https://'"$DOMAIN"'#' $APP_DIR_NEW/config/.env.staging
sed -i 's#CORS_ORIGINS=.*#CORS_ORIGINS=https://'"$DOMAIN"'#' $APP_DIR_NEW/config/.env.staging
sed -i 's#API_BASE_URL=.*#API_BASE_URL=https://'"$DOMAIN"'/api#' $APP_DIR_NEW/config/.env.staging
sed -i 's#WS_BASE_URL=.*#WS_BASE_URL=wss://'"$DOMAIN"'/ws#' $APP_DIR_NEW/config/.env.staging

echo "✅ Environment file updated with domain: $DOMAIN"

# 6. Set up Python environment
echo "Setting up Python environment..."
cd $APP_DIR_NEW
python3.10 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt gunicorn

# 7. Prepare embedding model if needed
echo "Checking embedding model configuration..."
EMBEDDING_MODEL=$(grep "^EMBEDDING_MODEL=" "$APP_DIR_NEW/config/.env.staging" | cut -d '"' -f 2)
if [ "$EMBEDDING_MODEL" = "Livingwithmachines/bert_1890_1900" ]; then
    echo "Preparing default embedding model..."
    python create/prepare_model.py
else
    echo "Skipping model preparation - using custom model: $EMBEDDING_MODEL"
fi

# 8. Build frontend
echo "Building frontend..."
cd $APP_DIR_NEW/frontend
npm install
npm run build
cd ..

# 9. Configure services (but don't start)
echo "Configuring services..."
# Create service files in new directory
cat > $APP_DIR_NEW/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR_NEW
Environment="PATH=$APP_DIR_NEW/.venv/bin"
Environment="PYTHONPATH=$APP_DIR_NEW"
EnvironmentFile=$APP_DIR_NEW/config/.env.staging

ExecStart=$APP_DIR_NEW/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# 10. Quick switch
echo "Performing quick switch..."
# Stop old services
sudo systemctl stop gunicorn || true
sudo systemctl stop llm-worker || true

# Move new directory to production location
sudo rm -rf $APP_DIR
sudo mv $APP_DIR_NEW $APP_DIR

# Update service files
sudo cp $APP_DIR/gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start new services
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl enable llm-worker
sudo systemctl start llm-worker

# Verify services are running
echo "Verifying services..."
sudo systemctl status gunicorn --no-pager
sudo systemctl status llm-worker --no-pager

echo "✅ Upgrade complete!"
echo "Access at: https://$DOMAIN" 