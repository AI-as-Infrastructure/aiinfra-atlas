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

# 1. Create new directory
echo "Setting up new application directory..."
sudo mkdir -p $APP_DIR_NEW
sudo chown -R $USER:$USER $APP_DIR_NEW

# 2. Clone fresh repository
echo "Cloning fresh repository..."
git clone -b $GIT_BRANCH $GITHUB_REPO $APP_DIR_NEW
cd $APP_DIR_NEW
git lfs pull

# 3. Copy environment file
echo "Copying environment file..."
sudo cp -r "$APP_DIR/config/.env.staging" "$APP_DIR_NEW/config/.env.staging"

# 4. Set up Python environment
echo "Setting up Python environment..."
cd $APP_DIR_NEW
python3.10 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt gunicorn

# 5. Prepare embedding model if needed
echo "Checking embedding model configuration..."
EMBEDDING_MODEL=$(grep "^EMBEDDING_MODEL=" "$APP_DIR_NEW/config/.env.staging" | cut -d '"' -f 2)
if [ "$EMBEDDING_MODEL" = "Livingwithmachines/bert_1890_1900" ]; then
    echo "Preparing default embedding model..."
    python create/prepare_model.py
else
    echo "Skipping model preparation - using custom model: $EMBEDDING_MODEL"
fi

# 6. Build frontend
echo "Building frontend..."
cd $APP_DIR_NEW/frontend
npm install
npm run build
cd ..

# 7. Configure services (but don't start)
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

# 8. Quick switch
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
echo "Access at: https://localhost" 