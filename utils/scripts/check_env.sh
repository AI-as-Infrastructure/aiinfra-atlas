#!/bin/bash

# Python environment check script
set -e

# Get Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
RECOMMENDED_VERSION="3.11.5"

echo "Python Environment Check"
echo "======================"
echo "Recommended Python version: $RECOMMENDED_VERSION"
echo "Current Python version: $PYTHON_VERSION"

# Check virtual environment
if [ -d ".venv" ]; then
    echo "Virtual environment: Found"
else
    echo "Virtual environment: Not found"
fi

# Check for potential issues
if [ "$PYTHON_VERSION" != "$RECOMMENDED_VERSION" ]; then
    echo ""
    echo "WARNING: Python version mismatch!"
    echo "The recommended version is $RECOMMENDED_VERSION"
    echo "You are using $PYTHON_VERSION"
    echo "This may cause compatibility issues."
fi

# Check for required packages
echo ""
echo "Checking required packages..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
    pip list | grep -E "fastapi|uvicorn|torch|transformers" || true
fi 