#!/bin/bash
#=============================================================================
# ATLAS LOCAL PRODUCTION DEPLOYMENT
#=============================================================================
# 
# PURPOSE:
#   This script deploys the application locally on a production server.
#   It sets up the application with Nginx, Gunicorn, and uses Let's Encrypt SSL.
# 
# USAGE:
#   Run this script directly on the production server from the atlas project root:
#   ./deploy/production/production-local.sh
# 
# REQUIREMENTS:
#   - config/.env.production file must exist in the current directory
#   - Script must be run from the atlas project root directory  
#   - User must have sudo privileges
# 
# NOTES:
#   - Let's Encrypt certificates are automatically set up
#   - The script will deploy the application to /opt/atlas
#   - The web service will run using the current user
#
#=============================================================================

set -e

# GitHub repository URL for cloning
GITHUB_REPO="https://github.com/AI-as-Infrastructure/aiinfra-atlas.git"

# Git branch to use for deployment (allow override via environment)
GIT_BRANCH="${GIT_BRANCH:-main}"

# Load all environment variables from production file
if [ -f "config/.env.production" ]; then
    echo "Loading environment from config/.env.production"
    set -a
    source config/.env.production
    set +a
    echo "Environment variables loaded successfully"
    
    # Validate critical environment variables
    required_vars=("ENVIRONMENT" "VITE_API_URL")
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
APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"

# Domain settings - extract from VITE_API_URL
if [ -n "$VITE_API_URL" ]; then
    DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||')
    echo "Using domain from VITE_API_URL: $DOMAIN"
else
    echo "ERROR: VITE_API_URL is not set or empty"
    echo "Cannot determine domain for deployment"
    exit 1
fi
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"

# Set current user as deploy user
export DEPLOY_USER=$(whoami)

echo "🚀 Deploying locally to $APP_DIR"
echo "   Using git branch: $GIT_BRANCH"
echo "   Using domain: $DOMAIN"
echo "   Running as user: $DEPLOY_USER"

# Install system dependencies
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y nginx python3.10 python3.10-venv python3.10-dev git-lfs redis-server curl build-essential make

# Verify we're running from the application directory
if [ ! -f "config/.env.production" ]; then
    echo "ERROR: This script must be run from the atlas project root directory"
    echo "Expected to find config/.env.production in current directory"
    exit 1
fi

# Ensure we're in /opt/atlas
CURRENT_DIR=$(pwd)
if [ "$CURRENT_DIR" != "$APP_DIR" ]; then
    echo "ERROR: This script must be run from $APP_DIR"
    echo "Current directory: $CURRENT_DIR"
    echo "Please clone the repository to $APP_DIR and run from there"
    exit 1
fi

echo "✅ Running from correct directory: $APP_DIR"

# Update URLs in the environment file to use the actual domain
echo "Updating environment URLs for production deployment..."
sed -i "s#VITE_API_URL=.*#VITE_API_URL=https://$DOMAIN#" $APP_DIR/config/.env.production
sed -i "s#CORS_ORIGINS=.*#CORS_ORIGINS=https://$DOMAIN#" $APP_DIR/config/.env.production
sed -i "s#API_BASE_URL=.*#API_BASE_URL=https://$DOMAIN/api#" $APP_DIR/config/.env.production
sed -i "s#WS_BASE_URL=.*#WS_BASE_URL=wss://$DOMAIN/ws#" $APP_DIR/config/.env.production
echo "✅ Environment file updated with domain: $DOMAIN"

# Set up Python environment
echo "Setting up Python environment..."
cd $APP_DIR
python3.10 -m venv $APP_DIR/.venv
source $APP_DIR/.venv/bin/activate
pip install --upgrade pip
if [ ! -f "$APP_DIR/config/requirements.lock" ]; then
    echo "❌ Error: $APP_DIR/config/requirements.lock not found. Run 'make l' to generate it before deployment."
    exit 1
fi
echo "Installing from requirements.lock (locked dependencies, CPU default)..."
pip install -r $APP_DIR/config/requirements.lock

# Set up Python package structure
echo "Setting up Python package structure..."
mkdir -p $APP_DIR/backend
touch $APP_DIR/backend/__init__.py
echo "$APP_DIR" > $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth
chmod 644 $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth

# Set up Redis with authentication
echo "Configuring Redis with authentication..."
# Extract password from REDIS_URL format: redis://:password@host:port/db
REDIS_URL=$(grep "^REDIS_URL=" "$APP_DIR/config/.env.production" | cut -d '=' -f 2)
REDIS_PASSWORD=$(echo "$REDIS_URL" | sed -n 's/.*redis:\/\/:\([^@]*\)@.*/\1/p')
if [ -z "$REDIS_PASSWORD" ]; then
    echo "ERROR: Could not extract Redis password from REDIS_URL in $APP_DIR/config/.env.production"
    echo "Expected format: REDIS_URL=redis://:password@localhost:6379/1"
    exit 1
fi

# Set requirepass in redis.conf (idempotent)
sudo sed -i "/^#* *requirepass /d" /etc/redis/redis.conf
sudo bash -c "echo 'requirepass $REDIS_PASSWORD' >> /etc/redis/redis.conf"

# Enable and restart Redis
sudo systemctl enable redis-server
sudo systemctl restart redis-server

# Set up Node.js environment - exact version matching
echo "Setting up Node.js environment..."
TARGET_NODE="22.14.0"
if [ -f "$APP_DIR/frontend/.nvmrc" ]; then
    TARGET_NODE=$(cat "$APP_DIR/frontend/.nvmrc" | tr -d 'v\r\n')
fi
echo "Target Node.js version: $TARGET_NODE"

# First, remove any existing nodejs to avoid conflicts
sudo apt remove -y nodejs npm 2>/dev/null || true

# Install nvm if not present
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "Installing nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    # Source nvm immediately
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
fi

# Load nvm
echo "Loading nvm..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Verify nvm is loaded
if command -v nvm &> /dev/null; then
    echo "nvm loaded successfully"
    nvm install $TARGET_NODE
    nvm use $TARGET_NODE
    nvm alias default $TARGET_NODE
    
    # Verify exact version
    node_version=$(node -v)
    if [[ "$node_version" == "v$TARGET_NODE" ]]; then
        echo "✅ Node.js $TARGET_NODE installed and activated"
    else
        echo "ERROR: Node.js version mismatch! Found $node_version but need v$TARGET_NODE"
        exit 1
    fi
else
    echo "ERROR: nvm failed to load properly"
    exit 1
fi

# Check if models directory exists and has required models
echo "Checking model directory..."
if [ ! -d "$APP_DIR/models" ] || [ -z "$(ls -A $APP_DIR/models 2>/dev/null)" ]; then
    echo "Models directory missing or empty. Generating models..."
    cd $APP_DIR
    . .venv/bin/activate
    python utils/scripts/prepare_model.py
    echo "✅ Models generated successfully"
else
    echo "✅ Models directory found with content"
fi

# Check if retriever exists
if [ ! -f "$APP_DIR/backend/retrievers/hansard_retriever.py" ]; then
    echo "Generating retriever..."
    cd $APP_DIR
    bash utils/scripts/create_retriever.sh
    echo "✅ Retriever generated"
else
    echo "✅ Retriever already exists"
fi

# Set up frontend environment
echo "Setting up frontend environment..."
cd $APP_DIR

# Run the Vue files generation script
if [ -f "$APP_DIR/config/generate_vue_files.sh" ]; then
    chmod +x $APP_DIR/config/generate_vue_files.sh
    $APP_DIR/config/generate_vue_files.sh
    echo "✅ Frontend environment configured"
else
    echo "ERROR: config/generate_vue_files.sh not found"
    exit 1
fi

# Build frontend
if [ -d "$APP_DIR/frontend" ]; then
    echo "Building frontend..."
    cd $APP_DIR/frontend
    
    export NODE_OPTIONS="--max_old_space_size=4096"
    npm install && npm run build
    
    if [ -d "$APP_DIR/frontend/dist" ]; then
        echo "✅ Frontend built successfully"
    else
        echo "ERROR: Frontend build failed"
        exit 1
    fi
else
    echo "ERROR: frontend directory not found"
    exit 1
fi

# Set up initial HTTP-only Nginx configuration (before SSL)
echo "Setting up initial HTTP Nginx configuration..."
sudo mkdir -p /var/log/$APP_NAME

# Create initial HTTP-only nginx config for certbot
cat > /tmp/nginx.conf << EOL
server {
    listen 80;
    server_name $DOMAIN;
    
    # Let's Encrypt HTTP challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Temporary proxy to backend for initial setup
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
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
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Install initial nginx config
sudo mv /tmp/nginx.conf /etc/nginx/sites-available/$APP_NAME
sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Create web root for Let's Encrypt challenges
sudo mkdir -p /var/www/html

# Test and restart nginx
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "ERROR: Nginx configuration test failed"
    exit 1
fi
sudo systemctl restart nginx

# Now verify SSL certificates exist or set them up
echo "Verifying SSL certificates..."
if [ ! -f "$CERT_DIR/fullchain.pem" ] || [ ! -f "$CERT_DIR/privkey.pem" ]; then
    echo "SSL certificates not found. Setting up Let's Encrypt..."
    
    # Check if certbot is installed
    if ! command -v certbot >/dev/null 2>&1; then
        echo "Installing certbot..."
        sudo apt update
        sudo apt install -y certbot python3-certbot-nginx
    fi
    
    echo "Running: sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect"
    sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect
    
    if [ $? -eq 0 ]; then
        echo "✅ SSL certificates generated successfully"
    else
        echo "WARNING: Certbot failed. You may need to run 'sudo certbot --nginx -d $DOMAIN' manually after DNS propagation"
    fi
else
    echo "✅ SSL certificates found at $CERT_DIR"
fi

# Now replace with the full nginx config from template (includes SSL and static files)
echo "Setting up full Nginx configuration from template..."
if [ ! -f "$APP_DIR/deploy/production/nginx.conf.template" ]; then
    echo "ERROR: nginx.conf.template not found"
    exit 1
fi

# Set variables for the template
export SERVER_NAME="$DOMAIN"
export APP_DIR="$APP_DIR"

# Process the template and create the final config
envsubst '$SERVER_NAME $APP_DIR' < $APP_DIR/deploy/production/nginx.conf.template > /tmp/nginx_final.conf
echo "✅ Full Nginx configuration generated from template"

# Install final nginx config
sudo mv /tmp/nginx_final.conf /etc/nginx/sites-available/$APP_NAME

# Test final nginx config
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "ERROR: Final Nginx configuration test failed"
    exit 1
fi
sudo systemctl restart nginx

# Set up Gunicorn
echo "Setting up Gunicorn..."

# Create systemd service file
echo "Creating systemd service..."
cat > /tmp/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
EnvironmentFile=$APP_DIR/config/.env.production
ExecStart=/bin/bash -c 'source $APP_DIR/config/.env.production && $APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w \${GUNICORN_WORKERS:-8} -b 127.0.0.1:8000 --max-requests \${GUNICORN_MAX_REQUESTS:-3000} --max-requests-jitter \${GUNICORN_MAX_REQUESTS_JITTER:-300} --timeout \${GUNICORN_TIMEOUT:-300} --keep-alive \${GUNICORN_KEEPALIVE:-30} --worker-tmp-dir /dev/shm --access-logfile /var/log/$APP_NAME/gunicorn-access.log --error-logfile /var/log/$APP_NAME/gunicorn-error.log'
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Create LLM Worker service
echo "Creating LLM worker service..."
cat > /tmp/llm-worker.service << EOL
[Unit]
Description=Atlas LLM Background Worker
After=network.target redis-server.service
Requires=redis-server.service

[Service]
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
Environment="PYTHONPATH=$APP_DIR"
Environment="ENVIRONMENT=production"
EnvironmentFile=$APP_DIR/config/.env.production
Environment="WORKER_ID=production-worker-1"
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/backend/services/worker.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

# Copy service config files to server
sudo mv /tmp/gunicorn.service /etc/systemd/system/
sudo mv /tmp/llm-worker.service /etc/systemd/system/

# Set permissions and restart services
echo "Setting permissions and restarting services..."
sudo chown -R $DEPLOY_USER:$DEPLOY_USER $APP_DIR /var/log/$APP_NAME
sudo systemctl daemon-reload
sudo systemctl enable gunicorn llm-worker
sudo systemctl restart gunicorn llm-worker
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "ERROR: Nginx configuration test failed"
    exit 1
fi
sudo systemctl restart nginx

echo "✅ Deployment complete!"
echo "✅ Application deployed to $APP_DIR"
echo "✅ Service running as user: $DEPLOY_USER"
echo "✅ Domain configured: $DOMAIN"
echo ""
echo "Your application is now available at https://$DOMAIN"