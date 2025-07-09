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

echo "🔄 Gracefully stopping production services..."

# Stop Gunicorn first (application layer)
echo "Stopping Gunicorn (application server)..."
if sudo systemctl is-active --quiet gunicorn; then
    sudo systemctl stop gunicorn
    echo "✅ Gunicorn stopped"
else
    echo "ℹ️  Gunicorn was not running"
fi

# Stop Nginx next (reverse proxy)
echo "Stopping Nginx (reverse proxy)..."
if sudo systemctl is-active --quiet nginx; then
    sudo systemctl stop nginx
    echo "✅ Nginx stopped"
else
    echo "ℹ️  Nginx was not running"
fi

# Stop worker services if they exist
echo "Stopping worker services..."
if sudo systemctl is-active --quiet atlas-worker; then
    sudo systemctl stop atlas-worker
    echo "✅ Atlas worker stopped"
else
    echo "ℹ️  Atlas worker was not running"
fi

# Keep Redis running for data persistence unless explicitly requested
echo "ℹ️  Keeping Redis running for data persistence"
echo "   To stop Redis manually: sudo systemctl stop redis-server"

# Clear any temporary files but preserve logs
echo "Cleaning temporary files..."
sudo rm -f /tmp/gunicorn* /tmp/atlas* || true

echo "✅ Production services stopped gracefully"
echo "📊 Data and logs preserved for restart"
echo "🔄 To restart: make p (redeploy) or manually start services"

ENDSTOP

echo "✅ Production environment stopped gracefully!"
echo "📋 Next steps:"
echo "   • Services are stopped but data is preserved"
echo "   • To restart: run 'make p' to redeploy"
echo "   • To clean up completely: run 'make dp'"