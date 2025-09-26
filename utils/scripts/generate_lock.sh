#!/usr/bin/env bash

# Requirements lock file generation script (CPU-only, reproducible)
set -euo pipefail

REQ_IN="config/requirements.txt"
REQ_OUT="config/requirements.lock"
TMP_VENV=".venv_lock"

if [ ! -f "$REQ_IN" ]; then
        echo "❌ Error: $REQ_IN not found!"
        exit 1
fi

# Prefer python3.10 for compatibility with deploy targets; fall back to python3
PY_BIN="python3.10"
if ! command -v $PY_BIN >/dev/null 2>&1; then
    PY_BIN="python3"
fi

echo "📦 Creating temporary environment for lock generation using $PY_BIN..."
rm -rf "$TMP_VENV" || true
$PY_BIN -m venv "$TMP_VENV"

echo "🔌 Activating temporary environment..."
source "$TMP_VENV/bin/activate"
pip install --upgrade pip
echo "📥 Installing pip-tools..."
pip install pip-tools

# Force CPU-only PyTorch index to avoid CUDA packages
export PIP_INDEX_URL="https://download.pytorch.org/whl/cpu"
export PIP_EXTRA_INDEX_URL="https://pypi.org/simple"
unset TORCH_CUDA_INDEX_URL || true

echo "🔒 Generating $REQ_OUT from $REQ_IN (CPU-only lock)..."
pip-compile --verbose "$REQ_IN" -o "$REQ_OUT"

echo "🧹 Cleaning up temporary environment..."
deactivate || true
rm -rf "$TMP_VENV"

echo "✅ Lock file generated successfully at $REQ_OUT"