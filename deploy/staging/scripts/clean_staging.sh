#!/bin/bash
#=============================================================================
# ATLAS STAGING ENVIRONMENT CLEANUP
#=============================================================================
# 
# PURPOSE:
#   This script completely removes the staging environment, including all
#   services, files, and configurations.
# 
# USAGE:
#   ./deploy/staging/scripts/clean_staging.sh
#
# REQUIREMENTS:
#   - config/.env.staging file must exist
#   - SSH access to the staging server
#
#=============================================================================

set -e

# Load environment variables
if [ -f "config/.env.staging" ]; then
    source config/.env.staging
elif [ -f "/tmp/.env.staging" ]; then
    source /tmp/.env.staging
else
    echo "ERROR: No .env.staging file found!"
    exit 1
fi

# Set default values if not in env file
STAGING_HOST=${STAGING_HOST}
STAGING_USER=${STAGING_USER:-atlas_deploy}
APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"

if [ -z "$STAGING_HOST" ]; then
    echo "ERROR: STAGING_HOST not set in environment"
    exit 1
fi

echo "🧹 Cleaning up staging environment at $STAGING_USER@$STAGING_HOST..."

# Execute cleanup on remote server
ssh -o StrictHostKeyChecking=no $STAGING_USER@$STAGING_HOST "export SUDO_PASSWORD='$SUDO_PASSWORD'; bash -s" << 'ENDSSH'
    # Set locale to avoid warnings
    echo "Setting locale..."
    echo "$SUDO_PASSWORD" | sudo -S locale-gen en_US.UTF-8
    echo "$SUDO_PASSWORD" | sudo -S update-locale LANG=en_US.UTF-8
    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8

    echo "Stopping and removing services..."
    
    # Stop and disable Gunicorn
    echo "Stopping Gunicorn..."
    echo "$SUDO_PASSWORD" | sudo -S systemctl stop gunicorn || true
    echo "$SUDO_PASSWORD" | sudo -S systemctl disable gunicorn || true
    echo "$SUDO_PASSWORD" | sudo -S rm -f /etc/systemd/system/gunicorn.service
    echo "$SUDO_PASSWORD" | sudo -S systemctl daemon-reload
    
    # Stop and disable Nginx
    echo "Stopping Nginx..."
    echo "$SUDO_PASSWORD" | sudo -S systemctl stop nginx || true
    echo "$SUDO_PASSWORD" | sudo -S systemctl disable nginx || true
    
    # Remove Nginx configurations
    echo "Removing Nginx configurations..."
    echo "$SUDO_PASSWORD" | sudo -S rm -f /etc/nginx/sites-enabled/$APP_NAME
    echo "$SUDO_PASSWORD" | sudo -S rm -f /etc/nginx/sites-available/$APP_NAME
    echo "$SUDO_PASSWORD" | sudo -S rm -f /etc/nginx/sites-enabled/default
    
    # Remove SSL certificates
    echo "Removing SSL certificates..."
    echo "$SUDO_PASSWORD" | sudo -S rm -rf /etc/letsencrypt/live/$DOMAIN || true
    echo "$SUDO_PASSWORD" | sudo -S rm -rf /etc/letsencrypt/archive/$DOMAIN || true
    echo "$SUDO_PASSWORD" | sudo -S rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf || true
    
    # Remove Nginx logs
    echo "Removing Nginx logs..."
    echo "$SUDO_PASSWORD" | sudo -S rm -f /var/log/nginx/access.log
    echo "$SUDO_PASSWORD" | sudo -S rm -f /var/log/nginx/error.log
    echo "$SUDO_PASSWORD" | sudo -S rm -f /var/log/nginx/*.log
    
    # Stop and disable Redis
    echo "Stopping Redis..."
    echo "$SUDO_PASSWORD" | sudo -S systemctl stop redis-server || true
    echo "$SUDO_PASSWORD" | sudo -S systemctl disable redis-server || true
    
    # Kill any remaining processes
    echo "Killing any remaining processes..."
    echo "$SUDO_PASSWORD" | sudo -S pkill -f gunicorn || true
    echo "$SUDO_PASSWORD" | sudo -S pkill -f "python.*atlas" || true
    
    # Verify services are stopped
    echo "Verifying services are stopped..."
    if systemctl is-active --quiet gunicorn; then
        echo "WARNING: Gunicorn is still running, forcing stop..."
        echo "$SUDO_PASSWORD" | sudo -S systemctl stop gunicorn
    fi
    if systemctl is-active --quiet nginx; then
        echo "WARNING: Nginx is still running, forcing stop..."
        echo "$SUDO_PASSWORD" | sudo -S systemctl stop nginx
    fi
    if systemctl is-active --quiet redis-server; then
        echo "WARNING: Redis is still running, forcing stop..."
        echo "$SUDO_PASSWORD" | sudo -S systemctl stop redis-server
    fi
    
    echo "Removing application files..."
    # Force remove the application directory and all its contents
    echo "$SUDO_PASSWORD" | sudo -S rm -rf /opt/atlas
    # Double check and force remove if it still exists
    if [ -d "/opt/atlas" ]; then
        echo "Force removing /opt/atlas directory..."
        echo "$SUDO_PASSWORD" | sudo -S chattr -i /opt/atlas 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /opt/atlas
    fi
    
    echo "Removing logs..."
    echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/$APP_NAME
    
    echo "Reloading systemd..."
    echo "$SUDO_PASSWORD" | sudo -S systemctl daemon-reload
    
    # Final verification
    echo "Performing final verification..."
    if [ -d "/opt/atlas" ]; then
        echo "ERROR: /opt/atlas directory still exists!"
        exit 1
    fi
    if systemctl is-active --quiet gunicorn; then
        echo "ERROR: Gunicorn service is still running!"
        exit 1
    fi
    if systemctl is-active --quiet redis-server; then
        echo "ERROR: Redis service is still running!"
        exit 1
    fi
    
    echo "✅ Cleanup complete!"
ENDSSH

echo "✅ Staging environment cleaned up successfully!" 