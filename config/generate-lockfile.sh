#!/bin/bash
set -e

# Setup proper directory paths
SCRIPT_DIR="$(dirname \"$(readlink -f \"$0\")\")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Move to project root for operations
cd "$PROJECT_ROOT"

# Load Environment Variables from the config directory
if [ -f "$PROJECT_ROOT/config/.env.development" ]; then
    set -a
    source "$PROJECT_ROOT/config/.env.development"
    set +a
else
    echo "Error: config/.env.development file not found!"
    exit 1
fi

# Set Python version and binary (use Python 3.10 as default if not specified in .env)
PYTHON_VERSION=${PYTHON_VERSION:-3.10}
PYTHON_BINARY="python${PYTHON_VERSION}"

# Use a temp venv to avoid polluting the main one
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