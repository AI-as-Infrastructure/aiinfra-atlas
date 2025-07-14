#!/bin/bash
#=============================================================================
# ATLAS PRODUCTION ENVIRONMENT CLEANUP
#=============================================================================
# 
# PURPOSE:
#   This script completely removes the production environment.
#   Can be run locally on the server or remotely via SSH.
# 
# USAGE:
#   Local (on server): ./deploy/production/scripts/clean_prod.sh
#   Remote: ./deploy/production/scripts/clean_prod.sh --remote
#
#=============================================================================

set -e

APP_NAME="atlas"
APP_DIR="/opt/atlas"

# Check if running remotely
if [ "$1" = "--remote" ]; then
    # Remote cleanup via SSH (legacy mode)
    # Load environment file to get connection details
    if [ -f "config/.env.production" ]; then
      set -a
      source config/.env.production
      set +a
    fi

    if [ -z "$PRODUCTION_HOST" ]; then
        echo "❌ PRODUCTION_HOST not set in config/.env.production"
        exit 1
    fi

    SSH_KEY="${SSH_KEY:-$HOME/atlas-prod-key.pem}"
    PRODUCTION_USER="${PRODUCTION_USER:-atlas_deploy}"

    echo "🧹 This will completely remove the production environment at $PRODUCTION_HOST"
    echo "⚠️  This action cannot be undone!"
    read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cleanup cancelled"
        exit 1
    fi

    echo "Connecting to $PRODUCTION_HOST via SSH to perform cleanup..."
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $PRODUCTION_USER@"$PRODUCTION_HOST" \
        "cd $APP_DIR && ./deploy/production/scripts/clean_prod.sh"
    
    echo "✅ Remote cleanup complete"
    exit 0
fi

# Local cleanup (default mode)
echo "🧹 This will completely remove the production environment locally"
echo "⚠️  This action cannot be undone!"
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

echo 'Stopping and removing services...'

# Stop and disable services
sudo systemctl stop gunicorn llm-worker 2>/dev/null || true
sudo systemctl disable gunicorn llm-worker 2>/dev/null || true
sudo rm -f /etc/systemd/system/gunicorn.service /etc/systemd/system/llm-worker.service

# Remove nginx site config
sudo rm -f /etc/nginx/sites-available/atlas /etc/nginx/sites-enabled/atlas
sudo systemctl restart nginx 2>/dev/null || true

# Remove application directory
sudo rm -rf $APP_DIR

# Remove logs
sudo rm -rf /var/log/$APP_NAME

# Remove SSL certificates (Let's Encrypt)
echo "Removing SSL certificates..."
if [ -d "/etc/letsencrypt/live" ]; then
    # Remove certificates for any atlas-related domains
    sudo find /etc/letsencrypt/live -name "*atlas*" -type d -exec rm -rf {} + 2>/dev/null || true
    # Remove renewal configs
    sudo find /etc/letsencrypt/renewal -name "*atlas*" -type f -exec rm -f {} + 2>/dev/null || true
    # Remove archive files
    sudo find /etc/letsencrypt/archive -name "*atlas*" -type d -exec rm -rf {} + 2>/dev/null || true
fi

# Clean up any temp files
sudo rm -f /tmp/.env.production /tmp/gunicorn.service /tmp/llm-worker.service /tmp/nginx.conf

# Reload systemd
sudo systemctl daemon-reload

echo '✅ Local cleanup complete - environment fully removed' 