#!/bin/bash
#=============================================================================
# ATLAS PRODUCTION DEPLOYMENT
#=============================================================================
# 
# PURPOSE:
#   This script deploys the application to a production EC2 instance over SSH.
#   It sets up the application with Nginx, Gunicorn, and uses Let's Encrypt SSL.
# 
# USAGE:
#   ./deploy/production/production.sh [PRODUCTION_IP] [SSH_USER]
#
# PARAMETERS:
#   PRODUCTION_IP - IP address of the production server (required)
#   SSH_USER      - SSH username for the production server (default: ubuntu)
# 
# EXAMPLE:
#   ./deploy/production/production.sh 203.0.113.10 ubuntu
# 
# REQUIREMENTS:
#   - SSH access to the production server using the atlas-prod-key.pem key
#   - config/.env.production file must exist
#   - The EC2 instance must be created using the CloudFormation template
# 
# NOTES:
#   - Let's Encrypt certificates are automatically set up by the EC2 instance
#   - The script will deploy the application to /opt/atlas
#   - The web service will run using www-data user
#
#=============================================================================

set -e

# GitHub repository URL for cloning
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"

# Git branch to use for deployment
GIT_BRANCH="0.1.1-production"

# Load all environment variables from production file
if [ -f "config/.env.production" ]; then
    echo "Loading environment from config/.env.production"
    # Load all variables from the file
    set -a
    source config/.env.production
    set +a
    echo "Environment variables loaded successfully"
fi

# ---- CONFIGURATION SECTION ----
# App settings
APP_NAME="atlas"                    # Name of the application
APP_DIR="/opt/$APP_NAME"            # Installation directory on server

# Server settings (read from environment when possible)
PRODUCTION_IP=${1:-$PRODUCTION_HOST}  # Remote production server IP address
SSH_USER=${2:-"atlas_deploy"}               # SSH username for remote deployment (default: atlas_deploy)

# Domain settings
DOMAIN="atlas-hansard.org"            # Production domain name
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"  # Where SSL certificates are stored

# SSH key settings
SSH_KEY="$HOME/atlas-prod-key-west1.pem"    # Path to the SSH key for us-west-1 region

# ---- END CONFIGURATION ----

if [ -z "$PRODUCTION_IP" ]; then
    echo "ERROR: Production IP address not provided and PRODUCTION_HOST not set in config/.env.production"
    echo "Usage: $0 [PRODUCTION_IP] [SSH_USER]"
    exit 1
fi

echo "🚀 Deploying to $SSH_USER@$PRODUCTION_IP:$APP_DIR"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "ERROR: SSH key not found at $SSH_KEY"
    echo "Please create the key pair using the create-key.sh script"
    exit 1
fi

# SSH into the server to set up the application
echo "Setting up application on the server..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@$PRODUCTION_IP "mkdir -p $APP_DIR"

# Copy the environment file to /tmp first (matching staging workflow)
echo "Copying environment file..."
scp -i $SSH_KEY config/.env.production $SSH_USER@$PRODUCTION_IP:/tmp/.env.production

# Execute remote setup commands
echo "Setting up the application on the server..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@$PRODUCTION_IP << 'ENDSSH'
# Load environment variables from production file as early as possible
if [ -f "/tmp/.env.production" ]; then
    echo "Loading environment from /tmp/.env.production"
    # More robust way to load environment variables with special characters
    set -a
    source /tmp/.env.production
    set +a
    
    # The ENVIRONMENT variable must be set in .env.production
    # No fallback - must be explicitly set
    if [ -z "$ENVIRONMENT" ]; then
        echo "ERROR: ENVIRONMENT variable is not set in .env.production"
        echo "Please add ENVIRONMENT=production to your .env.production file"
        exit 1
    else
        echo "Using ENVIRONMENT=$ENVIRONMENT from .env.production"
    fi
else
    # Fallback just in case
    echo "WARNING: /tmp/.env.production not found, setting environment manually"
    export ENVIRONMENT="production"
fi

cd /opt/atlas

# Make sure config directory exists and copy the environment file to its final location
mkdir -p /opt/atlas/config
cp /tmp/.env.production /opt/atlas/config/.env.production

# Clone or update the repository
echo "Checking for existing repository..."
# Use the configured Git branch for deployment
if [ -d "$APP_DIR/.git" ]; then
    echo "Updating existing repository from branch $GIT_BRANCH..."
    cd $APP_DIR && git fetch --all && git reset --hard origin/$GIT_BRANCH && git lfs pull
else
    echo "Cloning fresh repository from branch $GIT_BRANCH..."
    git clone --branch $GIT_BRANCH $GITHUB_REPO $APP_DIR && cd $APP_DIR && git lfs pull
fi

# Set up Python environment
echo "Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt gunicorn

# Ensure Python can find the application modules
echo "Setting up Python package structure..."
mkdir -p /opt/atlas/backend
touch /opt/atlas/backend/__init__.py
echo '/opt/atlas' > /opt/atlas/.venv/lib/python3.10/site-packages/atlas.pth
chmod 644 /opt/atlas/.venv/lib/python3.10/site-packages/atlas.pth

# Set up frontend environment
echo "Setting up frontend environment..."
cd /opt/atlas
chmod +x config/generate_vue_files.sh
./config/generate_vue_files.sh

# Build frontend
echo "Building frontend..."
cd /opt/atlas/frontend
npm install && npm run build

# Set up Nginx and Gunicorn
echo "Setting up Nginx and Gunicorn..."
sudo mkdir -p /var/log/$APP_NAME

# Create systemd service file
echo "Creating systemd service..."
cat > /tmp/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for atlas
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/atlas
Environment="PATH=/opt/atlas/.venv/bin"
Environment="PYTHONPATH=/opt/atlas"
EnvironmentFile=/opt/atlas/config/.env.production
ExecStart=/opt/atlas/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000 --access-logfile /var/log/atlas/gunicorn-access.log --error-logfile /var/log/atlas/gunicorn-error.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Create Nginx config from template
echo "Setting up Nginx from template..."

# Copy the template to the server
cp /opt/atlas/deploy/production/nginx.conf.template /tmp/nginx.conf.template

# Set variables for the template
export SERVER_NAME="atlas-hansard.org"
export APP_DIR="/opt/atlas"

# Process the template and create the final config
envsubst '\$SERVER_NAME \$APP_DIR' < /tmp/nginx.conf.template > /tmp/nginx.conf

# Copy config files to server
sudo mv /tmp/gunicorn.service /etc/systemd/system/
sudo mv /tmp/nginx.conf /etc/nginx/sites-available/atlas
sudo ln -sf /etc/nginx/sites-available/atlas /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Set permissions and restart services
echo "Setting permissions and restarting services..."
sudo chown -R www-data:www-data /opt/atlas /var/log/atlas
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo nginx -t
sudo systemctl restart nginx

# Create proper environment files
echo "Setting up backend environment..."
cat > "/opt/atlas/backend/load_env.py" << EOF
"""Load environment variables from .env.production file."""
import os
import re
from pathlib import Path

def load_dotenv(env_file):
    """Load environment variables from a file."""
    if not os.path.exists(env_file):
        print(f"Warning: {env_file} not found")
        return False
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Extract key and value with proper handling of quotes
            match = re.match(r'^([A-Za-z0-9_]+)=(?:"([^"]*)"|(.*))$', line)
            if match:
                key = match.group(1)
                value = match.group(2) if match.group(2) is not None else match.group(3)
                os.environ[key] = value
    
    return True

# Load from the production environment file
env_file = Path(__file__).parent.parent / "config" / ".env.production"
load_dotenv(str(env_file))
print(f"Loaded environment from {env_file}")
EOF

# Make sure permissions are correct
sudo chown www-data:www-data "/opt/atlas/backend/load_env.py"

# Modify the main app to load environment variables early
if ! grep -q "import load_env" "/opt/atlas/backend/app.py"; then
    # Add import at the top of the file
    sed -i '1s/^/import backend.load_env\n/' "/opt/atlas/backend/app.py"
    echo "Added environment loader to backend/app.py"
fi

# Set up Redis with authentication
echo "Configuring Redis with authentication..."
REDIS_PASSWORD=$(grep '^REDIS_PASSWORD' "/opt/atlas/config/.env.production" | cut -d'=' -f2 | tr -d '"')
if [ -z "$REDIS_PASSWORD" ]; then
    echo "ERROR: REDIS_PASSWORD not set in /opt/atlas/config/.env.production"
    exit 1
fi

# Set requirepass in redis.conf (idempotent)
sudo sed -i "/^#* *requirepass /d" /etc/redis/redis.conf
sudo bash -c "echo 'requirepass $REDIS_PASSWORD' >> /etc/redis/redis.conf"

# Enable and restart Redis
sudo systemctl enable redis-server
sudo systemctl restart redis-server
sudo systemctl status redis-server --no-pager

echo "✅ Deployment complete!"
ENDSSH

echo "Deployment to production server completed successfully!"
echo "Your application is now available at https://atlas-hansard.org"
echo ""
echo "To SSH into the server:"
echo "ssh -i $SSH_KEY $SSH_USER@$PRODUCTION_IP"
echo ""
echo "To view logs:"
echo "ssh -i $SSH_KEY $SSH_USER@$PRODUCTION_IP 'sudo tail -f /var/log/atlas/gunicorn-*.log'"
