#!/bin/bash
# Quick start backend without rebuilding environment
# Assumes dependencies are already installed

cd "$(dirname "$0")"

echo "Starting backend directly (no rebuild)..."

# Set the environment
export ENVIRONMENT=development

# Source the development environment properly
if [ -f config/.env.development ]; then
    set -a  # automatically export all variables
    source config/.env.development
    set +a  # turn off automatic export
fi

# Start the backend using existing Python
if [ -f .venv/bin/python ]; then
    echo "Using .venv Python..."
    .venv/bin/python -m uvicorn backend.app:app --reload --port 8000 --host 0.0.0.0
elif command -v python3 &> /dev/null; then
    echo "Using system Python3..."
    python3 -m uvicorn backend.app:app --reload --port 8000 --host 0.0.0.0
else
    echo "No Python found!"
    exit 1
fi