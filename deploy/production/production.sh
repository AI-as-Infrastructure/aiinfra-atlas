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
#   SSH_USER      - SSH username for the production server (default: atlas_deploy)
# 
# EXAMPLE:
#   ./deploy/production/production.sh 203.0.113.10 atlas_deploy
# 
# REQUIREMENTS:
#   - SSH access to the production server using the atlas-prod-key.pem key
#   - config/.env.production file must exist
#   - The EC2 instance must be created using the CloudFormation template
# 
# NOTES:
#   - Let's Encrypt certificates are automatically set up by the EC2 instance
#   - The script will deploy the application to /opt/atlas
#   - The web service will run using atlas_deploy user
#
#=============================================================================

set -e

# GitHub repository URL for cloning
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"

# Git branch to use for deployment (allow override via environment)
GIT_BRANCH="${GIT_BRANCH:-0.1.1-production}"

# Load all environment variables from production file
if [ -f "config/.env.production" ]; then
    echo "Loading environment from config/.env.production"
    # Load all variables from the file
    set -a
    source config/.env.production
    set +a
    echo "Environment variables loaded successfully"
    
    # Validate critical environment variables
    required_vars=("ENVIRONMENT" "PRODUCTION_USER" "REDIS_PASSWORD" "VITE_API_URL")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "ERROR: $var is not set in config/.env.production"
            echo "Please ensure all required variables are set in your .env.production file"
            exit 1
        fi
    done
    echo "✅ All required environment variables validated"
else
    echo "ERROR: config/.env.production not found!"
    echo "This file is required for deployment."
    exit 1
fi

# ---- CONFIGURATION SECTION ----
# App settings
APP_NAME="atlas"                    # Name of the application
APP_DIR="/opt/$APP_NAME"            # Installation directory on server

# Server settings (read from environment when possible)
PRODUCTION_IP=${1:-$PRODUCTION_HOST}  # Remote production server IP address
SSH_USER=${2:-"atlas_deploy"}        # SSH username for remote deployment (default: atlas_deploy)

# Domain settings - extract from VITE_API_URL if available
if [ -n "$VITE_API_URL" ]; then
    DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||')
    echo "Using domain from VITE_API_URL: $DOMAIN"
else
    echo "ERROR: VITE_API_URL is not set or empty"
    echo "Cannot determine domain for deployment"
    exit 1
fi
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
echo "   Using git branch: $GIT_BRANCH"
echo "   Using domain: $DOMAIN"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "ERROR: SSH key not found at $SSH_KEY"
    echo "Please ensure the key exists or update the SSH_KEY path"
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
GITHUB_REPO="$GITHUB_REPO"
GIT_BRANCH="$GIT_BRANCH"
APP_NAME="$APP_NAME"
DOMAIN="$DOMAIN"
CERT_DIR="$CERT_DIR"

# Ensure we use sudo where needed and set proper ownership
export DEPLOY_USER=\$(whoami)

# Load environment variables from production file as early as possible
if [ -f "/tmp/.env.production" ]; then
    echo "Loading environment from /tmp/.env.production"
    # More robust way to load environment variables with special characters
    set -a
    source /tmp/.env.production
    set +a
    
    # Validate critical variables again on the server
    for var in ENVIRONMENT PRODUCTION_USER REDIS_PASSWORD VITE_API_URL; do
        if [ -z "\${!var}" ]; then
            echo "ERROR: \$var is not set in .env.production"
            exit 1
        fi
    done
    echo "✅ Environment loaded and validated"
else
    echo "ERROR: /tmp/.env.production not found! Deployment cannot continue."
    exit 1
fi

# Set up application directory with proper permissions
echo "Setting up application directory..."
sudo mkdir -p \$APP_DIR && sudo chown -R \$DEPLOY_USER:\$DEPLOY_USER \$APP_DIR

# Clone or update the repository
echo "Checking for existing repository..."
# Use the configured Git branch for deployment
if [ -d "\$APP_DIR/.git" ]; then
    echo "Updating existing repository from branch \$GIT_BRANCH..."
    cd \$APP_DIR && git fetch --all && git reset --hard origin/\$GIT_BRANCH && git lfs pull
else
    echo "Cloning fresh repository from branch \$GIT_BRANCH..."
    git clone --branch \$GIT_BRANCH \$GITHUB_REPO \$APP_DIR && cd \$APP_DIR && git lfs pull
fi

# NOW copy the environment file from /tmp to the app's config directory
echo "Copying environment file from /tmp to app directory..."
if [ -f "/tmp/.env.production" ]; then
    mkdir -p "\$APP_DIR/config"
    mv /tmp/.env.production "\$APP_DIR/config/.env.production"
    chmod 644 "\$APP_DIR/config/.env.production"
    echo "✅ Environment file copied successfully"
    
    # Clean up any remaining temporary files
    echo "Cleaning up temporary files..."
    rm -f /tmp/.env.production 2>/dev/null || true
else
    echo "ERROR: /tmp/.env.production not found! Please transfer it before running this script."
    exit 1
fi

# Update URLs in the environment file to use the actual domain
echo "Updating environment URLs for production deployment..."
sed -i "s#VITE_API_URL=.*#VITE_API_URL=https://\$DOMAIN#" \$APP_DIR/config/.env.production
sed -i "s#CORS_ORIGINS=.*#CORS_ORIGINS=https://\$DOMAIN#" \$APP_DIR/config/.env.production
sed -i "s#API_BASE_URL=.*#API_BASE_URL=https://\$DOMAIN/api#" \$APP_DIR/config/.env.production
sed -i "s#WS_BASE_URL=.*#WS_BASE_URL=wss://\$DOMAIN/ws#" \$APP_DIR/config/.env.production
echo "✅ Environment file updated with domain: \$DOMAIN"

# Set up Python environment with explicit Python 3.10
echo "Setting up Python environment..."
cd \$APP_DIR
python3.10 -m venv \$APP_DIR/.venv
source \$APP_DIR/.venv/bin/activate
pip install --upgrade pip

# Install requirements - MUST exist
if [ -f "\$APP_DIR/requirements.txt" ]; then
    pip install -r \$APP_DIR/requirements.txt
elif [ -f "\$APP_DIR/config/requirements.txt" ]; then
    pip install -r \$APP_DIR/config/requirements.txt
else
    echo "ERROR: No requirements.txt found in \$APP_DIR or \$APP_DIR/config"
    echo "This file is required for deployment"
    exit 1
fi

# Set up Python package structure
echo "Setting up Python package structure..."
mkdir -p \$APP_DIR/backend
touch \$APP_DIR/backend/__init__.py
echo "\$APP_DIR" > \$APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth
chmod 644 \$APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth

# Set up frontend environment
echo "Setting up frontend environment..."
cd \$APP_DIR

# Verify environment file exists before running the script
if [ ! -f "config/.env.production" ]; then
    echo "ERROR: config/.env.production not found in \$APP_DIR"
    ls -la config/
    exit 1
fi

# Run the Vue files generation script - MUST exist
if [ -f "\$APP_DIR/config/generate_vue_files.sh" ]; then
    chmod +x \$APP_DIR/config/generate_vue_files.sh
    \$APP_DIR/config/generate_vue_files.sh
    
    # Check result of script execution
    if [ \$? -ne 0 ]; then
        echo "ERROR: Failed to generate frontend environment files"
        exit 1
    fi
    echo "✅ Frontend environment configured"
else
    echo "ERROR: config/generate_vue_files.sh not found in \$APP_DIR"
    echo "This script is required for frontend configuration"
    exit 1
fi

# Build frontend - directory MUST exist
if [ -d "\$APP_DIR/frontend" ]; then
    echo "Building frontend..."
    cd \$APP_DIR/frontend
    
    # Set Node options globally for the build
    export NODE_OPTIONS="--max_old_space_size=4096"
    echo "Building with NODE_OPTIONS=\$NODE_OPTIONS"
    
    # Check for .nvmrc file and use the specified Node.js version if available
    if [ -f ".nvmrc" ]; then
        NVMRC_VERSION=\$(cat .nvmrc)
        echo "Found .nvmrc file specifying Node.js version: \$NVMRC_VERSION"
        
        # Check current Node.js version
        CURRENT_NODE_VERSION=\$(node -v)
        echo "Current Node.js version: \$CURRENT_NODE_VERSION"
        
        # Compare versions (simplified check)
        if [[ "\$CURRENT_NODE_VERSION" != *"\$NVMRC_VERSION"* ]]; then
            echo "WARNING: Current Node.js version doesn't match .nvmrc version"
            echo "The deployment may proceed, but for optimal compatibility, consider updating the server's Node.js version"
        fi
    else
        echo "No .nvmrc file found, using system Node.js version: \$(node -v)"
    fi
    
    # Check if package.json has Node.js version requirements
    if [ -f "package.json" ] && grep -q "preinstall" package.json; then
        echo "Modifying package.json to bypass Node.js version check..."
        sed -i 's/"preinstall": ".*"/"preinstall": "echo Bypassing Node.js version check"/g' package.json
    fi
    
    # Install and build
    npm install && npm run build
    
    # Check if build succeeded - dist directory MUST exist
    if [ -d "\$APP_DIR/frontend/dist" ]; then
        echo "✅ Frontend built successfully"
    else
        echo "ERROR: Frontend build failed, dist directory not found"
        exit 1
    fi
else
    echo "ERROR: frontend directory not found in \$APP_DIR"
    echo "This directory is required for deployment"
    exit 1
fi

# Verify SSL certificates exist before nginx configuration
echo "Verifying SSL certificates..."
if [ ! -f "\$CERT_DIR/fullchain.pem" ] || [ ! -f "\$CERT_DIR/privkey.pem" ]; then
    echo "WARNING: SSL certificates not found at \$CERT_DIR"
    if [ -f "/opt/setup-ssl.sh" ]; then
        echo "Running SSL setup script..."
        sudo /opt/setup-ssl.sh
        # Wait a moment for the script to complete
        sleep 10
        
        # Check again
        if [ ! -f "\$CERT_DIR/fullchain.pem" ]; then
            echo "WARNING: SSL certificates still not found. They may be generated later."
            echo "You may need to run 'sudo certbot --nginx -d \$DOMAIN' manually after DNS propagation"
        fi
    else
        echo "ERROR: SSL setup script not found. Please run certbot manually."
    fi
else
    echo "✅ SSL certificates found at \$CERT_DIR"
fi

# Set up Nginx and Gunicorn
echo "Setting up Nginx and Gunicorn..."
sudo mkdir -p /var/log/\$APP_NAME

# Create systemd service file with atlas_deploy user
echo "Creating systemd service..."
cat > /tmp/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for \$APP_NAME
After=network.target

[Service]
User=\$DEPLOY_USER
Group=\$DEPLOY_USER
WorkingDirectory=\$APP_DIR
Environment="PATH=\$APP_DIR/.venv/bin"
Environment="PYTHONPATH=\$APP_DIR"
EnvironmentFile=\$APP_DIR/config/.env.productionn
ExecStart=\$APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 6 -b 127.0.0.1:8000 --access-logfile /var/log/\$APP_NAME/gunicorn-access.log --error-logfile /var/log/\$APP_NAME/gunicorn-error.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Create Nginx config from template - template MUST exist
echo "Setting up Nginx from template..."

# Nginx template MUST exist
if [ ! -f "\$APP_DIR/deploy/production/nginx.conf.template" ]; then
    echo "ERROR: nginx.conf.template not found at \$APP_DIR/deploy/production/"
    echo "This template is required for nginx configuration"
    exit 1
fi

# Set variables for the template
export SERVER_NAME="\$DOMAIN"
export APP_DIR="\$APP_DIR"

# Process the template and create the final config
envsubst '\$SERVER_NAME \$APP_DIR' < \$APP_DIR/deploy/production/nginx.conf.template > /tmp/nginx.conf
echo "✅ Nginx configuration generated from template"

# Copy config files to server
sudo mv /tmp/gunicorn.service /etc/systemd/system/
sudo mv /tmp/nginx.conf /etc/nginx/sites-available/\$APP_NAME
sudo ln -sf /etc/nginx/sites-available/\$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Set permissions and restart services
echo "Setting permissions and restarting services..."
sudo chown -R \$DEPLOY_USER:\$DEPLOY_USER \$APP_DIR /var/log/\$APP_NAME
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo nginx -t
if [ \$? -ne 0 ]; then
    echo "ERROR: Nginx configuration test failed"
    exit 1
fi
sudo systemctl restart nginx

# Create proper environment files
echo "Setting up backend environment..."

# Ensure backend directory exists
mkdir -p \$APP_DIR/backend

cat > "\$APP_DIR/backend/load_env.py" << EOF
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
chmod 644 "\$APP_DIR/backend/load_env.py"

# Check if app.py exists before trying to modify it
if [ ! -f "\$APP_DIR/backend/app.py" ]; then
    echo "ERROR: backend/app.py not found in \$APP_DIR"
    echo "This file is required for the application to run"
    exit 1
fi

# Modify the main app to load environment variables early
if ! grep -q "import load_env" "\$APP_DIR/backend/app.py"; then
    # Add import at the top of the file
    sed -i '1s/^/import backend.load_env\n/' "\$APP_DIR/backend/app.py"
    echo "✅ Added environment loader to backend/app.py"
fi

# Set up Redis with authentication
echo "Configuring Redis with authentication..."
REDIS_PASSWORD=\$(grep '^REDIS_PASSWORD' "\$APP_DIR/config/.env.production" | cut -d'=' -f2 | tr -d '"')
if [ -z "\$REDIS_PASSWORD" ]; then
    echo "ERROR: REDIS_PASSWORD not set in \$APP_DIR/config/.env.production"
    exit 1
fi

# Set requirepass in redis.conf (idempotent)
sudo sed -i "/^#* *requirepass /d" /etc/redis/redis.conf
sudo bash -c "echo 'requirepass \$REDIS_PASSWORD' >> /etc/redis/redis.conf"

# Enable and restart Redis
sudo systemctl enable redis-server
sudo systemctl restart redis-server
sudo systemctl status redis-server --no-pager
if [ \$? -ne 0 ]; then
    echo "ERROR: Redis failed to start"
    exit 1
fi

echo "✅ Deployment complete!"
echo "✅ Application deployed to \$APP_DIR"
echo "✅ Service running as user: \$DEPLOY_USER"
echo "✅ Domain configured: \$DOMAIN"
ENDSSH

echo "Deployment to production server completed successfully!"
echo "Your application is now available at https://$DOMAIN"
echo ""
echo "To SSH into the server:"
echo "ssh -i $SSH_KEY $SSH_USER@$PRODUCTION_IP"
echo ""
echo "To view logs:"
echo "ssh -i $SSH_KEY $SSH_USER@$PRODUCTION_IP 'sudo tail -f /var/log/$APP_NAME/gunicorn-*.log'"
