#!/bin/bash
#=============================================================================
# ATLAS CLOUDFLARE TUNNEL CLEANUP
#=============================================================================
#
# PURPOSE:
#   Completely removes the Cloudflare tunnel deployment:
#   services, systemd units, Nginx config, application directory, logs,
#   cloudflared config. UFW state is NOT modified (operator manages firewall
#   independently).
#
# USAGE:
#   make dcf
#   ./deploy/cloudflare/scripts/clean_cloudflare.sh
#
# NOTE:
#   The Cloudflare tunnel itself (in the dashboard) is NOT deleted.
#   Delete it manually via the Cloudflare Zero Trust dashboard if needed.
#
#=============================================================================

set -e

APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"

echo "This will completely remove the Cloudflare tunnel deployment."
echo "WARNING: This action cannot be undone!"
echo ""
echo "The following will be removed:"
echo "  - systemd services: gunicorn, llm-worker, cloudflared"
echo "  - Nginx site config: /etc/nginx/sites-available/$APP_NAME"
echo "  - Application directory: $APP_DIR"
echo "  - Logs: /var/log/$APP_NAME"
echo "  - cloudflared config: /etc/cloudflared/config.yml"
echo ""
echo "The following will NOT be removed:"
echo "  - UFW firewall rules (manage manually with 'sudo ufw status')"
echo "  - Cloudflare tunnel in dashboard (delete manually if needed)"
echo "  - Redis data (clear manually if needed)"
echo ""
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled"
    exit 1
fi

echo "Stopping and removing services..."

# Stop and disable services
sudo systemctl stop cloudflared gunicorn llm-worker 2>/dev/null || true
sudo systemctl disable cloudflared gunicorn llm-worker 2>/dev/null || true

# Remove systemd units
sudo rm -f /etc/systemd/system/gunicorn.service
sudo rm -f /etc/systemd/system/llm-worker.service
sudo rm -f /etc/systemd/system/cloudflared.service

# Remove Nginx site config
echo "Removing Nginx site config..."
sudo rm -f /etc/nginx/sites-enabled/$APP_NAME
sudo rm -f /etc/nginx/sites-available/$APP_NAME
sudo systemctl reload nginx 2>/dev/null || true

# Remove cloudflared config
sudo rm -f /etc/cloudflared/config.yml
sudo rmdir /etc/cloudflared 2>/dev/null || true

# Remove application directory
echo "Removing application directory..."
sudo rm -rf $APP_DIR

# Remove logs
echo "Removing logs..."
sudo rm -rf /var/log/$APP_NAME

# Clean up temp files
sudo rm -f /tmp/gunicorn.service /tmp/llm-worker.service /tmp/cloudflared.service /tmp/cloudflared-config.yml /tmp/atlas-cloudflare.conf

# Reload systemd
sudo systemctl daemon-reload

echo ""
echo "Cleanup complete."
echo ""
echo "Remaining manual steps (if needed):"
echo "  - Delete tunnel in Cloudflare Zero Trust dashboard"
echo "  - Remove DNS records pointing to the tunnel"
echo "  - Adjust UFW rules: sudo ufw status / sudo ufw disable"
echo "  - Uninstall cloudflared: sudo apt remove cloudflared"
echo "  - Stop Redis: sudo systemctl stop redis-server"
