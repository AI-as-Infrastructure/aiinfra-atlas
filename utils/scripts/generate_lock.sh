#!/usr/bin/env bash

# Requirements lock file generation script using uv
set -euo pipefail

PYPROJECT="pyproject.toml"
REQ_OUT="config/requirements.lock"

if [ ! -f "$PYPROJECT" ]; then
        echo "❌ Error: $PYPROJECT not found!"
        exit 1
fi

# Check if uv is available
if command -v uv &>/dev/null; then
    UV_CMD="uv"
elif command -v ~/.local/bin/uv &>/dev/null; then
    UV_CMD="~/.local/bin/uv"
else
    echo "⚠️  uv not found - falling back to pip-tools (slower)"
    echo "   Install uv for faster lock generation: curl -LsSf https://astral.sh/uv/install.sh | sh"

    # Fallback to old pip-tools method
    REQ_IN="config/requirements.txt"
    TMP_VENV=".venv_lock"

    if [ ! -f "$REQ_IN" ]; then
        echo "❌ Error: $REQ_IN not found!"
        exit 1
    fi

    PY_BIN="python3.10"
    if ! command -v $PY_BIN >/dev/null 2>&1; then
        PY_BIN="python3"
    fi

    echo "📦 Creating temporary environment for lock generation using $PY_BIN..."
    rm -rf "$TMP_VENV" || true
    $PY_BIN -m venv "$TMP_VENV"

    source "$TMP_VENV/bin/activate"
    pip install "pip>=23.0,<25.0" || pip install "pip>=23.0"
    pip install --upgrade pip-tools

    export PIP_INDEX_URL="https://download.pytorch.org/whl/cpu"
    export PIP_EXTRA_INDEX_URL="https://pypi.org/simple"

    echo "🔒 Generating $REQ_OUT from $REQ_IN..."
    pip-compile --verbose "$REQ_IN" -o "$REQ_OUT"

    deactivate || true
    rm -rf "$TMP_VENV"

    echo "✅ Lock file generated successfully at $REQ_OUT"
    exit 0
fi

# Use uv for lock generation
echo "✅ Using uv for fast lock generation"
echo "🔒 Generating $REQ_OUT from $PYPROJECT..."

# Generate lock file that works across CPU/GPU machines
# Note: We don't specify --index-url here because PyTorch variants are handled
# via optional dependencies at install time, not at lock time
$UV_CMD pip compile "$PYPROJECT" -o "$REQ_OUT" --universal

echo "✅ Lock file generated successfully at $REQ_OUT"
echo "   This lock file is portable across CPU and GPU machines"
echo "   PyTorch variant will be selected at install time based on hardware"