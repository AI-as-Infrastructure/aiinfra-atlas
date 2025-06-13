#!/bin/bash

# Staging deployment script
set -e

# Check required environment variables
if [ -z "$STAGING_IP" ] || [ -z "$STAGING_USER" ]; then
    echo "Error: STAGING_IP and STAGING_USER environment variables must be set"
    exit 1
fi

# Build frontend
echo "Building frontend..."
cd frontend
npm run build
cd ..

# Deploy to staging
echo "Deploying to staging..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'node_modules' \
    --exclude 'frontend/node_modules' \
    --exclude 'frontend/dist' \
    ./ ${STAGING_USER}@${STAGING_IP}:/home/${STAGING_USER}/atlas/

# Restart services
echo "Restarting services..."
ssh ${STAGING_USER}@${STAGING_IP} 'cd /home/${STAGING_USER}/atlas && \
    sudo systemctl restart atlas-backend && \
    sudo systemctl restart atlas-frontend'

echo "Deployment complete!" 