#!/bin/bash
# Script to run integration tests for the ATLAS backend

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source the environment variables
echo -e "${YELLOW}Loading environment variables...${NC}"
if [ -f "$PROJECT_ROOT/config/.env" ]; then
    source "$PROJECT_ROOT/config/.env"
    echo -e "${GREEN}Environment variables loaded from $PROJECT_ROOT/config/.env${NC}"
else
    echo -e "${RED}Error: $PROJECT_ROOT/config/.env not found${NC}"
    exit 1
fi

# Check if Python 3.10 is available
PYTHON_BIN="${PYTHON_BIN:-python3.10}"
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo -e "${RED}Error: $PYTHON_BIN not found. Make sure Python 3.10 is installed.${NC}"
    exit 1
fi

# Create a virtual environment if it doesn't exist
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON_BIN -m venv "$VENV_DIR"
    echo -e "${GREEN}Virtual environment created at $VENV_DIR${NC}"
fi

# Activate the virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}Virtual environment activated${NC}"

# Install dependencies if requirements.lock exists
if [ -f "$PROJECT_ROOT/config/requirements.lock" ]; then
    echo -e "${YELLOW}Installing dependencies from requirements.lock...${NC}"
    pip install -r "$PROJECT_ROOT/config/requirements.lock"
    echo -e "${GREEN}Dependencies installed${NC}"
else
    echo -e "${RED}Warning: $PROJECT_ROOT/config/requirements.lock not found${NC}"
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r "$PROJECT_ROOT/config/requirements.txt"
    echo -e "${GREEN}Dependencies installed${NC}"
fi

# Run the integration tests
echo -e "${YELLOW}Running integration tests...${NC}"
cd "$SCRIPT_DIR"
python -m tests.test_secrets_integration

# Check the exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Integration tests passed!${NC}"
else
    echo -e "${RED}Integration tests failed!${NC}"
    exit 1
fi

# Deactivate the virtual environment
deactivate
echo -e "${GREEN}Virtual environment deactivated${NC}"

echo -e "${GREEN}All tests completed successfully!${NC}"
