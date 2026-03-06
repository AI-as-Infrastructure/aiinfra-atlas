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
#   1. cloudflared (disconnect tunnel first -- site goes offline)
#   2. nginx       (stop reverse proxy)
#   3. llm-worker  (wait for in-flight LLM requests)
#   4. gunicorn    (stop backend API)
#   5. redis       (stop last -- services may write final data)
#
#=============================================================================

set -e

APP_NAME="atlas"

echo "Stopping Cloudflare tunnel deployment..."
echo ""

echo "Checking current service status..."
for svc in cloudflared nginx gunicorn llm-worker redis-server; do
    if sudo systemctl is-active --quiet $svc 2>/dev/null; then
        echo "  $svc: running"
    else
        echo "  $svc: not running"
    fi
done

echo ""
echo "Stopping services..."

# 1. Stop cloudflared first (site goes offline immediately)
echo "Stopping cloudflared tunnel..."
sudo systemctl stop cloudflared 2>/dev/null || echo "  cloudflared was not running"

# 2. Stop Nginx (reverse proxy)
echo "Stopping Nginx..."
sudo systemctl stop nginx 2>/dev/null || echo "  nginx was not running"

# 3. Wait for in-flight requests, then stop LLM worker
echo "Waiting 10 seconds for in-flight LLM requests..."
sleep 10
echo "Stopping LLM worker..."
sudo systemctl stop llm-worker 2>/dev/null || echo "  llm-worker was not running"

# 4. Stop Gunicorn
echo "Stopping Gunicorn..."
sudo systemctl stop gunicorn 2>/dev/null || echo "  gunicorn was not running"

# 5. Stop Redis last
echo "Stopping Redis..."
sudo systemctl stop redis-server 2>/dev/null || echo "  redis-server was not running"

# Memory cleanup
echo ""
echo "Memory cleanup..."
sync
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || echo "Note: Cannot clear system caches"

echo ""
echo "Final service status:"
for svc in cloudflared nginx gunicorn llm-worker redis-server; do
    if sudo systemctl is-active --quiet $svc 2>/dev/null; then
        echo "  $svc: STILL RUNNING (check manually)"
    else
        echo "  $svc: stopped"
    fi
done

echo ""
echo "Cloudflare tunnel deployment stopped."
echo "Data and configuration preserved for restart."
echo ""
echo "To restart: make cf"
echo "To clean up completely: make dcf"
