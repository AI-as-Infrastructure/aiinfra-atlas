#!/bin/bash

# Staging cleanup script
set -e

# Check required environment variables
if [ -z "$STAGING_IP" ] || [ -z "$STAGING_USER" ]; then
    echo "Error: STAGING_IP and STAGING_USER environment variables must be set"
    exit 1
fi

# Confirm cleanup
read -p "Are you sure you want to clean the staging application? This will remove all data! (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled"
    exit 1
fi

# Clean up application
echo "Cleaning up staging application..."
ssh ${STAGING_USER}@${STAGING_IP} 'cd /home/${STAGING_USER}/atlas && \
    sudo systemctl stop atlas-backend && \
    sudo systemctl stop atlas-frontend && \
    sudo rm -rf /home/${STAGING_USER}/atlas/* && \
    sudo rm -f /etc/systemd/system/atlas-*.service && \
    sudo systemctl daemon-reload'

echo "Cleanup complete!" 