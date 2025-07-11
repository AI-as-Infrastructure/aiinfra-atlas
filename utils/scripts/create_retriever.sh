#!/bin/bash

# Retriever creation script
set -e

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r config/requirements.lock

# Create retriever
echo "Creating retriever..."
python create/txt/create_hansard_retriever.py

echo "Retriever created successfully!"
echo "Move hansard_retriever.py to backend/retrievers to use the file with the ATLAS system."
echo "Ensure you have also generated a matching vector store using create_hansard_store.py." 