#!/bin/bash

# Get environment from ATLAS_ENV - no fallback, must be explicitly set
if [ -z "$ATLAS_ENV" ]; then
    echo "ERROR: ATLAS_ENV environment variable is not set"
    echo "Please set ATLAS_ENV to 'development', 'staging', or 'production' in your deployment script"
    exit 1
fi

ENVIRONMENT=$ATLAS_ENV
echo "Using environment: $ENVIRONMENT (from ATLAS_ENV)"

# Get the script's directory to use as base for relative paths
SCRIPT_DIR=$(dirname "$(realpath "$0")")

echo "Script directory: $SCRIPT_DIR"

# Define source and destination paths based on environment
ENV_TEMPLATE="$SCRIPT_DIR/.env.$ENVIRONMENT"
FRONTEND_ENV="$SCRIPT_DIR/../frontend/.env"
LOGOUT_TEMPLATE="$SCRIPT_DIR/../frontend/public/logout.template.html"
LOGOUT_HTML="$SCRIPT_DIR/../frontend/public/logout.html"

# Debug output
echo "Environment file path: $ENV_TEMPLATE"
echo "Frontend env path: $FRONTEND_ENV"
echo "Logout template path: $LOGOUT_TEMPLATE"

# Check if the environment file exists
if [ ! -f "$ENV_TEMPLATE" ]; then
    echo "Error: Environment file $ENV_TEMPLATE not found"
    # List contents of script directory for debugging
    echo "Contents of $SCRIPT_DIR:"
    ls -la "$SCRIPT_DIR/"
    exit 1
fi

# Get the VITE_API_URL from the environment template
VITE_API_URL=$(grep "VITE_API_URL" $ENV_TEMPLATE | cut -d "=" -f2)

# Generate frontend/.env file - only extract VITE_ variables
echo "Generating frontend environment file from $ENV_TEMPLATE..."
grep -E '^VITE_' $ENV_TEMPLATE > $FRONTEND_ENV
echo "Extracted only VITE_ prefixed variables to frontend/.env"

# Generate logout.html from template
echo "Generating logout.html with API URL: $VITE_API_URL"
if [ -f "$LOGOUT_TEMPLATE" ]; then
    sed "s|__VITE_API_URL__|$VITE_API_URL|g" $LOGOUT_TEMPLATE > $LOGOUT_HTML
    echo "Logout page generated successfully."
else
    echo "Error: Logout template file not found at $LOGOUT_TEMPLATE"
    exit 1
fi

echo "Frontend files generation complete for $ENVIRONMENT environment." 