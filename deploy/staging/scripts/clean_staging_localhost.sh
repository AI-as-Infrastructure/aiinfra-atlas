#!/bin/bash
# ATLAS LOCALHOST STAGING ENVIRONMENT CLEANUP
# Identical to previous clean_staging_local.sh – safely removes Atlas files, services.

set -e

APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"
LOG_DIR="/var/log/$APP_NAME"
CERT_DIR="/etc/letsencrypt/live/$APP_NAME"
NGINX_SITE="/etc/nginx/sites-available/$APP_NAME"
NGINX_SITE_LINK="/etc/nginx/sites-enabled/$APP_NAME"
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"
LLM_WORKER_SERVICE="/etc/systemd/system/llm-worker.service"

cat << EOF
WARNING: This will remove the local staging environment for Atlas.
Only Atlas-related files, logs, and services will be removed.
Home directories & unrelated system files stay untouched.
EOF
read -p "Are you sure you want to proceed? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled." && exit 0
fi

sudo systemctl stop gunicorn || true
sudo systemctl disable gunicorn || true
sudo systemctl stop llm-worker || true
sudo systemctl disable llm-worker || true
sudo systemctl daemon-reload

sudo rm -f "$GUNICORN_SERVICE" "$LLM_WORKER_SERVICE"

sudo rm -f "$NGINX_SITE" "$NGINX_SITE_LINK"
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx || true

sudo rm -rf "$LOG_DIR"

sudo rm -rf "$APP_DIR"

sudo rm -rf "$CERT_DIR"

PROJECT_ROOT="$(dirname $(dirname $(dirname "$0")))"
rm -f "$PROJECT_ROOT/deploy/staging/logs/nginx-error.log" "$PROJECT_ROOT/deploy/staging/logs/nginx-access.log"

echo "✅ Localhost staging environment cleaned." 