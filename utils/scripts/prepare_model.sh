#!/bin/bash

# Model preparation script
set -e

# Hardcode the environment for development
export ENVIRONMENT=development
echo "Using ENVIRONMENT=$ENVIRONMENT"

echo "🔍 Checking environment..."

# Check if config directory exists
if [ ! -d "config" ]; then
    echo "❌ Error: config directory not found!"
    exit 1
fi

# Check if environment file exists
if [ ! -f "config/.env.development" ]; then
    echo "❌ Error: config/.env.development not found!"
    echo "💡 Please create config/.env.development with your environment variables"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found!"
    echo "💡 This file is required for dependency management"
    exit 1
fi

# Install dependencies
echo "📥 Installing dependencies..."
# Install dependencies based on GPU availability
if command -v nvidia-smi &>/dev/null; then
    echo "GPU detected - installing GPU variant"
    pip install -e ".[cuda121]"  # Adjust variant as needed
else
    echo "No GPU detected - installing CPU variant"
    pip install -e ".[cpu]" --extra-index-url https://download.pytorch.org/whl/cpu
fi

# Check if prepare script exists
if [ ! -f "utils/scripts/prepare_model.py" ]; then
    echo "❌ Error: utils/scripts/prepare_model.py not found!"
    exit 1
fi

# Prepare model
echo "🔨 Preparing embedding model..."
python utils/scripts/prepare_model.py

echo "✅ Model prepared successfully!"
echo "💡 The model is now ready for use with ATLAS" 