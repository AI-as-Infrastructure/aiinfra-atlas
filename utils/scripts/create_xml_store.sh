#!/bin/bash

# XML vector store creation script
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
pip install -r requirements.txt

# Create XML vector store
echo "Creating XML vector store..."
python create/xml/create_hansard_store.py

echo "XML vector store created successfully!"
echo "Please commit the database directory and retriever file with Git LFS." 