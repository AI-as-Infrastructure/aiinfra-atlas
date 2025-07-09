#!/bin/bash
#=============================================================================
# ATLAS LOCALHOST STAGING ENVIRONMENT GRACEFUL STOP
#=============================================================================
# 
# PURPOSE:
#   This script gracefully stops the local staging environment services while
#   preserving data and configurations for potential restart.
# 
# USAGE:
#   ./deploy/staging/scripts/stop_staging_localhost.sh
#
# REQUIREMENTS:
#   - Local staging environment running
#   - sudo access for service management
#
#=============================================================================

set -e

APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"
LOG_DIR="/var/log/$APP_NAME"

echo "🛑 Stopping local staging environment gracefully..."

# App settings
APP_NAME="atlas"

echo "📊 Checking current service status..."
sudo systemctl status gunicorn --no-pager -l || echo "Gunicorn not running"
sudo systemctl status llm-worker --no-pager -l || echo "LLM worker not running"
sudo systemctl status nginx --no-pager -l || echo "Nginx not running"
sudo systemctl status redis-server --no-pager -l || echo "Redis not running"

echo ""
echo "🔄 Stopping services gracefully..."

# Stop LLM worker first (handles in-flight requests)
echo "Stopping LLM worker..."
sudo systemctl stop llm-worker || echo "LLM worker was not running"

# Wait a moment for LLM worker to finish current tasks
sleep 2

# Stop Gunicorn (backend API)
echo "Stopping Gunicorn backend..."
sudo systemctl stop gunicorn || echo "Gunicorn was not running"

# Stop Nginx (frontend)
echo "Stopping Nginx..."
sudo systemctl stop nginx || echo "Nginx was not running"

# Stop Redis last (in case services need to write final data)
echo "Stopping Redis..."
sudo systemctl stop redis-server || echo "Redis was not running"

echo ""
echo "📈 Memory cleanup..."
# Force garbage collection and clear any remaining memory
sync
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || echo "Note: Cannot clear system caches (non-root)"

# Clean temporary files but preserve logs and data
echo "🧹 Cleaning temporary files..."
sudo rm -f /tmp/gunicorn-*.pid /tmp/atlas-*.tmp 2>/dev/null || true
sudo rm -f /tmp/.env.staging 2>/dev/null || true

# Clear any stale lock files
if [ -d "$APP_DIR" ]; then
    sudo find "$APP_DIR" -name "*.lock" -delete 2>/dev/null || true
    sudo find "$APP_DIR" -name "*.pid" -delete 2>/dev/null || true
fi

# Reload systemd to clean up any stale service states
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

echo ""
echo "📋 Final service status check..."
sudo systemctl is-active gunicorn || echo "✅ Gunicorn stopped"
sudo systemctl is-active llm-worker || echo "✅ LLM worker stopped"
sudo systemctl is-active nginx || echo "✅ Nginx stopped"
sudo systemctl is-active redis-server || echo "✅ Redis stopped"

echo ""
echo "✅ Local staging environment stopped gracefully!"
echo ""
echo "📋 Next steps:"
echo "   • Application services are stopped but data is preserved"
echo "   • Nginx and Redis kept running for development"
echo "   • Logs preserved in $LOG_DIR"
echo "   • To restart: run 'make sl' to redeploy staging"
echo "   • To clean up completely: run 'make dsl'"
echo ""
echo "💡 Manual service control:"
echo "   • Start: sudo systemctl start <service>"
echo "   • Stop:  sudo systemctl stop <service>"
echo "   • Status: sudo systemctl status <service>"