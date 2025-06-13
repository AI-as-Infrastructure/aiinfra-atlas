#!/bin/bash

# Production cleanup script
set -e

# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=atlas-prod" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

if [ -z "$INSTANCE_IP" ]; then
    echo "Error: Could not find production instance"
    exit 1
fi

# Confirm cleanup
read -p "Are you sure you want to clean the production application? This will remove all data! (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled"
    exit 1
fi

# Clean up application
echo "Cleaning up production application..."
ssh ubuntu@${INSTANCE_IP} 'cd /home/ubuntu/atlas && \
    sudo systemctl stop atlas-backend && \
    sudo systemctl stop atlas-frontend && \
    sudo rm -rf /home/ubuntu/atlas/* && \
    sudo rm -f /etc/systemd/system/atlas-*.service && \
    sudo systemctl daemon-reload'

echo "Cleanup complete!" 