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

# Get production instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=atlas-prod" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].PrivateIpAddress' \
    --output text)

if [ -z "$INSTANCE_IP" ]; then
    echo "❌ Could not find production instance IP"
    exit 1
fi

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
aws sso login --profile atlas-prod
aws ssm start-session --target i-$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=atlas-prod" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text) \
    --document-name AWS-StartInteractiveCommand \
    --parameters command="
    echo 'Stopping and removing services...'
    
    # Stop and disable Gunicorn
    echo 'Stopping Gunicorn...'
    sudo systemctl stop gunicorn || true
    sudo systemctl disable gunicorn || true
    sudo rm -f /etc/systemd/system/gunicorn.service
    sudo systemctl daemon-reload
    
    # Stop and disable Nginx
    echo 'Stopping Nginx...'
    sudo systemctl stop nginx || true
    sudo systemctl disable nginx || true
    sudo rm -f /etc/nginx/sites-enabled/$APP_NAME
    sudo rm -f /etc/nginx/sites-available/$APP_NAME
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Stop and disable Redis
    echo 'Stopping Redis...'
    sudo systemctl stop redis-server || true
    sudo systemctl disable redis-server || true
    
    # Kill any remaining processes
    echo 'Killing any remaining processes...'
    sudo pkill -f gunicorn || true
    sudo pkill -f 'python.*atlas' || true
    
    # Verify services are stopped
    echo 'Verifying services are stopped...'
    if systemctl is-active --quiet gunicorn; then
        echo 'WARNING: Gunicorn is still running, forcing stop...'
        sudo systemctl stop gunicorn
    fi
    if systemctl is-active --quiet nginx; then
        echo 'WARNING: Nginx is still running, forcing stop...'
        sudo systemctl stop nginx
    fi
    if systemctl is-active --quiet redis-server; then
        echo 'WARNING: Redis is still running, forcing stop...'
        sudo systemctl stop redis-server
    fi
    
    echo 'Removing application files...'
    # Force remove the application directory and all its contents
    sudo rm -rf /opt/atlas
    # Double check and force remove if it still exists
    if [ -d '/opt/atlas' ]; then
        echo 'Force removing /opt/atlas directory...'
        sudo chattr -i /opt/atlas 2>/dev/null || true
        sudo rm -rf /opt/atlas
    fi
    
    echo 'Removing logs...'
    sudo rm -rf /var/log/$APP_NAME
    
    echo 'Reloading systemd...'
    sudo systemctl daemon-reload
    
    # Final verification
    echo 'Performing final verification...'
    if [ -d '/opt/atlas' ]; then
        echo 'ERROR: /opt/atlas directory still exists!'
        exit 1
    fi
    if systemctl is-active --quiet gunicorn; then
        echo 'ERROR: Gunicorn service is still running!'
        exit 1
    fi
    if systemctl is-active --quiet redis-server; then
        echo 'ERROR: Redis service is still running!'
        exit 1
    fi
    
    echo '✅ Cleanup complete!'
    " --profile atlas-prod

echo "✅ Production environment cleaned up successfully!" 