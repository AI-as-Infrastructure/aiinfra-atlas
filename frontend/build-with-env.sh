#!/bin/bash
# build-with-env.sh
# Script to build the React frontend with environment variables from config files

set -e

# Setup proper directory paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"  # Go up one level from frontend

# Define paths
SETUP_ENV_SCRIPT="$PROJECT_ROOT/config/setup_react_env.sh"

# Cleanup function to remove the temporary .env file upon exit
cleanup() {
    rm -f "$SCRIPT_DIR/.env" || true
    echo "Cleaned up temporary environment files"
}
trap cleanup EXIT

# Check if setup script exists
if [ ! -f "$SETUP_ENV_SCRIPT" ]; then
    echo "Error: $SETUP_ENV_SCRIPT not found!"
    exit 1
fi

# Generate the frontend environment file
echo "Setting up React environment variables..."
"$SETUP_ENV_SCRIPT"

# Build the React application
echo "Building React application..."
npm run build

echo "Frontend build completed successfully!"
