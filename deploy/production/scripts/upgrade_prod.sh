#!/bin/bash

# Production upgrade script with minimal downtime
set -e

# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=atlas-prod" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

if [ -z "$INSTANCE_IP" ]; then
    echo "Error: Could not find production instance"
    exit 1
fi

# Configuration
APP_NAME="atlas"
APP_DIR="/home/ubuntu/atlas"
APP_DIR_NEW="${APP_DIR}_new"
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"
GIT_BRANCH="main"
SSH_KEY="$HOME/atlas-prod-key-west1.pem"

echo "🚀 Starting production upgrade with minimal downtime..."

# 1. Check for environment file
if [ ! -f "config/.env.production" ]; then
    echo "ERROR: config/.env.production file not found!"
    echo "Please create it from config/.env.development and modify as needed."
    exit 1
fi

# 2. Extract domain from VITE_API_URL
VITE_API_URL=$(grep "^VITE_API_URL=" "config/.env.production" | cut -d '"' -f 2)
if [ -z "$VITE_API_URL" ]; then
    echo "ERROR: VITE_API_URL variable is not set in .env.production"
    echo "Please add VITE_API_URL=https://your-domain to your .env.production file"
    exit 1
fi

# Extract domain from URL (remove https:// prefix if present)
DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||')
echo "Using domain from VITE_API_URL: $DOMAIN"

# 3. Copy environment file to new location
echo "Copying environment file..."
scp -i $SSH_KEY config/.env.production ubuntu@${INSTANCE_IP}:/tmp/.env.production

# 4. Run upgrade on remote server
echo "Running upgrade on production server..."
ssh -i $SSH_KEY ubuntu@${INSTANCE_IP} << 'ENDSSH'
# Configuration
APP_NAME="atlas"
APP_DIR="/home/ubuntu/atlas"
APP_DIR_NEW="${APP_DIR}_new"
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"
GIT_BRANCH="main"

echo "Setting up new application directory..."
sudo mkdir -p $APP_DIR_NEW
sudo chown -R ubuntu:ubuntu $APP_DIR_NEW

echo "Cloning fresh repository..."
git clone -b $GIT_BRANCH $GITHUB_REPO $APP_DIR_NEW
cd $APP_DIR_NEW
git lfs pull

echo "Copying environment file..."
sudo cp /tmp/.env.production $APP_DIR_NEW/config/.env.production
sudo rm /tmp/.env.production

# Update URLs in the environment file to use the actual domain
echo "Updating environment URLs for production deployment..."
sed -i 's#VITE_API_URL=.*#VITE_API_URL=https://'"$DOMAIN"'#' $APP_DIR_NEW/config/.env.production
sed -i 's#CORS_ORIGINS=.*#CORS_ORIGINS=https://'"$DOMAIN"'#' $APP_DIR_NEW/config/.env.production
sed -i 's#API_BASE_URL=.*#API_BASE_URL=https://'"$DOMAIN"'/api#' $APP_DIR_NEW/config/.env.production
sed -i 's#WS_BASE_URL=.*#WS_BASE_URL=wss://'"$DOMAIN"'/ws#' $APP_DIR_NEW/config/.env.production

echo "✅ Environment file updated with domain: $DOMAIN"

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

echo "Configuring services..."
# Create service files in new directory
cat > $APP_DIR_NEW/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=$APP_DIR_NEW
Environment="PATH=$APP_DIR_NEW/.venv/bin"
Environment="PYTHONPATH=$APP_DIR_NEW"
EnvironmentFile=$APP_DIR_NEW/config/.env.production

ExecStart=$APP_DIR_NEW/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

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
ENDSSH

echo "✅ Upgrade complete!"
echo "Access at: https://$DOMAIN" 