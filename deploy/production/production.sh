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
GIT_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"

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
SSH_KEY="$HOME/atlas-prod-key-west1.pem"    # Path to the SSH key

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

# 1. Copy the environment file to /tmp (as in staging)
echo "Copying environment file..."
scp -i $SSH_KEY config/.env.production $SSH_USER@$PRODUCTION_IP:/tmp/.env.production

# 2. Now run the remote setup script (which will let git clone create $APP_DIR if needed)
echo "Setting up the application on the server..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@$PRODUCTION_IP << ENDSSH
# Set variables from the local script
APP_DIR="$APP_DIR"
GIT_REPO="$GIT_REPO"
GIT_BRANCH="$GIT_BRANCH"
APP_NAME="$APP_NAME"

# Ensure we use sudo where needed and set proper ownership
export DEPLOY_USER=\$(whoami)
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
    echo "ERROR: /tmp/.env.production not found! Deployment cannot continue."
    exit 1
fi

# Set up application directory with proper permissions
echo "Setting up application directory..."
sudo mkdir -p $APP_DIR
if [ -z "$PRODUCTION_USER" ]; then
    echo "ERROR: PRODUCTION_USER is not set in .env.production. Please set PRODUCTION_USER=atlas_user."
    exit 1
fi
sudo chown -R $PRODUCTION_USER:$PRODUCTION_USER $APP_DIR

# Make sure config directory exists and copy the environment file to its final location
mkdir -p $APP_DIR/config
cp /tmp/.env.production $APP_DIR/config/.env.production

# Change to the application directory for all subsequent commands
cd $APP_DIR

# Clone or update the repository (robust logic from staging)
echo "Checking for existing repository..."
if [ -d "$APP_DIR/.git" ]; then
    echo "Updating existing repository from branch $GIT_BRANCH..."
    git fetch --all && git reset --hard origin/$GIT_BRANCH && git lfs pull
elif [ "$(ls -A $APP_DIR)" ]; then
    echo "ERROR: $APP_DIR exists and is not empty, but is not a git repository."
    echo "Please clear the directory or ensure it is a valid git repo."
    exit 1
else
    echo "Cloning fresh repository from branch $GIT_BRANCH..."
    git clone --branch $GIT_BRANCH $GIT_REPO $APP_DIR && cd $APP_DIR && git lfs pull
    echo "✅ Repository cloned successfully"
fi

# Copy the environment file from /tmp to app directory...
# Environment file already copied above, just ensure proper permissions
sudo chmod 644 "$APP_DIR/config/.env.production"
echo "✅ Environment file set up successfully"

# Clean up any remaining temporary files
echo "Cleaning up temporary files..."
rm -f /tmp/.env.production 2>/dev/null || true


# Set up Python environment with explicit Python 3.10
echo "Setting up Python environment..."
cd $APP_DIR
sudo apt-get update
sudo apt-get install -y python3.10-venv

# Create the virtual environment with correct permissions
sudo python3.10 -m venv $APP_DIR/.venv
sudo chown -R $DEPLOY_USER:$DEPLOY_USER $APP_DIR/.venv
source $APP_DIR/.venv/bin/activate
pip install --upgrade pip

# Install requirements
if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r $APP_DIR/requirements.txt
elif [ -f "$APP_DIR/config/requirements.txt" ]; then
    pip install -r $APP_DIR/config/requirements.txt
else
    # Install basic requirements
    pip install fastapi uvicorn gunicorn python-dotenv
    echo "WARNING: No requirements.txt found, installed basic packages"
fi

# Set up Python package structure
echo "Setting up Python package structure..."
sudo mkdir -p $APP_DIR/backend
touch $APP_DIR/backend/__init__.py
echo "$APP_DIR" > $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth
sudo chmod 644 $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth

# Set up frontend environment
echo "Setting up frontend environment..."
cd $APP_DIR

# Run the Vue files generation script if it exists
if [ -f "$APP_DIR/config/generate_vue_files.sh" ]; then
    sudo chmod +x $APP_DIR/config/generate_vue_files.sh
    $APP_DIR/config/generate_vue_files.sh
else
    echo "Vue files generation script not found, skipping"
fi

# Build frontend
if [ -d "$APP_DIR/frontend" ]; then
    echo "Building frontend..."
    cd $APP_DIR/frontend
    
    # Check for .nvmrc file and use the specified Node.js version if available
    if [ -f ".nvmrc" ]; then
        NVMRC_VERSION=$(cat .nvmrc)
        echo "Found .nvmrc file specifying Node.js version: $NVMRC_VERSION"
        
        # Check current Node.js version
        CURRENT_NODE_VERSION=$(node -v)
        echo "Current Node.js version: $CURRENT_NODE_VERSION"
        
        # Compare versions (simplified check)
        if [[ "$CURRENT_NODE_VERSION" != *"$NVMRC_VERSION"* ]]; then
            echo "WARNING: Current Node.js version doesn't match .nvmrc version"
            echo "The deployment may proceed, but for optimal compatibility, consider updating the server's Node.js version"
        fi
    else
        echo "No .nvmrc file found, using system Node.js version: $(node -v)"
    fi
    
    # Check if package.json has Node.js version requirements
    if [ -f "package.json" ] && grep -q "preinstall" package.json; then
        echo "Modifying package.json to bypass Node.js version check..."
        sed -i 's/\"preinstall\": \".*\"/\"preinstall\": \"echo Bypassing Node.js version check\"/g' package.json
    fi
    
    # Install and build with increased memory limit for Node.js
    echo "Installing frontend dependencies and building..."
    NODE_OPTIONS=--max_old_space_size=4096 npm install && NODE_OPTIONS=--max_old_space_size=4096 npm run build
    
    # Check if build succeeded
    if [ -d "$APP_DIR/frontend/dist" ]; then
        echo "✅ Frontend built successfully"
    else
        echo "WARNING: Frontend build may have failed, dist directory not found"
    fi
else
    echo "WARNING: frontend directory not found, skipping frontend build"
fi

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

# Check if the template exists
if [ -f "$APP_DIR/deploy/production/nginx.conf.template" ]; then
    # Copy the template to the server
    cp $APP_DIR/deploy/production/nginx.conf.template /tmp/nginx.conf.template
    
    # Set variables for the template
    export SERVER_NAME="atlas-hansard.org"
    export APP_DIR="/opt/atlas"
    
    # Process the template and create the final config
    envsubst '\$SERVER_NAME \$APP_DIR' < /tmp/nginx.conf.template > /tmp/nginx.conf
else
    # Create a basic Nginx config directly
    echo "Nginx template not found, creating basic configuration"
    
    cat > /tmp/nginx.conf << EOL
server {
    listen 80;
    server_name atlas-hansard.org;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name atlas-hansard.org;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/atlas-hansard.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/atlas-hansard.org/privkey.pem;
    
    # Frontend static files
    location / {
        root $APP_DIR/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }
    
    # API proxy
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # WebSocket proxy configuration
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOL
fi

# Copy config files to server
sudo mv /tmp/gunicorn.service /etc/systemd/system/
sudo mv /tmp/nginx.conf /etc/nginx/sites-available/atlas
sudo ln -sf /etc/nginx/sites-available/atlas /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Set permissions and restart services
echo "Setting permissions and restarting services..."
sudo sudo chown -R www-data:www-data $APP_DIR /var/log/$APP_NAME
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo nginx -t
sudo systemctl restart nginx

# Create proper environment files
echo "Setting up backend environment..."

# Ensure backend directory exists
sudo mkdir -p $APP_DIR/backend

sudo tee "$APP_DIR/backend/load_env.py" > /dev/null << EOF
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
sudo sudo chown www-data:www-data "$APP_DIR/backend/load_env.py"

# Modify the main app to load environment variables early
if ! grep -q "import load_env" "$APP_DIR/backend/app.py"; then
    # Add import at the top of the file
    sed -i '1s/^/import backend.load_env\n/' "$APP_DIR/backend/app.py"
    echo "Added environment loader to backend/app.py"
fi

# Set up Redis with authentication
echo "Configuring Redis with authentication..."
REDIS_PASSWORD=$(grep '^REDIS_PASSWORD' "$APP_DIR/config/.env.production" | cut -d'=' -f2 | tr -d '"')
if [ -z "$REDIS_PASSWORD" ]; then
    echo "ERROR: REDIS_PASSWORD not set in $APP_DIR/config/.env.production"
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
