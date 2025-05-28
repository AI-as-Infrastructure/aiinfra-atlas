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

# Server settings
STAGING_HOST=${1:-"your-staging-server-ip"}  # Staging server IP address
STAGING_USER=${2:-"ubuntu"}                  # SSH username for remote deployment

# Domain/SSL settings
DOMAIN=${3:-"staging.example.com"}           # Domain for SSL certificate
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"     # Where SSL certificates are stored

# ---- END CONFIGURATION ----

# Local paths (don't modify)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "🚀 Deploying to $STAGING_USER@$STAGING_HOST:$APP_DIR"

# Function to run commands on remote server
run_cmd() {
    ssh "$STAGING_USER@$STAGING_HOST" "$1"
}

# Function to copy files to remote server
copy_file() {
    local src="$1"
    local dest="$2"
    
    # Ensure the destination directory exists
    ssh "$STAGING_USER@$STAGING_HOST" "sudo mkdir -p $(dirname "$dest")"
    
    # Copy the file
    scp -r "$src" "$STAGING_USER@$STAGING_HOST:/tmp/transfer"
    ssh "$STAGING_USER@$STAGING_HOST" "sudo mv /tmp/transfer $(basename "$dest")"
}

# 1. Check for environment file
if [ ! -f "$PROJECT_ROOT/config/.env.staging" ]; then
    echo "ERROR: config/.env.staging file not found!"
    echo "Please create it from config/.env.development and modify as needed."
    exit 1
fi

# 2. Install required packages with specific versions
echo "Installing required packages..."
run_cmd "sudo apt-get update && sudo apt-get install -y python3.10 python3.10-venv python3.10-dev python3-pip nginx git git-lfs"

# Install specific Node.js version
echo "Setting up Node.js environment..."
run_cmd "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
run_cmd "sudo apt-get install -y nodejs"
run_cmd "sudo npm install -g npm@latest"

# 3. Setup application directory
echo "Setting up application directory..."
run_cmd "sudo mkdir -p $APP_DIR && sudo chown -R $STAGING_USER:$STAGING_USER $APP_DIR"

# 4. Clone or update the repository
echo "Checking for existing repository..."
if run_cmd "[ -d '$APP_DIR/.git' ]"; then
    echo "Updating existing repository..."
    run_cmd "cd $APP_DIR && git fetch && git reset --hard origin/main && git clean -fd && git lfs pull"
else
    echo "Cloning fresh repository..."
    run_cmd "git clone https://github.com/AI-as-Infrastructure/aiinfra-atlas.git $APP_DIR && cd $APP_DIR && git lfs pull"
fi

# 5. Copy and update environment file
echo "Copying and updating environment file..."
copy_file "$PROJECT_ROOT/config/.env.staging" "$APP_DIR/config/.env.staging"

# Update URLs in the environment file to use the actual domain
echo "Updating environment URLs for remote deployment..."
run_cmd "sed -i 's#VITE_API_URL=.*#VITE_API_URL=https://$DOMAIN#' $APP_DIR/config/.env.staging"
run_cmd "sed -i 's#CORS_ORIGINS=.*#CORS_ORIGINS=https://$DOMAIN#' $APP_DIR/config/.env.staging"
run_cmd "sed -i 's#API_BASE_URL=.*#API_BASE_URL=https://$DOMAIN/api#' $APP_DIR/config/.env.staging"
run_cmd "sed -i 's#WS_BASE_URL=.*#WS_BASE_URL=wss://$DOMAIN/ws#' $APP_DIR/config/.env.staging"

echo "✅ Environment file updated with domain: $DOMAIN"
echo "⚠️ IMPORTANT: If you need additional environment changes, edit the file manually on the server at:"
echo "    $APP_DIR/config/.env.staging"

# 6. Setup Python environment with explicit Python 3.10
echo "Setting up Python environment..."
run_cmd "cd $APP_DIR && python3.10 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r config/requirements.txt gunicorn"

# Ensure Python can find the application modules
echo "Setting up Python package structure..."
run_cmd "mkdir -p $APP_DIR/backend"
run_cmd "touch $APP_DIR/backend/__init__.py"
run_cmd "echo '$APP_DIR' > $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth"
run_cmd "chmod 644 $APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth"

# 7. Build frontend
echo "Building frontend..."
run_cmd "cd $APP_DIR/frontend"
run_cmd "npm install && npm run build"

# 8. Set up Nginx and Gunicorn
echo "Setting up Nginx and Gunicorn..."
run_cmd "sudo mkdir -p /var/log/$APP_NAME"

# Create local logs directory
mkdir -p "$PROJECT_ROOT/deploy/staging/logs"

# Create Gunicorn service file with logging
cat > /tmp/gunicorn.service << EOL
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=www-data
Group=www-data
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
scp /tmp/gunicorn.service "$STAGING_USER@$STAGING_HOST:/tmp/"
scp /tmp/nginx.conf "$STAGING_USER@$STAGING_HOST:/tmp/"
ssh "$STAGING_USER@$STAGING_HOST" "sudo mv /tmp/gunicorn.service /etc/systemd/system/ && \
                                  sudo mv /tmp/nginx.conf /etc/nginx/sites-available/$APP_NAME && \
                                  sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/ && \
                                  sudo rm -f /etc/nginx/sites-enabled/default"

# Add instructions about SSL certificates
echo "⚠️ Important: You must set up SSL certificates on the server before deployment is complete."
echo "If you're using Let's Encrypt, run on the server:"
echo "  sudo certbot --nginx -d $DOMAIN"
echo "Or for manual certificate installation, place certificates at:"
echo "  $CERT_DIR/fullchain.pem"
echo "  $CERT_DIR/privkey.pem"
echo "and ensure they are readable by www-data."

# 9. Set permissions and restart services
echo "Setting permissions and restarting services..."
run_cmd "sudo chown -R www-data:www-data $APP_DIR /var/log/$APP_NAME && \
         sudo systemctl daemon-reload && \
         sudo systemctl enable gunicorn && \
         sudo systemctl restart gunicorn && \
         sudo nginx -t && \
         sudo systemctl restart nginx"

echo "Deployment complete!"
echo "Access at: https://$STAGING_HOST (or https://$DOMAIN if DNS is configured)"

# Add command to download remote logs
echo "To download logs from the server, run:"
echo "mkdir -p deploy/staging/logs && scp $STAGING_USER@$STAGING_HOST:/var/log/$APP_NAME/*.log deploy/staging/logs/"

# Copy environment variables for frontend
echo "Setting up frontend environment..."
run_cmd "grep '^VITE_' $APP_DIR/config/.env.staging > $APP_DIR/frontend/.env"
echo "✅ Frontend environment configured"

# Create proper environment files instead of symlinks
echo "Setting up backend environment..."
run_cmd "cp $APP_DIR/config/.env.staging $APP_DIR/config/.env"
echo "✅ Backend environment configured" 