#!/bin/bash
# test_env_integration.sh
# Script to test the integration of the secrets management system with the frontend

set -e

# Setup proper directory paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"  # Go up one level from tests
PROJECT_ROOT="$(dirname "$FRONTEND_DIR")"  # Go up one level from frontend

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing frontend environment integration...${NC}"

# Check if setup_react_env.sh exists
if [ ! -f "$PROJECT_ROOT/config/setup_react_env.sh" ]; then
    echo -e "${RED}Error: setup_react_env.sh not found!${NC}"
    exit 1
fi

# Run the setup script
echo -e "${YELLOW}Running setup_react_env.sh...${NC}"
"$PROJECT_ROOT/config/setup_react_env.sh"

# Check if .env file was created
if [ ! -f "$FRONTEND_DIR/.env" ]; then
    echo -e "${RED}Error: Frontend .env file was not created!${NC}"
    exit 1
fi

# Check if required React environment variables are present
echo -e "${YELLOW}Checking for required React environment variables...${NC}"
REQUIRED_VARS=(
    "REACT_APP_SITE_TITLE"
    "REACT_APP_CLIENT_ID"
    "REACT_APP_ISSUER_URL"
    "REACT_APP_REDIRECT_URI"
    "REACT_APP_LOGOUT_URL"
    "REACT_APP_OAUTH_SCOPE"
    "REACT_APP_FRONTEND_URL"
)

MISSING_VARS=0
for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^$VAR=" "$FRONTEND_DIR/.env"; then
        echo -e "${RED}Missing required variable: $VAR${NC}"
        MISSING_VARS=$((MISSING_VARS+1))
    else
        echo -e "${GREEN}Found $VAR${NC}"
    fi
done

# Check for direct references to process.env in JavaScript files
echo -e "${YELLOW}Checking for direct references to process.env in JavaScript files...${NC}"
DIRECT_REFS=$(grep -l "process\.env\.REACT_APP_" --include="*.js" --exclude="envConfig.js" -r "$FRONTEND_DIR/src" 2>/dev/null || echo "")

if [ -n "$DIRECT_REFS" ]; then
    echo -e "${RED}Warning: Found direct references to process.env in:${NC}"
    echo "$DIRECT_REFS"
    echo -e "${YELLOW}These should be updated to use the envConfig utility.${NC}"
else
    echo -e "${GREEN}No direct references to process.env found. All files are using the envConfig utility.${NC}"
fi

# Clean up
echo -e "${YELLOW}Cleaning up...${NC}"
rm -f "$FRONTEND_DIR/.env"

# Final result
if [ $MISSING_VARS -eq 0 ] && [ -z "$DIRECT_REFS" ]; then
    echo -e "${GREEN}Frontend environment integration test passed!${NC}"
    exit 0
else
    echo -e "${RED}Frontend environment integration test failed!${NC}"
    exit 1
fi
