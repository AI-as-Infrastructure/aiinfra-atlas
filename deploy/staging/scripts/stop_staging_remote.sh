#!/bin/bash
#=============================================================================
# ATLAS REMOTE STAGING ENVIRONMENT GRACEFUL STOP
#=============================================================================
# 
# PURPOSE:
#   This script gracefully stops the remote staging environment services while
#   preserving data and configurations for potential restart.
# 
# USAGE:
#   ./deploy/staging/scripts/stop_staging_remote.sh
#
# REQUIREMENTS:
#   - config/.env.staging file must exist locally (copied to /tmp/.env.staging)
#   - SSH access to the staging server
#
#=============================================================================

set -e

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

echo "🛑 Gracefully stopping remote staging environment at $STAGING_USER@$STAGING_HOST..."

# Execute graceful stop on remote server
ssh -o StrictHostKeyChecking=no $STAGING_USER@$STAGING_HOST bash -s << 'ENDSTOP'

set -e
APP_NAME="atlas"
SUDO="sudo"

echo "🛑 Stopping remote staging environment gracefully..."

# App settings
APP_NAME="atlas"

echo "📊 Checking current service status..."
$SUDO systemctl status gunicorn --no-pager -l || echo "Gunicorn not running"
$SUDO systemctl status llm-worker --no-pager -l || echo "LLM worker not running"
$SUDO systemctl status nginx --no-pager -l || echo "Nginx not running"
$SUDO systemctl status redis-server --no-pager -l || echo "Redis not running"

echo ""
echo "🔄 Stopping services gracefully..."

# Stop LLM worker first (handles in-flight requests)
echo "Stopping LLM worker..."
$SUDO systemctl stop llm-worker || echo "LLM worker was not running"

# Wait a moment for LLM worker to finish current tasks
sleep 2

# Stop Gunicorn (backend API)
echo "Stopping Gunicorn backend..."
$SUDO systemctl stop gunicorn || echo "Gunicorn was not running"

# Stop Nginx (frontend)
echo "Stopping Nginx..."
$SUDO systemctl stop nginx || echo "Nginx was not running"

# Stop Redis last (in case services need to write final data)
echo "Stopping Redis..."
$SUDO systemctl stop redis-server || echo "Redis was not running"

echo ""
echo "📈 Memory cleanup..."
# Force garbage collection and clear any remaining memory
sync
$SUDO sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || echo "Note: Cannot clear system caches"

# Clean temporary files but preserve logs and data
echo "🧹 Cleaning temporary files..."
$SUDO rm -f /tmp/gunicorn-*.pid /tmp/atlas-*.tmp 2>/dev/null || true

# Clear any stale lock files
if [ -d "/opt/atlas" ]; then
    $SUDO find /opt/atlas -name "*.lock" -delete 2>/dev/null || true
    $SUDO find /opt/atlas -name "*.pid" -delete 2>/dev/null || true
fi

# Reload systemd to clean up any stale service states
echo "🔄 Reloading systemd..."
$SUDO systemctl daemon-reload

echo ""
echo "📋 Final service status check..."
$SUDO systemctl is-active gunicorn || echo "✅ Gunicorn stopped"
$SUDO systemctl is-active llm-worker || echo "✅ LLM worker stopped"
$SUDO systemctl is-active nginx || echo "✅ Nginx stopped"
$SUDO systemctl is-active redis-server || echo "✅ Redis stopped"

echo ""
echo "✅ Remote staging services stopped gracefully!"
echo ""
echo "📋 Next steps:"
echo "   • Application services are stopped but data is preserved"
echo "   • Nginx and Redis kept running for staging infrastructure"
echo "   • Logs preserved in /var/log/atlas"
echo "   • To restart: run 'make sr' to redeploy remote staging"
echo "   • To clean up completely: run 'make dsr'"

ENDSTOP

echo "✅ Remote staging environment stopped gracefully!"
echo ""
echo "📋 Local next steps:"
echo "   • Remote staging application is stopped"
echo "   • To restart: run 'make sr' to redeploy remote staging"
echo "   • To clean up completely: run 'make dsr'"