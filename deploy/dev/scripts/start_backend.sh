#!/bin/bash
set -e

# Backend development startup script
echo "🔍 Checking backend environment..."

# Set environment
export ENVIRONMENT=development

# Regenerate frontend environment variables to ensure consistency
echo "📝 Regenerating frontend environment variables..."
if [ -f "config/generate_vue_files.sh" ]; then
    bash config/generate_vue_files.sh
else
    echo "⚠️  Warning: config/generate_vue_files.sh not found - frontend env may be outdated"
fi

# Set default Python version if not specified
PYTHON_VERSION=${PYTHON_VERSION:-3.10}

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python$PYTHON_VERSION -m venv .venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies if needed
if [ ! -f "config/requirements.lock" ]; then
    echo "❌ Error: requirements.lock not found!"
    echo "💡 Please run 'make l' to generate it"
    exit 1
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r config/requirements.lock

# Start FastAPI app with Uvicorn
echo "🚀 Starting backend server..."
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000 