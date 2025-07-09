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

echo "🔄 Gracefully stopping remote staging services..."

# Function to check if a service is running
check_service() {
    local service_name=$1
    if $SUDO systemctl is-active --quiet "$service_name" 2>/dev/null; then
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
        $SUDO systemctl stop "$service_name"
        echo "✅ $display_name stopped"
    else
        echo "ℹ️  $display_name was not running"
    fi
}

# Stop application services first
stop_service "gunicorn" "Gunicorn (application server)"

# Stop worker services if they exist
if $SUDO systemctl list-unit-files | grep -q llm-worker; then
    stop_service "llm-worker" "LLM Worker service"
fi

if $SUDO systemctl list-unit-files | grep -q atlas-worker; then
    stop_service "atlas-worker" "Atlas Worker service"
fi

# Keep infrastructure services running for staging environment
echo "Checking Nginx..."
if check_service "nginx"; then
    echo "ℹ️  Keeping Nginx running (needed for staging infrastructure)"
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
$SUDO rm -f /tmp/gunicorn-*.pid /tmp/atlas-*.tmp 2>/dev/null || true

# Clear any stale lock files
if [ -d "/opt/atlas" ]; then
    $SUDO find /opt/atlas -name "*.lock" -delete 2>/dev/null || true
    $SUDO find /opt/atlas -name "*.pid" -delete 2>/dev/null || true
fi

# Reload systemd to clean up any stale service states
echo "🔄 Reloading systemd..."
$SUDO systemctl daemon-reload

# Display status summary
echo ""
echo "📊 Service Status Summary:"
echo "========================="

services=("gunicorn:Gunicorn" "nginx:Nginx" "redis-server:Redis")
for service_info in "${services[@]}"; do
    IFS=':' read -r service display <<< "$service_info"
    if check_service "$service"; then
        echo "🟢 $display: Running"
    else
        echo "🔴 $display: Stopped"
    fi
done

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