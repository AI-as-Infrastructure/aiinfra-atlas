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
#   SSH_USER   - SSH username for the staging server (default: ubuntu)
#   DOMAIN     - Domain name for SSL certificate (default: staging.example.com)
# 
# EXAMPLE:
#   ./deploy/staging/staging.sh 203.0.113.10 ubuntu staging.example.com
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

# ---- CONFIGURATION SECTION ----
# App settings
APP_NAME="atlas"                    # Name of the application
APP_DIR="/opt/$APP_NAME"            # Installation directory on server

# Server settings (production remote)
STAGING_HOST="192.168.20.17"       # Remote staging server IP address (production)
STAGING_USER="atlas_deploy"        # SSH username for remote deployment (production)

# Domain/SSL settings
DOMAIN=${3:-"staging.example.com"}           # Domain for SSL certificate
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
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g npm@latest

# 3. Setup application directory
echo "Setting up application directory..."
sudo mkdir -p $APP_DIR && sudo chown -R $USER:$USER $APP_DIR

# Ensure frontend directory is owned by atlas_deploy for build permissions
sudo chown -R atlas_deploy:atlas_deploy $APP_DIR/frontend

# 4. Clone or update the repository
echo "Checking for existing repository..."
# --- Use 0.1.0-staging branch for remote production deployment ---
if [ -d "$APP_DIR/.git" ]; then
    echo "Updating existing repository..."
    cd $APP_DIR && git fetch && git reset --hard origin/0.1.0-staging && git clean -fd && git lfs pull
else
    echo "Cloning fresh repository..."
    git clone --branch 0.1.0-staging https://github.com/AI-as-Infrastructure/aiinfra-atlas.git $APP_DIR && cd $APP_DIR && git lfs pull
fi

# 5. Move the environment file into place (copied from Makefile before running this script)
if [ -f "/tmp/.env.staging" ]; then
    echo "Copying .env.staging into $APP_DIR/config/.env.staging"
    mkdir -p "$APP_DIR/config"
    mv /tmp/.env.staging "$APP_DIR/config/.env.staging"
else
    echo "ERROR: /tmp/.env.staging not found! Please transfer it before running this script."
    exit 1
fi

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

# 7. Build frontend
echo "Building frontend..."
cd $APP_DIR/frontend
npm install && npm run build

# 8. Set up Nginx and Gunicorn
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
Environment="ATLAS_ENV=staging"
ExecStart=$APP_DIR/.venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000 --access-logfile /var/log/$APP_NAME/gunicorn-access.log --error-logfile /var/log/$APP_NAME/gunicorn-error.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Create Nginx config with improved security headers
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
echo "Access at: https://$DOMAIN"

# Add command to download remote logs
echo "To download logs from the server, run:"
echo "mkdir -p deploy/staging/logs && cp /var/log/$APP_NAME/*.log deploy/staging/logs/"

# Copy environment variables for frontend
echo "Setting up frontend environment..."
grep '^VITE_' $APP_DIR/config/.env.staging > $APP_DIR/frontend/.env
echo "✅ Frontend environment configured"

# Create proper environment files instead of symlinks
echo "Setting up backend environment..."
cp $APP_DIR/config/.env.staging $APP_DIR/config/.env
echo "✅ Backend environment configured" 

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