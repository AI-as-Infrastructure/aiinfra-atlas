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

# Detect GPU and install appropriate PyTorch for corpus building
echo "🎮 Detecting GPU capability for corpus building..."

# Check current PyTorch installation
CURRENT_TORCH_GPU=false
if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    CURRENT_TORCH_GPU=true
    echo "📦 Existing PyTorch installation has GPU support"
fi

if command -v nvidia-smi &>/dev/null; then
    echo "✅ NVIDIA GPU detected"

    # Only reinstall if current PyTorch doesn't have GPU support
    if [ "$CURRENT_TORCH_GPU" = false ]; then
        echo "🔄 Installing GPU-enabled PyTorch (this may take a moment)..."
        CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' | cut -d. -f1,2 | tr -d '.' || echo "124")
        echo "   Detected CUDA version code: $CUDA_VERSION"

        # For very new GPUs (compute capability 11.x, 12.x), use the latest CUDA build
        # RTX 5090 and similar new cards need CUDA 12.4+
        if [ "$CUDA_VERSION" = "118" ]; then
            TORCH_INDEX="https://download.pytorch.org/whl/cu118"
        elif [ "$CUDA_VERSION" = "121" ]; then
            TORCH_INDEX="https://download.pytorch.org/whl/cu121"
        else
            # For CUDA 12.4+ and newer GPUs, use the latest nightly build
            echo "   Using PyTorch nightly for newer GPU support (CUDA 12.4+)"
            TORCH_INDEX="https://download.pytorch.org/whl/nightly/cu124"
        fi

        # Force reinstall PyTorch with GPU support
        pip uninstall torch torchvision torchaudio -y 2>/dev/null || true

        # Install latest PyTorch with support for newer GPUs
        if [ "$TORCH_INDEX" = "https://download.pytorch.org/whl/nightly/cu124" ]; then
            pip install --pre torch --index-url $TORCH_INDEX
        else
            pip install torch --index-url $TORCH_INDEX
        fi

        # Verify GPU is actually available after install
        if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
            echo "✅ GPU support confirmed - corpus building will use GPU"
            echo "gpu" > .venv/.corpus_mode
        else
            echo "⚠️  GPU PyTorch installed but GPU not accessible - will use CPU"
            echo "   This may be due to CUDA driver issues"
            echo "cpu" > .venv/.corpus_mode
        fi
    else
        echo "✅ GPU support already configured - corpus building will use GPU"
        echo "gpu" > .venv/.corpus_mode
    fi
else
    echo "💻 No GPU detected - ensuring CPU-only PyTorch..."
    if [ "$CURRENT_TORCH_GPU" = true ] || ! python -c "import torch" 2>/dev/null; then
        # Need to install CPU version (either switching from GPU or no torch at all)
        pip uninstall torch -y 2>/dev/null || true
        pip install torch --index-url https://download.pytorch.org/whl/cpu
    fi
    echo "cpu" > .venv/.corpus_mode
fi

# Display GPU status summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎮 GPU Configuration Summary:"
if [ -f ".venv/.corpus_mode" ]; then
    MODE=$(cat .venv/.corpus_mode)
    if [ "$MODE" = "gpu" ]; then
        echo "  ✅ Corpus Building: GPU acceleration enabled"
        echo "  ✅ RAG Search: GPU acceleration enabled"
        echo "  🚀 All embeddings will use GPU for faster processing"
    else
        echo "  💻 Corpus Building: CPU mode"
        echo "  💻 RAG Search: CPU mode"
        echo "  ℹ️  GPU not available or not configured"
    fi
else
    echo "  ⚠️  Mode not configured - defaulting to CPU"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start FastAPI app with Uvicorn
echo "🚀 Starting backend server..."
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000 --reload-exclude=".venv/*" --reload-exclude="*.pyc" --reload-exclude="__pycache__/*" 