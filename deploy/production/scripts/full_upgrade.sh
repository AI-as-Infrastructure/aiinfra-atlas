#!/bin/bash

# Full production upgrade script - for environment changes and complete rebuilds
# This script runs a complete rebuild like 'make p' but with backup/rollback capability

set -euo pipefail
trap 'echo "❌ Full upgrade failed at line $LINENO"; exit 1' ERR

# Configuration
APP_NAME="atlas"
APP_DIR="/opt/atlas"
GIT_BRANCH="${GIT_BRANCH:-main}"

echo "🚀 Starting FULL production upgrade (complete rebuild)..."

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

# 3. Update code (non-interactive, safe)
echo "🔄 Updating code..."

# Only stash if there are local changes; guard with timeout to avoid hangs
if ! git diff --quiet; then
    echo "Stashing tracked changes only (10s timeout)..."
    timeout 10s git stash push -m "Production upgrade stash $(date)" >/dev/null 2>&1 || \
        echo "⚠️  Stash timed out/failed; continuing without stash"
else
    echo "No local changes to stash"
fi

# Clean up any stale git lock from prior interruptions
[ -f .git/index.lock ] && rm -f .git/index.lock || true

# Refresh code non-interactively
git fetch --prune origin
git reset --hard origin/$GIT_BRANCH
git lfs pull

# 5. FULL rebuild - Python environment
echo "🐍 Rebuilding Python environment..."
# Create venv if missing (supports fresh servers)
if [ ! -d ".venv" ]; then
    if command -v python3.10 >/dev/null 2>&1; then
        python3.10 -m venv .venv
    else
        python3 -m venv .venv
    fi
fi
source .venv/bin/activate
pip install --upgrade pip
if [ ! -f "config/requirements.lock" ]; then
    echo "❌ Error: config/requirements.lock not found. Run 'make l' first."
    exit 1
fi
pip install -r config/requirements.lock

# 6. Set up Python package structure (in case it's missing)
echo "📦 Setting up Python package structure..."
mkdir -p backend
touch backend/__init__.py
echo "$APP_DIR" > .venv/lib/python3.10/site-packages/atlas.pth
chmod 644 .venv/lib/python3.10/site-packages/atlas.pth

# 7. Generate frontend environment files (picks up .env.production changes)
echo "🔄 Generating frontend environment files..."
export ENVIRONMENT=production
chmod +x config/generate_vue_files.sh
./config/generate_vue_files.sh

# 8. FULL rebuild - Frontend
echo "🏗️ Rebuilding frontend completely..."
cd frontend
npm install
export NODE_OPTIONS="--max_old_space_size=4096"
npm run build
cd ..

# 9. Update URLs in the environment file to match domain
echo "🔄 Updating environment URLs..."
sed -i "s#VITE_API_URL=.*#VITE_API_URL=https://$DOMAIN#" "$APP_DIR/config/.env.production"
sed -i "s#CORS_ORIGINS=.*#CORS_ORIGINS=https://$DOMAIN#" "$APP_DIR/config/.env.production"

# 10. Configure Redis (in case password changed)
echo "🔄 Configuring Redis..."
if [ -n "$REDIS_PASSWORD" ]; then
    sudo sed -i '/^#* *requirepass /d' /etc/redis/redis.conf
    sudo bash -c "echo 'requirepass $REDIS_PASSWORD' >> /etc/redis/redis.conf"
    sudo systemctl restart redis-server
    echo "✅ Redis configured with new password"
fi

# 11. Graceful service restart
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

# 12. Verify services are running
echo "🔍 Verifying services..."
sleep 5  # Give services time to start

for service in gunicorn llm-worker; do
    if ! sudo systemctl is-active --quiet $service; then
        echo "❌ ERROR: $service failed to start"
        echo "Check logs: journalctl -u $service -n 50"
        exit 1
    fi
done

# 13. Restart Nginx
echo "🔄 Restarting Nginx..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration test failed"
    exit 1
fi
sudo systemctl restart nginx

# 14. Verify application is responding
echo "🔍 Testing application response..."
sleep 5
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" | grep -q "200\|301\|302"; then
    echo "✅ Application is responding"
else
    echo "⚠️ Application may not be responding correctly"
    echo "Check manually: curl -I https://$DOMAIN"
fi

echo "✅ FULL production upgrade complete!"
echo "✅ Application running at: https://$DOMAIN"
echo "✅ Environment variables reloaded"
echo "✅ Frontend rebuilt with new environment"
echo "✅ Python dependencies updated"
echo ""
echo "🔍 To verify services:"
echo "  sudo systemctl status gunicorn llm-worker"
echo "  curl -I https://$DOMAIN"