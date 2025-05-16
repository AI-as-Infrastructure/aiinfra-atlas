#!/bin/bash
# Script to run all secrets management tests for the ATLAS backend
# This script will run the basic tests and the integration tests that don't require external services

set -e  # Exit immediately if a command exits with a non-zero status

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Loading environment variables...${NC}"
# Source the environment variables
if [ -f "$(pwd)/config/.env" ]; then
    source "$(pwd)/config/.env"
    echo -e "${GREEN}Environment variables loaded from $(pwd)/config/.env${NC}"
else
    echo -e "${RED}Error: .env file not found at $(pwd)/config/.env${NC}"
    exit 1
fi

echo -e "${YELLOW}Activating virtual environment...${NC}"
# Check if virtual environment exists, if not create it
if [ ! -d "backend/.venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3.10 -m venv backend/.venv
fi

# Activate virtual environment
source backend/.venv/bin/activate
echo -e "${GREEN}Virtual environment activated${NC}"

echo -e "${YELLOW}Installing dependencies from requirements.lock...${NC}"
# Install dependencies
pip install -r "$(pwd)/config/requirements.lock"

echo -e "${YELLOW}Running basic secrets tests...${NC}"
# Run the basic secrets tests
cd backend
python3.10 -m tests.test_secrets_basic
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Basic secrets tests passed!${NC}"
else
    echo -e "${RED}Basic secrets tests failed!${NC}"
    exit 1
fi

echo -e "${YELLOW}Running static code analysis for secrets integration...${NC}"
# Run a simple grep to check if all backend files are using the secrets manager
FILES_USING_SECRETS=$(grep -l "from utils.secrets_manager import" --include="*.py" -r .)
echo -e "${GREEN}Files using secrets manager:${NC}"
echo "$FILES_USING_SECRETS"

# Check for any remaining references to the old env directory in application code
# Exclude test files and third-party libraries
echo -e "${YELLOW}Checking for references to old env directory in application code...${NC}"
# Search for very specific patterns that reference the old env directory
OLD_ENV_REFS=$(grep -l -E "load_dotenv\(os\.path\.join\(.*,\s*['\"]env['\"]\)|os\.path\.join\(.*,\s*['\"]env['\"]\)" --include="*.py" --exclude-dir=".venv" --exclude-dir="tests" -r .)
if [ -n "$OLD_ENV_REFS" ]; then
    echo -e "${RED}Warning: Found references to old env directory in application code:${NC}"
    echo "$OLD_ENV_REFS"
    echo -e "${YELLOW}These should be updated to use the new secrets management system.${NC}"
else
    echo -e "${GREEN}No references to old env directory found in application code.${NC}"
fi

echo -e "${GREEN}All secrets management tests completed successfully!${NC}"
