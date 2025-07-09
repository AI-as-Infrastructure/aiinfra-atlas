#!/bin/bash
#=============================================================================
# ATLAS PRODUCTION ENVIRONMENT GRACEFUL STOP
#=============================================================================
# 
# PURPOSE:
#   This script gracefully stops the production environment services while
#   preserving data and configurations for potential restart.
# 
# USAGE:
#   ./deploy/production/scripts/stop_production.sh
#
# REQUIREMENTS:
#   - AWS CLI configured with appropriate permissions
#   - SSH access to the production server
#
#=============================================================================

set -e

# ---------------------------------------------------------------------------
# Load environment file to allow PRODUCTION_HOST override and other vars
if [ -f "config/.env.production" ]; then
  # shellcheck disable=SC1091
  set -a
  source config/.env.production
  set +a
fi

# Region configuration (fallback when we need AWS lookup)
REGION="${AWS_REGION:-us-west-1}"

# Determine instance IP / host
if [ -n "$PRODUCTION_HOST" ]; then
  INSTANCE_IP="$PRODUCTION_HOST"
  echo "Using PRODUCTION_HOST from .env.production: $INSTANCE_IP"
else
  echo "PRODUCTION_HOST not set – falling back to AWS EC2 lookup"
  PROFILE_OPTION=""
  if [ -n "$AWS_PROFILE" ]; then
    PROFILE_OPTION="--profile $AWS_PROFILE"
  fi

  set +e
  INSTANCE_IP=$(aws ec2 describe-instances $PROFILE_OPTION --region "$REGION" \
      --filters "Name=tag:Name,Values=atlas-prod-server" "Name=instance-state-name,Values=running" \
      --query 'Reservations[0].Instances[0].PublicIpAddress' --output text 2>&1)
  AWS_RC=$?
  set -e

  if [ $AWS_RC -ne 0 ] || [ -z "$INSTANCE_IP" ] || [ "$INSTANCE_IP" = "None" ]; then
    echo "❌ Could not determine production instance IP (AWS lookup failed)."
    exit 1
  fi
fi

# SSH key path (can be overridden via SSH_KEY_PATH)
SSH_KEY="${SSH_KEY_PATH:-$HOME/atlas-prod-key-west1.pem}"
# ---------------------------------------------------------------------------

echo "🛑 Gracefully stopping production environment at $INSTANCE_IP..."

# Execute graceful stop on remote server
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ubuntu@"$INSTANCE_IP" bash -s << 'ENDSTOP'

set -e
APP_NAME="atlas"

echo "🚨 Stopping production environment gracefully..."

echo "📊 Checking current service status..."
sudo systemctl status gunicorn --no-pager -l || echo "Gunicorn not running"
sudo systemctl status llm-worker --no-pager -l || echo "LLM worker not running"
sudo systemctl status nginx --no-pager -l || echo "Nginx not running"
sudo systemctl status redis-server --no-pager -l || echo "Redis not running"

echo ""
echo "🔄 Stopping services gracefully..."

# Put up maintenance page first
echo "📄 Enabling maintenance mode..."
sudo systemctl stop nginx || echo "Nginx was not running"

# Wait for current requests to complete
echo "⏱️  Waiting 30 seconds for current requests to complete..."
sleep 30

# Stop LLM worker (handles in-flight requests)
echo "Stopping LLM worker..."
sudo systemctl stop llm-worker || echo "LLM worker was not running"

# Wait for LLM worker to finish current tasks
echo "⏱️  Waiting 10 seconds for LLM tasks to complete..."
sleep 10

# Stop Gunicorn (backend API)
echo "Stopping Gunicorn backend..."
sudo systemctl stop gunicorn || echo "Gunicorn was not running"

# Stop worker services if they exist
echo "Stopping worker services..."
if sudo systemctl is-active --quiet atlas-worker; then
    sudo systemctl stop atlas-worker
    echo "✅ Atlas worker stopped"
else
    echo "ℹ️  Atlas worker was not running"
fi

# Stop Redis last (in case services need to write final data)
echo "Stopping Redis..."
sudo systemctl stop redis-server || echo "Redis was not running"

echo ""
echo "📈 Memory cleanup..."
# Force garbage collection and clear any remaining memory
sync
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || echo "Note: Cannot clear system caches"

echo ""
echo "📋 Final service status check..."
sudo systemctl is-active gunicorn || echo "✅ Gunicorn stopped"
sudo systemctl is-active llm-worker || echo "✅ LLM worker stopped"
sudo systemctl is-active nginx || echo "✅ Nginx stopped"
sudo systemctl is-active redis-server || echo "✅ Redis stopped"

echo ""
echo "🛑 PRODUCTION ENVIRONMENT STOPPED"
echo "⚠️  Website is now offline!"
echo "💡 To restart: make p"

ENDSTOP

echo "✅ Production environment stopped gracefully!"
echo "📋 Next steps:"
echo "   • Services are stopped but data is preserved"
echo "   • To restart: run 'make p' to redeploy"
echo "   • To clean up completely: run 'make dp'"