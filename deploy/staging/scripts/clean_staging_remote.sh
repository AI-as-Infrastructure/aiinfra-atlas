#!/bin/bash
# Wrapper around old clean_staging.sh but renamed for clarity

# Delegate to same file content

set -e

# Include original script content

#=============================================================================
# ATLAS STAGING ENVIRONMENT CLEANUP
#=============================================================================
# 
# PURPOSE:
#   This script completely removes the staging environment, including all
#   services, files, and configurations.
# 
# USAGE:
#   ./deploy/staging/scripts/clean_staging_remote.sh
#
# REQUIREMENTS:
#   - config/.env.staging file must exist locally (copied to /tmp/.env.staging)
#   - SSH access to the staging server
#=============================================================================

# Load environment variables (expect .env.staging in current dir or /tmp)
if [ -f "config/.env.staging" ]; then
    source config/.env.staging
elif [ -f "/tmp/.env.staging" ]; then
    source /tmp/.env.staging
else
    echo "ERROR: No .env.staging file found!"
    exit 1
fi

STAGING_HOST=${STAGING_HOST}
STAGING_USER=${STAGING_USER:-atlas_deploy}
APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"

if [ -z "$STAGING_HOST" ]; then
    echo "ERROR: STAGING_HOST not set in environment"
    exit 1
fi

echo "🧹 Cleaning up remote staging environment at $STAGING_USER@$STAGING_HOST..."

ssh -o StrictHostKeyChecking=no $STAGING_USER@$STAGING_HOST bash -s << 'ENDSSH'
set -e
APP_NAME="atlas"
SUDO="sudo"

# Stop & disable services
$SUDO systemctl stop gunicorn || true
$SUDO systemctl disable gunicorn || true
$SUDO systemctl daemon-reload

# Stop nginx & redis
$SUDO systemctl stop nginx || true
$SUDO systemctl disable nginx || true
$SUDO systemctl stop redis-server || true
$SUDO systemctl disable redis-server || true

# Remove systemd files
$SUDO rm -f /etc/systemd/system/gunicorn.service

# Remove nginx site configs
$SUDO rm -f /etc/nginx/sites-enabled/atlas /etc/nginx/sites-available/atlas
$SUDO rm -f /etc/nginx/sites-enabled/default

# Remove application directory & logs
$SUDO rm -rf /opt/atlas /var/log/atlas

# Remove certificates (self-signed)
$SUDO rm -rf /etc/letsencrypt/live/*atlas* || true

$SUDO systemctl daemon-reload

echo "✅ Remote staging cleanup finished"
ENDSSH

echo "✅ Staging environment cleaned on remote host" 