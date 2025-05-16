#!/bin/bash
# start-with-env.sh
# Script to start the React frontend development server with environment variables from config files

set -e

# Setup proper directory paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"  # Go up one level from frontend

# Define paths
SETUP_ENV_SCRIPT="$PROJECT_ROOT/config/setup_react_env.sh"

# Check if setup script exists
if [ ! -f "$SETUP_ENV_SCRIPT" ]; then
    echo "Error: $SETUP_ENV_SCRIPT not found!"
    exit 1
fi

# Generate the frontend environment file
echo "Setting up React environment variables..."
"$SETUP_ENV_SCRIPT"

# Start the React development server
echo "Starting React development server..."
PORT=3001 npm start

echo "Frontend development server stopped."
