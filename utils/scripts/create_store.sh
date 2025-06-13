#!/bin/bash

# Vector store creation script
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

# Check if requirements.lock exists
if [ ! -f "config/requirements.lock" ]; then
    echo "❌ Error: config/requirements.lock not found!"
    echo "💡 Try running 'make l' first to generate the lock file"
    exit 1
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r config/requirements.lock

# Check if create script exists
if [ ! -f "create/txt/create_hansard_store.py" ]; then
    echo "❌ Error: create/txt/create_hansard_store.py not found!"
    exit 1
fi

# Create vector store
echo "🔨 Creating vector store..."
python create/txt/create_hansard_store.py

echo "✅ Vector store created successfully!"
echo "💡 Please commit the database directory and retriever file with Git LFS." 