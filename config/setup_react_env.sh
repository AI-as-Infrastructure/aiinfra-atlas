#!/bin/bash
# setup_react_env.sh
# Script to generate React environment file from config files
# This script is used by dev.sh and build processes to create the frontend .env file

set -e

# Get environment from argument or default to dev
ENV=${1:-dev}

# Convert environment to uppercase using portable method
ENV_UPPER=$(echo "$ENV" | tr '[:lower:]' '[:upper:]')

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up React environment for: ${ENV}${NC}"

# Setup proper directory paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"  # Go up one level from config

# Define paths
ENV_FILE="$SCRIPT_DIR/.env"
SECRETS_FILE="$SCRIPT_DIR/.secrets"
FRONTEND_ENV_FILE="$PROJECT_ROOT/frontend/.env"

# Check if config files exist
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE file not found!"
    exit 1
fi

if [ ! -f "$SECRETS_FILE" ]; then
    echo "Error: $SECRETS_FILE file not found!"
    exit 1
fi

# Create frontend environment file
echo "Creating frontend environment file from config files..."

# Start with a clean file
> "$FRONTEND_ENV_FILE"

# Add React app variables from .env file
echo "Adding React variables from $ENV_FILE..."
while IFS= read -r line; do
    if [[ -n "$line" ]]; then
        echo "$line" >> "$FRONTEND_ENV_FILE"
    fi
done < <(grep "^REACT_APP_" "$ENV_FILE" || true)
echo "Found $(grep -c "^REACT_APP_" "$ENV_FILE" || echo 0) REACT_APP_ variables in $ENV_FILE"

# Add React app variables from .secrets file
echo "Adding React variables from $SECRETS_FILE..."
while IFS= read -r line; do
    if [[ -n "$line" ]]; then
        echo "$line" >> "$FRONTEND_ENV_FILE"
    fi
done < <(grep "^REACT_APP_" "$SECRETS_FILE" || true)
echo "Found $(grep -c "^REACT_APP_" "$SECRETS_FILE" || echo 0) REACT_APP_ variables in $SECRETS_FILE"

# Check for specific auth variables
echo "Checking for authentication variables..."
if grep -q "^REACT_APP_ISSUER_URL=" "$FRONTEND_ENV_FILE"; then
    echo "✅ REACT_APP_ISSUER_URL found in frontend .env"
else
    echo "❌ REACT_APP_ISSUER_URL not found in frontend .env"
fi

if grep -q "^REACT_APP_CLIENT_ID=" "$FRONTEND_ENV_FILE"; then
    echo "✅ REACT_APP_CLIENT_ID found in frontend .env"
else
    echo "❌ REACT_APP_CLIENT_ID not found in frontend .env"
fi

# Add environment-specific Redis password
REDIS_VAR="REDIS_${ENV_UPPER}_PASSWORD"
REDIS_PASSWORD=$(grep "^$REDIS_VAR=" "$SECRETS_FILE" | cut -d= -f2 | tr -d '"')

if [ -n "$REDIS_PASSWORD" ]; then
    echo "Adding environment-specific Redis password for $ENV environment..."
    echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> "$FRONTEND_ENV_FILE"
else
    echo -e "${YELLOW}Warning: $REDIS_VAR not found in $SECRETS_FILE${NC}"
fi

# Add environment-specific Phoenix project name
PHOENIX_VAR="PHOENIX_PROJECT_NAME_${ENV_UPPER}"
PHOENIX_PROJECT_NAME=$(grep "^$PHOENIX_VAR=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')

if [ -n "$PHOENIX_PROJECT_NAME" ]; then
    echo "Adding environment-specific Phoenix project name for $ENV environment..."
    echo "PHOENIX_PROJECT_NAME=$PHOENIX_PROJECT_NAME" >> "$FRONTEND_ENV_FILE"
else
    # If the environment-specific variable is not found, use the default PHOENIX_PROJECT_NAME
    DEFAULT_PHOENIX=$(grep "^PHOENIX_PROJECT_NAME=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
    if [ -n "$DEFAULT_PHOENIX" ]; then
        echo "Using default PHOENIX_PROJECT_NAME from $ENV_FILE..."
        echo "PHOENIX_PROJECT_NAME=$DEFAULT_PHOENIX" >> "$FRONTEND_ENV_FILE"
    else
        # Default fallback values based on environment
        case "$ENV" in
            dev)
                DEFAULT_VALUE="ATLAS-Hansard-Dev"
                ;;
            staging)
                DEFAULT_VALUE="ATLAS-Hansard-Staging"
                ;;
            prod)
                DEFAULT_VALUE="ATLAS-Hansard-Prod"
                ;;
            *)
                DEFAULT_VALUE="ATLAS-Hansard"
                ;;
        esac
        echo -e "${YELLOW}Warning: No Phoenix project name found in $ENV_FILE. Using default: $DEFAULT_VALUE${NC}"
        echo "PHOENIX_PROJECT_NAME=$DEFAULT_VALUE" >> "$FRONTEND_ENV_FILE"
    fi
fi

# Set proper permissions
chmod 644 "$FRONTEND_ENV_FILE"

echo -e "${GREEN}Frontend environment file created successfully at $FRONTEND_ENV_FILE${NC}"