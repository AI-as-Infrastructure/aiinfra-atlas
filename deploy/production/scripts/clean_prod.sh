#!/bin/bash
#=============================================================================
# ATLAS PRODUCTION ENVIRONMENT CLEANUP
#=============================================================================
# 
# PURPOSE:
#   This script completely removes the production environment, including all
#   services, files, and configurations.
# 
# USAGE:
#   ./deploy/production/scripts/clean_prod.sh
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

# Confirm with user
echo "🧹 This will completely remove the production environment at $INSTANCE_IP"
echo "⚠️  This action cannot be undone!"
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

# Execute cleanup on remote server using AWS SSO
echo "Connecting to $INSTANCE_IP via SSH to perform cleanup..."

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ubuntu@"$INSTANCE_IP" bash -s << 'ENDCLEAN'

set -e
APP_NAME="atlas"

echo 'Stopping and removing services...'
# Stop and disable Gunicorn
sudo systemctl stop gunicorn || true
sudo systemctl disable gunicorn || true
sudo rm -f /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload

# Stop and disable Nginx
sudo systemctl stop nginx || true
sudo systemctl disable nginx || true

# Stop and disable Redis
sudo systemctl stop redis-server || true
sudo systemctl disable redis-server || true

# Remove application directory
sudo rm -rf /home/ubuntu/atlas /opt/atlas

# Remove logs
sudo rm -rf /var/log/atlas

echo 'Reloading systemd...'
sudo systemctl daemon-reload

echo '✅ Remote cleanup complete'

ENDCLEAN

echo "✅ Production environment cleaned up successfully!" 