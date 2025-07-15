#!/bin/bash

# Simple production upgrade script - for server-side upgrades with rollback capability
# This script assumes you're running it directly on the production server

set -euo pipefail
trap 'echo "❌ Upgrade failed at line $LINENO"; exit 1' ERR

# Configuration
APP_NAME="atlas"
APP_DIR="/opt/atlas"
BACKUP_DIR="/opt/atlas_backup"
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

# 3. Remove old backup and create new one
echo "📦 Creating backup..."
sudo rm -rf "$BACKUP_DIR"
sudo cp -r "$APP_DIR" "$BACKUP_DIR"
echo "✅ Backup created at $BACKUP_DIR"

# 4. Update code
echo "🔄 Updating code..."
git stash push -m "Production upgrade stash $(date)" || true
git fetch origin
git reset --hard origin/$GIT_BRANCH
git lfs pull

# 5. Check if we need to rebuild frontend
FRONTEND_REBUILD=false
if [ -f "$BACKUP_DIR/frontend/package.json" ]; then
    if ! diff -q frontend/package.json "$BACKUP_DIR/frontend/package.json" >/dev/null 2>&1; then
        echo "📦 Frontend dependencies changed - rebuild required"
        FRONTEND_REBUILD=true
    fi
    if ! diff -q frontend/src "$BACKUP_DIR/frontend/src" >/dev/null 2>&1; then
        echo "📦 Frontend source changed - rebuild required"
        FRONTEND_REBUILD=true
    fi
else
    echo "📦 No previous frontend found - rebuild required"
    FRONTEND_REBUILD=true
fi

# 6. Rebuild frontend if needed
if [ "$FRONTEND_REBUILD" = true ]; then
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
else
    echo "✅ Frontend unchanged - skipping rebuild"
fi

# 7. Check if Python dependencies changed
if [ -f "$BACKUP_DIR/config/requirements.txt" ]; then
    if ! diff -q config/requirements.txt "$BACKUP_DIR/config/requirements.txt" >/dev/null 2>&1; then
        echo "📦 Python dependencies changed - updating..."
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r config/requirements.txt
    else
        echo "✅ Python dependencies unchanged"
    fi
else
    echo "📦 No previous requirements found - installing dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r config/requirements.txt
fi

# 8. Graceful service restart
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

# 9. Verify services are running
echo "🔍 Verifying services..."
sleep 5  # Give services time to start

ROLLBACK_NEEDED=false
for service in gunicorn llm-worker; do
    if ! sudo systemctl is-active --quiet $service; then
        echo "❌ ERROR: $service failed to start"
        ROLLBACK_NEEDED=true
        break
    fi
done

if [ "$ROLLBACK_NEEDED" = true ]; then
    echo "🔄 Attempting rollback..."
    
    # Stop current services
    sudo systemctl stop gunicorn llm-worker || true
    
    # Restore backup
    sudo rm -rf "$APP_DIR"
    sudo mv "$BACKUP_DIR" "$APP_DIR"
    
    # Start services with backup
    sudo systemctl start gunicorn llm-worker
    
    # Verify rollback worked
    sleep 5
    if sudo systemctl is-active --quiet gunicorn && sudo systemctl is-active --quiet llm-worker; then
        echo "✅ Rollback successful - services restored"
        echo "Check logs for upgrade failure: journalctl -u gunicorn -n 50"
        exit 1
    else
        echo "❌ Rollback failed - manual intervention required"
        echo "Check logs: journalctl -u gunicorn -n 50"
        echo "Check logs: journalctl -u llm-worker -n 50"
        exit 1
    fi
fi

# 10. Restart Nginx
echo "🔄 Restarting Nginx..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration test failed"
    exit 1
fi
sudo systemctl reload nginx

# 11. Verify application is responding
echo "🔍 Testing application response..."
sleep 2
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" | grep -q "200\|301\|302"; then
    echo "✅ Application is responding"
else
    echo "⚠️ Application may not be responding correctly"
    echo "Check manually: curl -I https://$DOMAIN"
fi

# 12. Cleanup - remove backup since upgrade was successful
echo "🧹 Cleaning up successful upgrade..."
sudo rm -rf "$BACKUP_DIR"

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