#!/bin/bash
#=============================================================================
# ATLAS REMOTE STAGING DEPLOYMENT
#=============================================================================
# 
# PURPOSE:
#   This script deploys the application to a remote staging server over SSH.
#   It sets up the entire environment including Nginx, Gunicorn, and SSL.
# 
# USAGE:
#   ./deploy/staging/staging.sh [STAGING_IP] [SSH_USER] [DOMAIN]
#
# PARAMETERS:
#   STAGING_IP - IP address of the staging server (required)
#   SSH_USER   - SSH username for the staging server (default: atlas_deploy)
#   DOMAIN     - Domain name for SSL certificate 

# Load environment variables from staging file as early as possible
if [ -f "/tmp/.env.staging" ]; then
    echo "Loading environment from /tmp/.env.staging"
    # More robust way to load environment variables with special characters
    set -a
    source /tmp/.env.staging
    set +a
    
    # The ENVIRONMENT variable must be set in .env.staging
    # No fallback - must be explicitly set
    if [ -z "$ENVIRONMENT" ]; then
        echo "ERROR: ENVIRONMENT variable is not set in .env.staging"
        echo "Please add ENVIRONMENT=staging to your .env.staging file"
        exit 1
    else
        echo "Using ENVIRONMENT=$ENVIRONMENT from .env.staging"
    fi
else
    # Fallback just in case
    echo "WARNING: /tmp/.env.staging not found, setting environment manually"
    export ENVIRONMENT="staging"
fi
# 
# EXAMPLE:
#   ./deploy/staging/staging.sh 203.0.113.10 atlas_deploy staging.example.com
# 
# REQUIREMENTS:
#   - SSH access to the staging server
#   - config/.env.staging file must exist
#   - SSL certificates must be set up on the server (see notes below)
# 
# NOTES:
#   - For SSL, you need to set up certificates on the server
#   - You can use Let's Encrypt with: sudo certbot --nginx -d yourdomain.com
#   - The script will create/update the application directory at /opt/atlas
#   - The web service will run using www-data user
#
#=============================================================================

set -e

# Set default environment values (important for scripts that check for either variable)
export ENVIRONMENT="staging"
export ATLAS_ENV="staging"  # For backward compatibility with existing scripts

# Load environment variables from staging file as early as possible
if [ -f "/tmp/.env.staging" ]; then
    echo "Loading environment from /tmp/.env.staging"
    # Only set specific variables we need rather than trying to export everything
    # This avoids issues with spaces and special characters in values
    export ENVIRONMENT="staging"
    export ATLAS_ENV="staging"
    export STAGING_HOST=$(grep "^STAGING_HOST=" /tmp/.env.staging | cut -d= -f2)
    export STAGING_USER=$(grep "^STAGING_USER=" /tmp/.env.staging | cut -d= -f2)
    # Add any other specific variables needed here
fi

# ---- CONFIGURATION SECTION ----
# App settings
APP_NAME="atlas"                    # Name of the application
APP_DIR="/opt/$APP_NAME"            # Installation directory on server

# Server settings (read from environment when possible)
STAGING_HOST=${STAGING_HOST:-"192.168.20.17"}  # Remote staging server IP address
STAGING_USER=${STAGING_USER:-"atlas_deploy"}   # SSH username for remote deployment

# Domain/SSL settings
# Extract domain from VITE_API_URL - must be explicitly set
if [ -z "$VITE_API_URL" ]; then
    echo "ERROR: VITE_API_URL variable is not set in .env.staging"
    echo "Please add VITE_API_URL=https://your-domain to your .env.staging file"
    exit 1
fi

# Extract domain from URL (remove https:// prefix if present)
DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||')
echo "Using domain from VITE_API_URL: $DOMAIN"

CERT_DIR="/etc/letsencrypt/live/$DOMAIN"     # Where SSL certificates are stored

# ---- END CONFIGURATION ----

echo "🚀 Deploying to $APP_DIR"

# 1. Install required packages with specific versions
echo "Installing required packages..."
sudo apt-get update && sudo apt-get install -y python3.10 python3.10-venv python3.10-dev python3-pip nginx git git-lfs redis-server


# --- Self-signed SSL certificate for staging ---
SSL_DIR="/etc/letsencrypt/live/$DOMAIN"
CERT_FILE="$SSL_DIR/fullchain.pem"
KEY_FILE="$SSL_DIR/privkey.pem"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Generating self-signed certificate for staging..."
    sudo mkdir -p "$SSL_DIR"
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/CN=$DOMAIN"
    sudo chmod 600 "$KEY_FILE"
    sudo chmod 644 "$CERT_FILE"
    echo "Self-signed certificate generated at $SSL_DIR."
else
    echo "SSL certificate already exists at $SSL_DIR."
fi

# Install specific Node.js version
echo "Setting up Node.js environment..."

# Always try to load nvm first
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    echo "Loading nvm..."
    \. "$NVM_DIR/nvm.sh"  # Load nvm
    
    # Check if nvm is now available
    if command -v nvm &> /dev/null || type nvm &> /dev/null; then
        echo "Using nvm to install Node.js 22.14.0"
        nvm install 22.14.0
        nvm use 22.14.0
        nvm alias default 22.14.0
        
        # Verify the correct version is active
        node_version=$(node -v)
        echo "Active Node.js version: $node_version"
        
        if [[ "$node_version" != "v22.14.0" ]]; then
            echo "ERROR: Node.js version mismatch! Found $node_version but need v22.14.0"
            echo "Try installing nvm and running this script again"
            exit 1
        fi
    else
        echo "nvm command not available even though nvm.sh exists"
    fi
else
    echo "nvm not found, installing system-wide Node.js..."
    # Install system-wide from NodeSource
    echo "Installing Node.js 22.14.0 from NodeSource..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get update && sudo apt-get install -y nodejs
    
    # Verify Node.js installation
    node_version=$(node -v)
    echo "Active Node.js version: $node_version"
    
    # Create symlinks to ensure the right version is used
    if [[ "$node_version" == "v22.14.0" ]]; then
        echo "Node.js 22.14.0 installed successfully"
    else
        echo "WARNING: Node.js version mismatch! Found $node_version but need v22.14.0"
        echo "Attempting to fix with symlinks..."
        
        # If using nvm, create symlinks to the nvm version
        if [ -d "$NVM_DIR/versions/node/v22.14.0/bin" ]; then
            sudo ln -sf "$NVM_DIR/versions/node/v22.14.0/bin/node" /usr/bin/node
            sudo ln -sf "$NVM_DIR/versions/node/v22.14.0/bin/npm" /usr/bin/npm
            echo "Created symlinks to nvm version"
        else
            echo "ERROR: Cannot find Node.js 22.14.0 installation"
            exit 1
        fi
    fi
fi

# Final verification
node_version=$(node -v)
if [[ "$node_version" != "v22.14.0" ]]; then
    echo "ERROR: Node.js version verification failed! Found $node_version but need v22.14.0"
    exit 1
fi

echo "✅ Node.js 22.14.0 configured successfully"
npm -v

# 3. Setup application directory
echo "Setting up application directory..."
sudo mkdir -p $APP_DIR && sudo chown -R $USER:$USER $APP_DIR

# 4. Clone or update the repository
echo "Checking for existing repository..."
# --- Use 0.1.0-staging branch for remote production deployment ---
if [ -d "$APP_DIR/.git" ]; then
    echo "Updating existing repository..."
    cd $APP_DIR && git fetch --all && git reset --hard origin/0.1.0-staging && git lfs pull
else
    echo "Cloning fresh repository..."
    git clone --branch 0.1.0-staging https://github.com/AI-as-Infrastructure/aiinfra-atlas.git $APP_DIR && cd $APP_DIR && git lfs pull
fi

# 5. Copy the environment file from /tmp to the app's config directory
echo "Copying environment file from /tmp to app directory..."
if [ -f "/tmp/.env.staging" ]; then
    mkdir -p "$APP_DIR/config"
    mv /tmp/.env.staging "$APP_DIR/config/.env.staging"
    chmod 644 "$APP_DIR/config/.env.staging"
    echo "✅ Environment file copied successfully"
    
    # Clean up any remaining temporary files
    echo "Cleaning up temporary files..."
    rm -f /tmp/.env.staging 2>/dev/null || true
else
    echo "ERROR: /tmp/.env.staging not found! Please transfer it before running this script."
    exit 1
fi

# Ensure frontend directory is owned by atlas_deploy for build permissions
sudo chown -R atlas_deploy:atlas_deploy $APP_DIR/frontend

# Update URLs in the environment file to use the actual domain
echo "Updating environment URLs for remote deployment..."
sed -i 's#VITE_API_URL=.*#VITE_API_URL=https://'"$DOMAIN"'#' $APP_DIR/config/.env.staging
sed -i 's#CORS_ORIGINS=.*#CORS_ORIGINS=https://'"$DOMAIN"'#' $APP_DIR/config/.env.staging
sed -i 's#API_BASE_URL=.*#API_BASE_URL=https://'"$DOMAIN"'/api#' $APP_DIR/config/.env.staging
sed -i 's#WS_BASE_URL=.*#WS_BASE_URL=wss://'"$DOMAIN"'/ws#' $APP_DIR/config/.env.staging

echo "✅ Environment file updated with domain: $DOMAIN"
echo "⚠️ IMPORTANT: If you need additional environment changes, edit the file manually on the server at:"
echo "    $APP_DIR/config/.env.staging"

# 6. Setup Python environment with explicit Python 3.10
echo "Setting up Python environment..."
cd $APP_DIR && python3.10 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r config/requirements.txt gunicorn

# Ensure Python can find the application modules
echo "Setting up Python package structure..."
mkdir -p $APP_DIR/backend
touch $APP_DIR/backend/__init__.py
echo '$APP_DIR' > $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth
chmod 644 $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth

# 7. Set up environment variables and generate frontend templates
echo "Setting up frontend environment..."
cd $APP_DIR

# Verify environment file exists before running the script
if [ ! -f "config/.env.staging" ]; then
    echo "ERROR: config/.env.staging not found in $APP_DIR"
    ls -la config/
    exit 1
fi

# Ensure script is executable
chmod +x config/generate_vue_files.sh

# Run the script with environment already sourced from .env.staging
./config/generate_vue_files.sh

# Check result of script execution
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to generate frontend environment files"
    exit 1
fi

echo "✅ Frontend environment configured"

# 8. Build frontend
echo "Building frontend..."
cd $APP_DIR/frontend
npm install && npm run build

# 9. Set up Nginx and Gunicorn
echo "Setting up Nginx and Gunicorn..."
sudo mkdir -p /var/log/$APP_NAME

# Create local logs directory
mkdir -p deploy/staging/logs

# Create Gunicorn service file with logging
cat > /tmp/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
Environment="ENVIRONMENT=staging"
ExecStart=$APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000 --access-logfile /var/log/$APP_NAME/gunicorn-access.log --error-logfile /var/log/$APP_NAME/gunicorn-error.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Create Nginx config with improved security headers
# Use SERVER_NAME based on the domain extracted from VITE_API_URL
export SERVER_NAME="$DOMAIN"
echo "Setting up Nginx with SERVER_NAME=$SERVER_NAME"

cat > /tmp/nginx.conf << EOL
server {
    listen 80;
    server_name $SERVER_NAME;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $SERVER_NAME;
    
    # SSL configuration
    ssl_certificate $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options "nosniff";
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";

    location / {
        root $APP_DIR/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }

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
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Original WebSocket location (keeping for compatibility)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Copy config files to server
sudo mv /tmp/gunicorn.service /etc/systemd/system/
sudo mv /tmp/nginx.conf /etc/nginx/sites-available/$APP_NAME
sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# SSL certificates must be set up on the server. Use Let's Encrypt or provide production certificates as needed.
echo "\u26a0\ufe0f Important: SSL certificates must be set up on the server. Use Let's Encrypt or provide production certificates as needed."
echo "For Let's Encrypt: sudo certbot --nginx -d $DOMAIN"
echo "For manual: place certs at $CERT_DIR/fullchain.pem and $CERT_DIR/privkey.pem and ensure correct permissions."

# 9. Set permissions and restart services
echo "Setting permissions and restarting services..."
sudo chown -R $USER:$USER $APP_DIR /var/log/$APP_NAME
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo nginx -t
sudo systemctl restart nginx

echo "Deployment complete!"

# Add command to download remote logs
echo "To download logs from the server, run:"
echo "mkdir -p deploy/staging/logs && cp /var/log/$APP_NAME/*.log deploy/staging/logs/"

# Final cleanup of temporary files
echo "Performing final cleanup..."
rm -f /tmp/staging_remote.sh 2>/dev/null || true
echo "✅ Temporary files removed from /tmp"

# Frontend environment is already set up before the build

# Create proper environment files instead of symlinks
echo "Setting up backend environment..."
# Ensure the staging environment file is in place (don't copy to itself)
echo "Using config/.env.staging for backend configuration"

# Create an environment loader script for the backend
cat > "$APP_DIR/backend/load_env.py" << EOF
"""Load environment variables from .env.staging file."""
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

# Load from the staging environment file
env_file = Path(__file__).parent.parent / "config" / ".env.staging"
load_dotenv(str(env_file))
print(f"Loaded environment from {env_file}")
EOF

# Make sure permissions are correct
sudo chown $USER:$USER "$APP_DIR/backend/load_env.py"

# Modify the main app to load environment variables early
if ! grep -q "import load_env" "$APP_DIR/backend/app.py"; then
    # Add import at the top of the file
    sed -i '1s/^/import backend.load_env\n/' "$APP_DIR/backend/app.py"
    echo "✅ Added environment loader to backend/app.py"
fi

echo "✅ Backend environment configured to use config/.env.staging" 

# --- Redis Setup for Staging (after .env.staging is in place) ---
echo "Configuring Redis with authentication for staging..."
REDIS_PASSWORD=$(grep '^REDIS_PASSWORD' "$APP_DIR/config/.env.staging" | cut -d'=' -f2 | tr -d '"')
if [ -z "$REDIS_PASSWORD" ]; then
    echo "ERROR: REDIS_PASSWORD not set in $APP_DIR/config/.env.staging"
    exit 1
fi

# Set requirepass in redis.conf (idempotent)
sudo sed -i "/^#* *requirepass /d" /etc/redis/redis.conf
sudo bash -c "echo 'requirepass $REDIS_PASSWORD' >> /etc/redis/redis.conf"

# Enable and restart Redis
sudo systemctl enable redis-server
sudo systemctl restart redis-server
sudo systemctl status redis-server --no-pager