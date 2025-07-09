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

echo "🛑 Gracefully stopping local staging environment..."

# Function to check if a service is running
check_service() {
    local service_name=$1
    if sudo systemctl is-active --quiet "$service_name" 2>/dev/null; then
        return 0  # Service is running
    else
        return 1  # Service is not running
    fi
}

# Function to stop a service gracefully
stop_service() {
    local service_name=$1
    local display_name=$2
    
    echo "Checking $display_name..."
    if check_service "$service_name"; then
        echo "Stopping $display_name..."
        sudo systemctl stop "$service_name"
        echo "✅ $display_name stopped"
    else
        echo "ℹ️  $display_name was not running"
    fi
}

# Stop services in order (application first, then infrastructure)
echo "🔄 Stopping staging services..."

# Stop application services first
stop_service "gunicorn" "Gunicorn (application server)"
stop_service "llm-worker" "LLM Worker service"

# Stop infrastructure services (but keep some running for development)
echo "Checking Nginx..."
if check_service "nginx"; then
    echo "ℹ️  Keeping Nginx running (may be used by other projects)"
    echo "   To stop Nginx manually: sudo systemctl stop nginx"
else
    echo "ℹ️  Nginx was not running"
fi

echo "Checking Redis..."
if check_service "redis-server"; then
    echo "ℹ️  Keeping Redis running for data persistence"
    echo "   To stop Redis manually: sudo systemctl stop redis-server"
else
    echo "ℹ️  Redis was not running"
fi

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

# Display status summary
echo ""
echo "📊 Service Status Summary:"
echo "========================="

services=("gunicorn:Gunicorn" "llm-worker:LLM Worker" "nginx:Nginx" "redis-server:Redis")
for service_info in "${services[@]}"; do
    IFS=':' read -r service display <<< "$service_info"
    if check_service "$service"; then
        echo "🟢 $display: Running"
    else
        echo "🔴 $display: Stopped"
    fi
done

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