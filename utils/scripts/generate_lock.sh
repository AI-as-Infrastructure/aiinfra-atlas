#!/bin/bash

# Requirements lock file generation script
set -e

echo "🔍 Checking virtual environment..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install pip-tools
echo "📥 Installing pip-tools..."
pip install pip-tools

# Check if requirements.txt exists
if [ ! -f "config/requirements.txt" ]; then
    echo "❌ Error: config/requirements.txt not found!"
    exit 1
fi

# Generate lock file
echo "🔒 Generating requirements.lock file..."
echo "📝 Using config/requirements.txt as input..."
pip-compile --verbose config/requirements.txt -o config/requirements.lock

if [ $? -eq 0 ]; then
    echo "✅ Lock file generated successfully at config/requirements.lock"
    echo "⚠️  WARNING: This file is machine-specific."
else
    echo "❌ Error: Failed to generate lock file"
    exit 1
fi 