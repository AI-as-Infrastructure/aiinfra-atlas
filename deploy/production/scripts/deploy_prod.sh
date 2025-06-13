#!/bin/bash

# Production deployment script
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

# Build frontend
echo "Building frontend..."
cd frontend
npm run build
cd ..

# Deploy to production
echo "Deploying to production..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'node_modules' \
    --exclude 'frontend/node_modules' \
    --exclude 'frontend/dist' \
    ./ ubuntu@${INSTANCE_IP}:/home/ubuntu/atlas/

# Restart services
echo "Restarting services..."
ssh ubuntu@${INSTANCE_IP} 'cd /home/ubuntu/atlas && \
    sudo systemctl restart atlas-backend && \
    sudo systemctl restart atlas-frontend'

echo "Deployment complete!" 