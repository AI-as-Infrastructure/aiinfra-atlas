#!/bin/bash
set -e

# Setup proper directory paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"  # Go up two levels from deploy/dev

# Move to project root for operations
cd "$PROJECT_ROOT"

# Load Environment Variables from the config directory
if [ -f "$PROJECT_ROOT/config/.env" ]; then
    set -a
    source "$PROJECT_ROOT/config/.env"
    set +a
else
    echo "Error: config/.env file not found!"
    exit 1
fi

# Set Python version and binary (use Python 3.10 as default if not specified in .env)
PYTHON_VERSION=${PYTHON_VERSION:-3.10}
PYTHON_BINARY=${PYTHON_BINARY:-python$PYTHON_VERSION}

echo "Creating a fresh virtual environment with Python ${PYTHON_VERSION} for generating lockfile..."
rm -rf .venv_temp || true
${PYTHON_BINARY} -m venv .venv_temp

echo "Installing dependencies from config/requirements.txt..."
.venv_temp/bin/pip install --upgrade pip
.venv_temp/bin/pip install -r "$PROJECT_ROOT/config/requirements.txt"

echo "Generating comprehensive lock file with all dependencies..."
.venv_temp/bin/pip freeze > "$PROJECT_ROOT/config/requirements.lock"

echo "Cleaning up temporary environment..."
rm -rf .venv_temp

echo "Requirements lock file generated successfully!"
echo "Your development and staging environments will now use identical dependencies."
