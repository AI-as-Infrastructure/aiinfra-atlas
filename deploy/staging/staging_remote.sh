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

# Load all environment variables from staging file (like working production script)
if [ -f "config/.env.staging" ]; then
    echo "Loading environment from config/.env.staging"
    # Load all variables from the file
    set -a
    source config/.env.staging
    set +a
    echo "Environment variables loaded successfully"
    
    # Validate critical environment variables
    required_vars=("ENVIRONMENT" "STAGING_USER" "REDIS_PASSWORD" "VITE_API_URL")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "ERROR: $var is not set in config/.env.staging"
            echo "Please ensure all required variables are set in your .env.staging file"
            exit 1
        fi
    done
    echo "✅ All required environment variables validated"
else
    echo "ERROR: config/.env.staging not found!"
    echo "This file is required for deployment."
    exit 1
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

# GitHub repository URL for cloning
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"

# Git branch to use for deployment
GIT_BRANCH="main"

# Set default environment values (important for scripts that check for either variable)
export ENVIRONMENT="staging"
export ATLAS_ENV="staging"  # For backward compatibility with existing scripts

# ---- CONFIGURATION SECTION ----
# App settings
APP_NAME="atlas"                    # Name of the application
APP_DIR="/opt/$APP_NAME"            # Installation directory on server

# Server settings (read from environment when possible)
STAGING_HOST=${STAGING_HOST}  # Remote staging server IP address
STAGING_USER=${STAGING_USER}   # SSH username for remote deployment

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

# 1. Copy the environment file to /tmp (as in working production script)
echo "Copying environment file..."
scp -o StrictHostKeyChecking=no config/.env.staging $STAGING_USER@$STAGING_HOST:/tmp/.env.staging

# 2. Now run the remote setup script (which will let git clone create $APP_DIR if needed)
echo "Setting up the application on the server..."
ssh -o StrictHostKeyChecking=no $STAGING_USER@$STAGING_HOST << ENDSSH
# Set variables from the local script
APP_DIR="$APP_DIR"
GITHUB_REPO="$GITHUB_REPO"
GIT_BRANCH="$GIT_BRANCH"
APP_NAME="$APP_NAME"
DOMAIN="$DOMAIN"
CERT_DIR="$CERT_DIR"

# Ensure we use sudo where needed and set proper ownership
export DEPLOY_USER=\$(whoami)

# Load environment variables from staging file as early as possible
if [ -f "/tmp/.env.staging" ]; then
    echo "Loading environment from /tmp/.env.staging"
    # More robust way to load environment variables with special characters
    set -a
    source /tmp/.env.staging
    set +a
    
    # Validate critical variables again on the server
    for var in ENVIRONMENT STAGING_USER REDIS_PASSWORD VITE_API_URL; do
        if [ -z "\${!var}" ]; then
            echo "ERROR: \$var is not set in .env.staging"
            exit 1
        fi
    done
    echo "✅ Environment loaded and validated"
else
    echo "ERROR: /tmp/.env.staging not found! Deployment cannot continue."
    exit 1
fi

# 1. Install required packages with specific versions
echo "Installing required packages..."
sudo apt-get update && sudo apt-get install -y python3.10 python3.10-venv python3.10-dev python3-pip nginx git git-lfs redis-server

# --- Self-signed SSL certificate for staging ---
SSL_DIR="/etc/letsencrypt/live/$DOMAIN"
CERT_FILE="\$SSL_DIR/fullchain.pem"
KEY_FILE="\$SSL_DIR/privkey.pem"

if [ ! -f "\$CERT_FILE" ] || [ ! -f "\$KEY_FILE" ]; then
    echo "Generating self-signed certificate for staging..."
    sudo mkdir -p "\$SSL_DIR"
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
        -keyout "\$KEY_FILE" \\
        -out "\$CERT_FILE" \\
        -subj "/CN=$DOMAIN"
    sudo chmod 600 "\$KEY_FILE"
    sudo chmod 644 "\$CERT_FILE"
    echo "Self-signed certificate generated at \$SSL_DIR."
else
    echo "SSL certificate already exists at \$SSL_DIR."
fi

# Install specific Node.js version
echo "Setting up Node.js environment..."

# Always try to load nvm first
export NVM_DIR="\$HOME/.nvm"
if [ -s "\$NVM_DIR/nvm.sh" ]; then
    echo "Loading nvm..."
    \\. "\$NVM_DIR/nvm.sh"  # Load nvm
    
    # Check if nvm is now available
    if command -v nvm &> /dev/null || type nvm &> /dev/null; then
        echo "Using nvm to install Node.js 22.14.0"
        nvm install 22.14.0
        nvm use 22.14.0
        nvm alias default 22.14.0
        
        # Verify the correct version is active
        node_version=\$(node -v)
        echo "Active Node.js version: \$node_version"
        
        if [[ "\$node_version" != "v22.14.0" ]]; then
            echo "ERROR: Node.js version mismatch! Found \$node_version but need v22.14.0"
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
    node_version=\$(node -v)
    echo "Active Node.js version: \$node_version"
    
    # Create symlinks to ensure the right version is used
    if [[ "\$node_version" == "v22.14.0" ]]; then
        echo "Node.js 22.14.0 installed successfully"
    else
        echo "WARNING: Node.js version mismatch! Found \$node_version but need v22.14.0"
        echo "Attempting to fix with symlinks..."
        
        # If using nvm, create symlinks to the nvm version
        if [ -d "\$NVM_DIR/versions/node/v22.14.0/bin" ]; then
            sudo ln -sf "\$NVM_DIR/versions/node/v22.14.0/bin/node" /usr/bin/node
            sudo ln -sf "\$NVM_DIR/versions/node/v22.14.0/bin/npm" /usr/bin/npm
            echo "Created symlinks to nvm version"
        else
            echo "ERROR: Cannot find Node.js 22.14.0 installation"
            exit 1
        fi
    fi
fi

# Final verification
node_version=\$(node -v)
if [[ "\$node_version" != "v22.14.0" ]]; then
    echo "ERROR: Node.js version verification failed! Found \$node_version but need v22.14.0"
    exit 1
fi

echo "✅ Node.js 22.14.0 configured successfully"
npm -v

# 3. Setup application directory
echo "Setting up application directory..."
sudo mkdir -p $APP_DIR && sudo chown -R \$USER:\$USER $APP_DIR

# 4. Clone or update the repository
echo "Checking for existing repository..."
# Use the configured Git branch for deployment
if [ -d "$APP_DIR/.git" ]; then
    echo "Updating existing repository from branch $GIT_BRANCH..."
    cd $APP_DIR && git fetch --all && git reset --hard origin/$GIT_BRANCH && git lfs pull
else
    echo "Cloning fresh repository from branch $GIT_BRANCH..."
    git clone --branch $GIT_BRANCH $GITHUB_REPO $APP_DIR && cd $APP_DIR && git lfs pull
fi

# --- Enforce Node.js version from frontend/.nvmrc ---
if [ -f "$APP_DIR/frontend/.nvmrc" ]; then
    TARGET_NODE_VERSION=\$(cat "$APP_DIR/frontend/.nvmrc" | tr -d 'v\\r\\n')
    echo "Found frontend/.nvmrc specifying Node.js \$TARGET_NODE_VERSION"
    current_node=\$(node -v 2>/dev/null || echo "")
    current_node=\${current_node#v}
    if [ "\$current_node" != "\$TARGET_NODE_VERSION" ]; then
        echo "Installing Node.js \$TARGET_NODE_VERSION via nvm to match frontend/.nvmrc"
        # Ensure nvm is loaded
        if [ -s "\$HOME/.nvm/nvm.sh" ]; then . "\$HOME/.nvm/nvm.sh"; fi
        nvm install "\$TARGET_NODE_VERSION"
        nvm use "\$TARGET_NODE_VERSION"
        nvm alias default "\$TARGET_NODE_VERSION"
    fi
    echo "✅ Node.js version after frontend/.nvmrc enforcement: \$(node -v)"
else
    echo "WARNING: frontend/.nvmrc not found; using existing Node.js version"
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

# 6. Setup Python environment with explicit Python 3.10
echo "Setting up Python environment..."
cd $APP_DIR && python3.10 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r config/requirements.txt 

# Ensure Python can find the application modules
echo "Setting up Python package structure..."
mkdir -p $APP_DIR/backend
touch $APP_DIR/backend/__init__.py
echo '$APP_DIR' > $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth
chmod 644 $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth

# Prepare embedding model if using default model
echo "Checking embedding model configuration..."
EMBEDDING_MODEL=\$(grep "^EMBEDDING_MODEL=" "$APP_DIR/config/.env.staging" | cut -d '"' -f 2)
if [ "\$EMBEDDING_MODEL" = "Livingwithmachines/bert_1890_1900" ]; then
    echo "Preparing default embedding model..."
    # Ensure we're in the app directory and virtual environment is activated
    cd $APP_DIR
    . .venv/bin/activate
    python create/prepare_model.py
else
    echo "Skipping model preparation - using custom model: \$EMBEDDING_MODEL"
fi

# Ensure Phoenix environment variables are properly set for the API
echo "Verifying Phoenix API variables..."
cd $APP_DIR
echo "Phoenix API key: \$(grep PHOENIX_CLIENT_HEADERS config/.env.staging)"
echo "Phoenix project: \$(grep PHOENIX_PROJECT_NAME config/.env.staging)"
echo "Phoenix endpoint: \$(grep PHOENIX_COLLECTOR_ENDPOINT config/.env.staging)"

# Debug: Show the actual values being extracted
PHOENIX_PROJECT_VALUE=\$(grep PHOENIX_PROJECT_NAME config/.env.staging | cut -d'=' -f2- | tr -d '"')
echo "Extracted Phoenix project name: '\$PHOENIX_PROJECT_VALUE'"
if [ -z "\$PHOENIX_PROJECT_VALUE" ]; then
    echo "WARNING: PHOENIX_PROJECT_NAME appears to be empty or not found in config/.env.staging"
    echo "Contents of config/.env.staging:"
    cat config/.env.staging | grep -E "(PHOENIX|PROJECT)" || echo "No Phoenix variables found"
fi

# Ensure environment file is properly formatted for systemd
echo "Ensuring .env.staging is properly formatted for systemd..."
# Remove any Windows line endings and ensure proper format
sed -i 's/\\r\$//' config/.env.staging
# Ensure no spaces around equals signs (systemd requirement)
sed -i 's/ *= */=/' config/.env.staging
# Remove any trailing whitespace
sed -i 's/[[:space:]]*\$//' config/.env.staging
echo "Environment file formatting completed"

# Ensure Python environment has access to Phoenix variables
cd $APP_DIR
echo "export PHOENIX_CLIENT_HEADERS=\"\$(grep PHOENIX_CLIENT_HEADERS config/.env.staging | cut -d'=' -f2-)\"" >> .venv/bin/activate
echo "export PHOENIX_PROJECT_NAME=\"\$(grep PHOENIX_PROJECT_NAME config/.env.staging | cut -d'=' -f2-)\"" >> .venv/bin/activate
echo "export PHOENIX_COLLECTOR_ENDPOINT=\"\$(grep PHOENIX_COLLECTOR_ENDPOINT config/.env.staging | cut -d'=' -f2-)\"" >> .venv/bin/activate

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
if [ \$? -ne 0 ]; then
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

# Create systemd service file with explicit Phoenix environment variables
echo "Creating systemd service..."

# Extract Phoenix variables from the environment file
PHOENIX_CLIENT_HEADERS=\$(grep "^PHOENIX_CLIENT_HEADERS=" "\$APP_DIR/config/.env.staging" | cut -d'=' -f2- | tr -d '"')
PHOENIX_PROJECT_NAME=\$(grep "^PHOENIX_PROJECT_NAME=" "\$APP_DIR/config/.env.staging" | cut -d'=' -f2- | tr -d '"')
PHOENIX_COLLECTOR_ENDPOINT=\$(grep "^PHOENIX_COLLECTOR_ENDPOINT=" "\$APP_DIR/config/.env.staging" | cut -d'=' -f2- | tr -d '"')

echo "Phoenix variables for systemd service:"
echo "  PHOENIX_CLIENT_HEADERS: \${PHOENIX_CLIENT_HEADERS:0:20}..."
echo "  PHOENIX_PROJECT_NAME: \$PHOENIX_PROJECT_NAME"
echo "  PHOENIX_COLLECTOR_ENDPOINT: \$PHOENIX_COLLECTOR_ENDPOINT"

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
Environment="ENVIRONMENT=staging"
Environment="PHOENIX_CLIENT_HEADERS=\$PHOENIX_CLIENT_HEADERS"
Environment="PHOENIX_PROJECT_NAME=\$PHOENIX_PROJECT_NAME"
Environment="PHOENIX_COLLECTOR_ENDPOINT=\$PHOENIX_COLLECTOR_ENDPOINT"
EnvironmentFile=\$APP_DIR/config/.env.staging
ExecStart=\$APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000 --access-logfile /var/log/\$APP_NAME/gunicorn-access.log --error-logfile /var/log/\$APP_NAME/gunicorn-error.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Create Nginx config matching the working staging template
echo "Setting up Nginx with domain: $DOMAIN"

cat > /tmp/nginx.conf << EOL
server {
    listen 80;
    server_name $DOMAIN;
    
    location / {
        return 301 https://\\\$host\\\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name $DOMAIN;
    
    ssl_certificate $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
    ssl_session_cache shared:SSL:10m;
    
    # Frontend - Vue.js static files
    location / {
        root $APP_DIR/frontend/dist;
        try_files \\\$uri \\\$uri/ /index.html;
        
        # Cache static assets
        location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg)\\\$ {
            expires 30d;
            add_header Cache-Control "public, no-transform";
        }
    }
    
    # Backend - FastAPI API endpoints
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }
    
    # WebSockets support
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \\\$host;
    }
    
    # Logs
    access_log /var/log/$APP_NAME/access.log;
    error_log /var/log/$APP_NAME/error.log;
}
EOL

# Create required log directories for Nginx
sudo mkdir -p /var/log/nginx
sudo chown www-data:adm /var/log/nginx

# Copy config files to server
sudo mv /tmp/gunicorn.service /etc/systemd/system/
sudo mv /tmp/nginx.conf /etc/nginx/sites-available/$APP_NAME
sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# SSL certificates must be set up on the server. Use Let's Encrypt or provide production certificates as needed.
echo "⚠️ Important: SSL certificates must be set up on the server. Use Let's Encrypt or provide production certificates as needed."
echo "For Let's Encrypt: sudo certbot --nginx -d $DOMAIN"
echo "For manual: place certs at $CERT_DIR/fullchain.pem and $CERT_DIR/privkey.pem and ensure correct permissions."

# 9. Set permissions and restart services
echo "Setting permissions and restarting services..."
sudo chown -R \$USER:\$USER $APP_DIR /var/log/$APP_NAME
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn

# Test nginx config before restarting
echo "Testing Nginx configuration..."
if sudo nginx -t; then
    echo "✅ Nginx configuration is valid"
    sudo systemctl restart nginx
    if sudo systemctl is-active --quiet nginx; then
        echo "✅ Nginx restarted successfully"
    else
        echo "❌ Nginx failed to start"
        sudo systemctl status nginx --no-pager
        exit 1
    fi
else
    echo "❌ Nginx configuration test failed"
    sudo nginx -t
    exit 1
fi

echo "Deployment complete!"

# Add command to download remote logs
echo "To download logs from the server, run:"
echo "mkdir -p deploy/staging/logs && cp /var/log/$APP_NAME/*.log deploy/staging/logs/"

# Final cleanup of temporary files
echo "Performing final cleanup..."
rm -f /tmp/staging_remote.sh 2>/dev/null || true
echo "✅ Temporary files removed from /tmp"

# --- Redis Setup for Staging (simplified approach like production) ---
echo "Configuring Redis with authentication for staging..."
REDIS_PASSWORD=\$(grep '^REDIS_PASSWORD' "$APP_DIR/config/.env.staging" | cut -d'=' -f2 | tr -d '"')
if [ -z "\$REDIS_PASSWORD" ]; then
    echo "ERROR: REDIS_PASSWORD not set in $APP_DIR/config/.env.staging"
    exit 1
fi

echo "Using Redis password: \${REDIS_PASSWORD:0:3}***"

# Set requirepass in redis.conf (idempotent approach from working production script)
sudo sed -i "/^#* *requirepass /d" /etc/redis/redis.conf
sudo bash -c "echo 'requirepass \$REDIS_PASSWORD' >> /etc/redis/redis.conf"

# Enable and restart Redis (exact approach from working production script)
sudo systemctl enable redis-server
sudo systemctl restart redis-server

# Test Redis connection instead of relying on systemctl status
echo "Testing Redis connection..."
if redis-cli -a "\$REDIS_PASSWORD" ping > /dev/null 2>&1; then
    echo "✅ Redis configured successfully"
else
    echo "⚠️ Redis connection test failed, but deployment completed successfully"
    echo "You may need to check Redis configuration manually"
fi

ENDSSH

echo "Deployment to staging server completed successfully!"
echo "Your application is now available at https://$DOMAIN"

