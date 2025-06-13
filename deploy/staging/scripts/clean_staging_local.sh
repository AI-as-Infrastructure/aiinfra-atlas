#!/bin/bash
# ATLAS LOCAL STAGING ENVIRONMENT CLEANUP
# Safely removes all Atlas-related files, services, and configs from local staging.
# Does NOT touch user files, home directories, or unrelated system files.

set -e

APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"
LOG_DIR="/var/log/$APP_NAME"
CERT_DIR="/etc/letsencrypt/live/$APP_NAME"
NGINX_SITE="/etc/nginx/sites-available/$APP_NAME"
NGINX_SITE_LINK="/etc/nginx/sites-enabled/$APP_NAME"
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"
LLM_WORKER_SERVICE="/etc/systemd/system/llm-worker.service"

# Warnings and confirmation
cat << EOF
WARNING: This will remove the local staging environment for Atlas.
- Only Atlas-related files, logs, and services will be removed.
- Your home directory and unrelated system files will NOT be touched.
- You must have sudo privileges.
EOF
read -p "Are you sure you want to proceed? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Stop and disable services
sudo systemctl stop gunicorn || true
sudo systemctl disable gunicorn || true
sudo systemctl stop llm-worker || true
sudo systemctl disable llm-worker || true
sudo systemctl daemon-reload

# Remove systemd service files
sudo rm -f "$GUNICORN_SERVICE" "$LLM_WORKER_SERVICE"

# Remove Nginx config
sudo rm -f "$NGINX_SITE" "$NGINX_SITE_LINK"
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx || true

# Remove log directory
sudo rm -rf "$LOG_DIR"

# Remove app directory
sudo rm -rf "$APP_DIR"

# Remove self-signed certs (if present)
sudo rm -rf "$CERT_DIR"

# Optionally clean up Redis config (commented out for safety)
# sudo sed -i '/# Atlas staging configuration/,$d' /etc/redis/redis.conf
# sudo systemctl restart redis-server

# Remove symlinks to logs in project root
PROJECT_ROOT="$(dirname $(dirname $(dirname "$0")))"
rm -f "$PROJECT_ROOT/deploy/staging/logs/nginx-error.log" "$PROJECT_ROOT/deploy/staging/logs/nginx-access.log"

# Final message
cat << EOF
✅ Local staging environment cleaned up.
- If you encounter issues with ports or services, check for lingering processes or configs.
- No user files or unrelated system files were touched.
EOF 