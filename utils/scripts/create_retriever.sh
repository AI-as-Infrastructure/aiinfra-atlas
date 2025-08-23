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

# Install dependencies (prefer CPU lock; allow optional GPU torch via TORCH_CUDA_INDEX_URL)
echo "Installing dependencies..."
pip install --upgrade pip
PYTORCH_INDEX_DEFAULT="https://download.pytorch.org/whl/cu126"
PYTORCH_INDEX="${TORCH_CUDA_INDEX_URL:-$PYTORCH_INDEX_DEFAULT}"
if grep -qE '^(torch|torchvision|torchaudio)==.*\+cu' config/requirements.lock; then
    echo "🔧 Detected CUDA wheels in lockfile. Installing non-torch deps first..."
    TMP_NO_TORCH=$(mktemp)
    grep -v -E '^(torch|torchvision|torchaudio)==.*' config/requirements.lock > "$TMP_NO_TORCH"
    pip install -r "$TMP_NO_TORCH"
    rm -f "$TMP_NO_TORCH"

    echo "🧩 Installing CUDA-enabled torch stack from: $PYTORCH_INDEX"
    pip install --index-url "$PYTORCH_INDEX" torch torchvision torchaudio
else
    pip install -r config/requirements.lock
fi

# Create retriever
echo "Creating retriever..."
python create/txt/create_hansard_retriever.py

echo "Retriever created successfully!"
echo "Move hansard_retriever.py to backend/retrievers to use the file with the ATLAS system."
echo "Ensure you have also generated a matching vector store using create_hansard_store.py." 