#!/bin/bash
#=============================================================================
# ATLAS CLOUDFLARE TUNNEL GRACEFUL STOP
#=============================================================================
#
# PURPOSE:
#   Gracefully stops all Cloudflare tunnel deployment services while
#   preserving data and configuration for restart.
#
# USAGE:
#   make scf
#   ./deploy/cloudflare/scripts/stop_cloudflare.sh
#
# STOP ORDER:
#   1. nginx       (stop reverse proxy -- site goes offline)
#   2. llm-worker  (wait for in-flight LLM requests)
#   3. gunicorn    (stop backend API)
#   4. redis       (stop last -- services may write final data)
#
# NOTE: cloudflared is NOT stopped. It is operator-managed and may be
#   serving SSH access. Stopping it would lock out remote operators.
#
#=============================================================================

set -e

APP_NAME="atlas"

echo "Stopping Cloudflare tunnel deployment..."
echo ""

echo "Checking current service status..."
for svc in nginx gunicorn llm-worker redis-server cloudflared; do
    if sudo systemctl is-active --quiet $svc 2>/dev/null; then
        echo "  $svc: running"
    else
        echo "  $svc: not running"
    fi
done

echo ""
echo "Stopping services..."

# cloudflared is NOT stopped -- it is operator-managed and may serve SSH access.

# 1. Stop Nginx (reverse proxy -- site goes offline)
echo "Stopping Nginx..."
sudo systemctl stop nginx 2>/dev/null || echo "  nginx was not running"

# 2. Wait for in-flight requests, then stop LLM worker
echo "Waiting 10 seconds for in-flight LLM requests..."
sleep 10
echo "Stopping LLM worker..."
sudo systemctl stop llm-worker 2>/dev/null || echo "  llm-worker was not running"

# 3. Stop Gunicorn
echo "Stopping Gunicorn..."
sudo systemctl stop gunicorn 2>/dev/null || echo "  gunicorn was not running"

# 4. Stop Redis last
echo "Stopping Redis..."
sudo systemctl stop redis-server 2>/dev/null || echo "  redis-server was not running"

# Memory cleanup
echo ""
echo "Memory cleanup..."
sync
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || echo "Note: Cannot clear system caches"

echo ""
echo "Final service status:"
for svc in nginx gunicorn llm-worker redis-server; do
    if sudo systemctl is-active --quiet $svc 2>/dev/null; then
        echo "  $svc: STILL RUNNING (check manually)"
    else
        echo "  $svc: stopped"
    fi
done
# cloudflared status (informational only -- not managed by this script)
if sudo systemctl is-active --quiet cloudflared 2>/dev/null; then
    echo "  cloudflared: running (operator-managed, not stopped)"
else
    echo "  cloudflared: not running (operator-managed)"
fi

echo ""
echo "Application services stopped. cloudflared tunnel left running."
echo "Data and configuration preserved for restart."
echo ""
echo "To restart: make cf"
echo "To clean up completely: make dcf"
