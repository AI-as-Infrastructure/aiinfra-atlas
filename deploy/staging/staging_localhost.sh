#!/bin/bash
#=============================================================================
# ATLAS LOCALHOST STAGING DEPLOYMENT
#=============================================================================
# 
# PURPOSE:
#   This script deploys the application in "staging mode" to the local machine.
#   It's designed for testing the staging environment locally before deploying
#   to an actual staging server. This allows developers to verify staging 
#   configurations, including HTTPS, without needing access to the staging server.
# 
# USAGE:
#   ./deploy/staging/staging_localhost.sh
# 
# REQUIREMENTS:
#   - sudo privileges on local machine
#   - config/.env.staging file must exist
#   - nginx, openssl, nodejs, npm, python3
# 
# NOTES:
#   - Creates self-signed SSL certificates for localhost
#   - Uses the current user for service permissions (not www-data)
#   - Access the deployed app at https://localhost
#   - You will need to manually trust the self-signed certificate in your browser
#
#=============================================================================

set -e

# ---- CONFIGURATION SECTION ----
# App settings
APP_NAME="atlas"                         # Name of the application
APP_DIR="/opt/$APP_NAME"                 # Installation directory on server
CURRENT_USER=$(whoami)                   # Current user for file ownership
CERT_DIR="/etc/letsencrypt/live/$APP_NAME"  # Certificate location

# ---- END CONFIGURATION ----

# Local paths (don't modify)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "💻 Deploying locally to $APP_DIR as user $CURRENT_USER"

# 1. Check for environment file
if [ ! -f "$PROJECT_ROOT/config/.env.staging" ]; then
    echo "ERROR: config/.env.staging file not found!"
    echo "Please create it from config/.env.development and modify as needed."
    exit 1
fi

# Extract Python version from the environment file
PYTHON_VERSION=$(grep "^PYTHON_VERSION=" "$PROJECT_ROOT/config/.env.staging" | cut -d '"' -f 2)
if [ -z "$PYTHON_VERSION" ]; then
    echo "ERROR: PYTHON_VERSION not found in config/.env.staging"
    echo "Please ensure your environment file contains PYTHON_VERSION=\"x.y\""
    exit 1
fi
echo "Using Python version $PYTHON_VERSION from environment file"

# 2. Install required packages with specific versions
echo "Installing required packages..."
sudo apt-get update && sudo apt-get install -y python$PYTHON_VERSION python$PYTHON_VERSION-venv python$PYTHON_VERSION-dev python3-pip nginx git git-lfs gunicorn

# Fix the Node.js version handling - MUST use 22.14.0 exactly
echo "Setting up Node.js environment..."
if command -v nvm &> /dev/null; then
    # Use nvm (preferred method)
    echo "Using nvm to install Node.js 22.14.0..."
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # Load nvm
    nvm install 22.14.0
    nvm use 22.14.0
    NODE_PATH=$(which node)
    echo "Using Node.js at: $NODE_PATH"
else
    # Install system-wide from NodeSource
    echo "Installing Node.js 22.14.0 from NodeSource..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    # Check version after installation
    node_version=$(node -v)
    if [[ "$node_version" != "v22.14.0" ]]; then
        echo "ERROR: Node.js version mismatch! Found $node_version but need v22.14.0"
        echo "Try installing nvm and running this script again"
        exit 1
    fi
fi

# Verify Node.js version matches exactly
node_version=$(node -v)
if [[ "$node_version" != "v22.14.0" ]]; then
    echo "ERROR: Node.js version mismatch! Found $node_version but need v22.14.0"
    exit 1
fi
echo "Node.js v22.14.0 confirmed"

# 3. Setup application directory
echo "Setting up application directory..."
sudo mkdir -p $APP_DIR && sudo chown -R $CURRENT_USER:$CURRENT_USER $APP_DIR

# 4. Clone or update the repository
echo "Checking for existing repository..."
if [ -d "$APP_DIR/.git" ]; then
    echo "Updating existing repository..."
    cd $APP_DIR && git fetch && git reset --hard origin/0.1.0-staging && git clean -fd && git lfs pull
else
    echo "Cloning fresh repository..."
    git clone -b 0.1.0-staging https://github.com/AI-as-Infrastructure/aiinfra-atlas.git $APP_DIR && cd $APP_DIR && git lfs pull
fi

# 5. Copy environment file
echo "Copying environment file..."
sudo mkdir -p "$(dirname "$APP_DIR/config/.env.staging")"
sudo cp -r "$PROJECT_ROOT/config/.env.staging" "$APP_DIR/config/.env.staging"

# Check if environment file has correct settings for localhost deployment
if ! grep -q "VITE_API_URL=https://localhost" "$APP_DIR/config/.env.staging"; then
    echo "⚠️ WARNING: Your .env.staging file doesn't have VITE_API_URL set to https://localhost"
    echo "   This may cause frontend to API communication issues."
    echo "   Consider updating config/.env.staging with:"
    echo "   VITE_API_URL=https://localhost"
    echo "   CORS_ORIGINS=https://localhost,https://127.0.0.1"
    echo "   API_BASE_URL=https://localhost/api"
    echo "   WS_BASE_URL=wss://localhost/ws"
fi

# 6. Setup Python environment
echo "Setting up Python environment..."
cd $APP_DIR
# Use the version from environment file
python$PYTHON_VERSION -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt gunicorn

# Ensure Python can find the application modules - improved version
echo "Setting up Python path..."
# Create a proper __init__.py if it doesn't exist
sudo mkdir -p $APP_DIR/backend
if [ ! -f "$APP_DIR/backend/__init__.py" ]; then
  sudo touch "$APP_DIR/backend/__init__.py"
fi

# Create a proper .pth file for Python module path
echo "$APP_DIR" > $APP_DIR/.venv/lib/python$PYTHON_VERSION/site-packages/atlas.pth
chmod 644 $APP_DIR/.venv/lib/python$PYTHON_VERSION/site-packages/atlas.pth

# Make sure the Gunicorn service uses the correct Python version
cat > /tmp/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
# Use full path to Python executable in the venv
ExecStart=$APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000 --access-logfile ${LOGS_ABS_PATH}/gunicorn-access.log --error-logfile ${LOGS_ABS_PATH}/gunicorn-error.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Create Nginx config
echo "Creating Nginx configuration..."
cat > /tmp/nginx.conf << EOL
server {
    listen 80;
    server_name _;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name _;
    
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

    location /ws {
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

# 7. Build frontend
echo "Building frontend..."
cd $APP_DIR/frontend
npm install && npm run build

# 8. Set up Nginx and Gunicorn
echo "Setting up Nginx and Gunicorn..."
sudo mkdir -p /var/log/$APP_NAME

# Create logs directory and configure logging
echo "Setting up logging..."
mkdir -p "$PROJECT_ROOT/deploy/staging/logs"
sudo mkdir -p /var/log/$APP_NAME

# Create absolute path for log files
LOGS_ABS_PATH="$PROJECT_ROOT/deploy/staging/logs"
mkdir -p "$LOGS_ABS_PATH"

# Install config files
sudo mv /tmp/gunicorn.service /etc/systemd/system/gunicorn.service
sudo mv /tmp/nginx.conf /etc/nginx/sites-available/$APP_NAME
sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Set up certificates for localhost
echo "Setting up self-signed certificates for localhost..."
    
# Create directory for certificates
sudo mkdir -p $CERT_DIR
    
# Generate self-signed certificate if it doesn't exist
if [ ! -f "$CERT_DIR/privkey.pem" ]; then
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout $CERT_DIR/privkey.pem \
        -out $CERT_DIR/fullchain.pem \
        -subj '/CN=localhost' \
        -addext 'subjectAltName=DNS:localhost'
    
    echo "Self-signed certificate generated for localhost."
    echo "⚠️ Important: You need to manually trust this certificate in your browser or system."
else
    echo "Self-signed certificates already exist."
fi
    
# Verify certificate files exist
if [ ! -f "$CERT_DIR/fullchain.pem" ] || [ ! -f "$CERT_DIR/privkey.pem" ]; then
    echo "❌ Certificate generation failed. Please check errors above."
    exit 1
else
    echo "✅ Certificates successfully generated."
fi
    
# Set correct permissions - for local use current user owns the certificates
sudo chmod 644 $CERT_DIR/fullchain.pem 
sudo chmod 600 $CERT_DIR/privkey.pem
sudo chown $CURRENT_USER:$CURRENT_USER $CERT_DIR/fullchain.pem $CERT_DIR/privkey.pem

# Before setting permissions and restarting services
# Clean up any existing failed service
echo "Cleaning up any existing service..."
sudo systemctl stop gunicorn || true
sudo systemctl disable gunicorn || true
sudo systemctl daemon-reload

# 9. Set permissions and restart services
echo "Setting permissions and restarting services..."
sudo chown -R $CURRENT_USER:$CURRENT_USER $APP_DIR
sudo chown -R $CURRENT_USER:$CURRENT_USER /var/log/$APP_NAME
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo nginx -t
sudo systemctl restart nginx

# Add symlink from system logs to our logs directory
echo "Creating symlinks to system logs..."
sudo ln -sf /var/log/nginx/error.log "$PROJECT_ROOT/deploy/staging/logs/nginx-error.log"
sudo ln -sf /var/log/nginx/access.log "$PROJECT_ROOT/deploy/staging/logs/nginx-access.log"

# Set up backend environment
echo "Setting up backend environment..."
# Ensure the staging environment file is in place at .env.staging (NOT .env)
sudo cp "$PROJECT_ROOT/config/.env.staging" "$APP_DIR/config/.env.staging"
echo "✅ Backend environment configured to use config/.env.staging"

# Set up frontend environment using the enhanced script with environment parameter
echo "Setting up frontend environment..."
cd $APP_DIR
chmod +x config/generate_vue_files.sh
# Run the script with 'staging' parameter
./config/generate_vue_files.sh staging
echo "✅ Frontend environment configured for staging"

echo "Deployment complete!"
echo "Access at: https://localhost"
echo "Note: You may need to accept the self-signed certificate in your browser." 