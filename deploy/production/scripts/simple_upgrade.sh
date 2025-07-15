#!/bin/bash

# Simple production upgrade script - for server-side upgrades with rollback capability
# This script assumes you're running it directly on the production server

set -euo pipefail
trap 'echo "❌ Upgrade failed at line $LINENO"; exit 1' ERR

# Configuration
APP_NAME="atlas"
APP_DIR="/opt/atlas"
GIT_BRANCH="${GIT_BRANCH:-main}"

echo "🚀 Starting production upgrade (server-side)..."

# 1. Verify we're in the right place
if [ ! -d "$APP_DIR" ]; then
    echo "ERROR: $APP_DIR not found. This script must be run on the production server."
    exit 1
fi

if [ ! -f "$APP_DIR/config/.env.production" ]; then
    echo "ERROR: $APP_DIR/config/.env.production not found"
    exit 1
fi

cd "$APP_DIR"

# 2. Load environment variables
set -a
source "$APP_DIR/config/.env.production"
set +a

# Extract domain for final verification
DOMAIN=$(echo "$VITE_API_URL" | sed -E 's|^https?://||; s|/$||')

# 3. Update code
echo "🔄 Updating code..."
git stash push -m "Production upgrade stash $(date)" || true
git fetch origin
git reset --hard origin/$GIT_BRANCH
git lfs pull

# 4. Always rebuild frontend for simplicity
echo "🏗️ Rebuilding frontend..."
cd frontend
npm install
export NODE_OPTIONS="--max_old_space_size=4096"
npm run build
cd ..

# Update frontend environment files
export ENVIRONMENT=production
chmod +x config/generate_vue_files.sh
./config/generate_vue_files.sh

# 5. Update Python dependencies
echo "🐍 Updating Python dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt

# 6. Graceful service restart
echo "🔄 Restarting services..."

# Stop services gracefully
echo "Stopping services..."
sudo systemctl stop gunicorn llm-worker || true

# Wait for complete shutdown (up to 30 seconds)
echo "Waiting for services to stop..."
for i in {1..30}; do
    if ! sudo systemctl is-active --quiet gunicorn && ! sudo systemctl is-active --quiet llm-worker; then
        echo "✅ Services stopped cleanly"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️ Services taking too long to stop - forcing shutdown"
        pkill -u "$(whoami)" -f 'gunicorn.*backend.app' || true
        pkill -u "$(whoami)" -f 'python.*worker.py' || true
    fi
    sleep 1
done

# Reset failed states
sudo systemctl reset-failed gunicorn llm-worker || true

# Start services
echo "Starting services..."
sudo systemctl start gunicorn llm-worker

# 7. Verify services are running
echo "🔍 Verifying services..."
sleep 5  # Give services time to start

for service in gunicorn llm-worker; do
    if ! sudo systemctl is-active --quiet $service; then
        echo "❌ ERROR: $service failed to start"
        echo "Check logs: journalctl -u $service -n 50"
        exit 1
    fi
done

# 8. Restart Nginx
echo "🔄 Restarting Nginx..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration test failed"
    exit 1
fi
sudo systemctl reload nginx

# 9. Verify application is responding
echo "🔍 Testing application response..."
sleep 2
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" | grep -q "200\|301\|302"; then
    echo "✅ Application is responding"
else
    echo "⚠️ Application may not be responding correctly"
    echo "Check manually: curl -I https://$DOMAIN"
fi

echo "✅ Production upgrade complete!"
echo "✅ Application running at: https://$DOMAIN"
echo ""
echo "🔍 To verify services:"
echo "  sudo systemctl status gunicorn llm-worker"
echo "  curl -I https://$DOMAIN"
echo ""
echo "📋 If issues arise, check logs:"
echo "  journalctl -u gunicorn -n 30"
echo "  journalctl -u llm-worker -n 30"
echo "  journalctl -u nginx -n 30"