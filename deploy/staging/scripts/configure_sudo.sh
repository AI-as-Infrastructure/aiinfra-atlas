#!/bin/bash

# Create sudoers file for atlas_deploy
echo "atlas_deploy ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/atlas_deploy

# Set correct permissions
sudo chmod 440 /etc/sudoers.d/atlas_deploy

echo "✅ Passwordless sudo configured for atlas_deploy user" 