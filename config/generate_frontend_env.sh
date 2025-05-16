#!/bin/bash
# generate_frontend_env.sh
# Script to generate Vue frontend environment file with only the necessary variables

set -e

# Get environment from argument or default to development
ENV=${1:-development}

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up Vue frontend environment...${NC}"

# Setup proper directory paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"  
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"  # Go up one level from config

# Define paths - get environment-specific .env file if available
BASE_ENV_FILE="$SCRIPT_DIR/.env"
ENV_SPECIFIC_FILE="$SCRIPT_DIR/.env.$ENV"
FRONTEND_ENV_FILE="$PROJECT_ROOT/frontend/.env"

# Check if environment-specific config file exists, otherwise fall back to default
if [ -f "$ENV_SPECIFIC_FILE" ]; then
    echo "Using environment-specific config file: $ENV_SPECIFIC_FILE"
    ENV_FILE="$ENV_SPECIFIC_FILE"
elif [ -f "$BASE_ENV_FILE" ]; then
    echo "Using default config file: $BASE_ENV_FILE"
    ENV_FILE="$BASE_ENV_FILE"
else
    echo "Error: Neither $ENV_SPECIFIC_FILE nor $BASE_ENV_FILE found!"
    exit 1
fi

# Create frontend environment file
echo "Creating frontend environment file..."

# Start with a clean file
> "$FRONTEND_ENV_FILE"

# Add Vue variables from .env file
echo "Adding VITE_ variables..."
while IFS= read -r line; do
    if [[ -n "$line" ]]; then
        echo "$line" >> "$FRONTEND_ENV_FILE"
    fi
done < <(grep "^VITE_" "$ENV_FILE" || true)

# Add ATLAS_VERSION and LAST_MODIFIED with VITE_ prefix
echo "Adding version information..."
if grep -q '^ATLAS_VERSION=' "$ENV_FILE"; then
    ATLAS_VERSION=$(grep '^ATLAS_VERSION=' "$ENV_FILE" | cut -d= -f2 | tr -d '"')
    echo "VITE_ATLAS_VERSION=$ATLAS_VERSION" >> "$FRONTEND_ENV_FILE"
    echo "Added ATLAS_VERSION: $ATLAS_VERSION"
else
    echo -e "${YELLOW}Warning: ATLAS_VERSION not found in $ENV_FILE${NC}"
fi

if grep -q '^LAST_MODIFIED=' "$ENV_FILE"; then
    LAST_MODIFIED=$(grep '^LAST_MODIFIED=' "$ENV_FILE" | cut -d= -f2 | tr -d '"')
    echo "VITE_LAST_MODIFIED=$LAST_MODIFIED" >> "$FRONTEND_ENV_FILE"
    echo "Added LAST_MODIFIED: $LAST_MODIFIED"
else
    echo -e "${YELLOW}Warning: LAST_MODIFIED not found in $ENV_FILE${NC}"
fi

# Set proper permissions
chmod 644 "$FRONTEND_ENV_FILE"

echo -e "${GREEN}Frontend environment file created successfully at $FRONTEND_ENV_FILE${NC}"