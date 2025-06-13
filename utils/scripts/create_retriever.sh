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
pip install -r requirements.txt

# Create retriever
echo "Creating retriever..."
python create/txt/create_retriever.py

echo "Retriever created successfully!"
echo "Please commit the retriever file with Git LFS." 