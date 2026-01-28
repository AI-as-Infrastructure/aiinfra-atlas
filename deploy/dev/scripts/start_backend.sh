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

# Check if uv is available, otherwise fall back to pip
if command -v uv &>/dev/null || command -v ~/.local/bin/uv &>/dev/null; then
    echo "✅ Using uv for faster dependency installation"
    UV_CMD=$(command -v uv || echo ~/.local/bin/uv)

    # Detect GPU and select appropriate PyTorch variant
    echo "🎮 Detecting GPU capability..."

    if command -v nvidia-smi &>/dev/null; then
        echo "✅ NVIDIA GPU detected"

        # Detect CUDA version and compute capability
        CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' | cut -d. -f1,2 | tr -d '.' || echo "124")
        echo "   Detected CUDA version code: $CUDA_VERSION"

        # Determine appropriate PyTorch variant
        if [ "$CUDA_VERSION" = "118" ]; then
            echo "   Installing CUDA 11.8 variant for older GPUs (GTX 10xx, RTX 20xx/30xx)"
            TORCH_EXTRA="cuda118"
            TORCH_INDEX="https://download.pytorch.org/whl/cu118"
        elif [ "$CUDA_VERSION" = "121" ]; then
            echo "   Installing CUDA 12.1 variant for RTX 40xx series"
            TORCH_EXTRA="cuda121"
            TORCH_INDEX=""
        else
            echo "   Installing CUDA 12.4+ nightly variant for RTX 50xx series"
            TORCH_EXTRA="cuda124-nightly"
            TORCH_INDEX="https://download.pytorch.org/whl/nightly/cu124"
        fi

        # Install with uv using optional dependency
        if [ -n "$TORCH_INDEX" ]; then
            $UV_CMD pip install -e ".[$TORCH_EXTRA]" --index-url "$TORCH_INDEX"
        else
            $UV_CMD pip install -e ".[$TORCH_EXTRA]"
        fi

        # Verify GPU is actually available after install
        if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
            echo "✅ GPU support confirmed - will use GPU acceleration"
            echo "gpu" > .venv/.corpus_mode
        else
            echo "⚠️  GPU PyTorch installed but GPU not accessible - falling back to CPU"
            echo "   This may be due to CUDA driver issues or unsupported compute capability"
            $UV_CMD pip install -e ".[cpu]"
            echo "cpu" > .venv/.corpus_mode
        fi
    else
        echo "💻 No GPU detected - installing CPU-only variant"
        $UV_CMD pip install -e ".[cpu]"
        echo "cpu" > .venv/.corpus_mode
    fi
else
    echo "⚠️  uv not found - falling back to pip (slower installation)"
    echo "   Install uv for 10-100x faster installs: curl -LsSf https://astral.sh/uv/install.sh | sh"

    pip install --upgrade pip
    pip install -r config/requirements.lock

    # Legacy GPU detection for pip fallback
    echo "🎮 Detecting GPU capability..."

    if command -v nvidia-smi &>/dev/null; then
        echo "✅ NVIDIA GPU detected"
        CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' | cut -d. -f1,2 | tr -d '.' || echo "124")

        if [ "$CUDA_VERSION" = "118" ]; then
            TORCH_INDEX="https://download.pytorch.org/whl/cu118"
        elif [ "$CUDA_VERSION" = "121" ]; then
            TORCH_INDEX="https://download.pytorch.org/whl/cu121"
        else
            TORCH_INDEX="https://download.pytorch.org/whl/nightly/cu124"
        fi

        pip uninstall torch -y 2>/dev/null || true
        if [ "$TORCH_INDEX" = "https://download.pytorch.org/whl/nightly/cu124" ]; then
            pip install --pre torch --index-url $TORCH_INDEX
        else
            pip install torch --index-url $TORCH_INDEX
        fi

        if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
            echo "gpu" > .venv/.corpus_mode
        else
            echo "cpu" > .venv/.corpus_mode
        fi
    else
        echo "💻 No GPU detected"
        pip uninstall torch -y 2>/dev/null || true
        pip install torch --index-url https://download.pytorch.org/whl/cpu
        echo "cpu" > .venv/.corpus_mode
    fi
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