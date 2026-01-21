#!/bin/bash
# Corpus wizard setup with isolated environment (GPU/CUDA version)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🧙 Corpus Configuration Wizard Setup (GPU/CUDA)"
echo "================================================"
echo ""

# Use a separate venv for corpus building to avoid conflicts
CORPUS_VENV=".venv_corpus"

# Use Python 3.10 to match the rest of the project
PYTHON_CMD="python3.10"

# Check if python3.10 is available
if ! command -v $PYTHON_CMD &>/dev/null; then
    echo -e "${YELLOW}⚠️  Python 3.10 not found, using default python3${NC}"
    PYTHON_CMD="python3"
fi

PYTHON_VER=$($PYTHON_CMD --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
echo "📦 Using Python ${PYTHON_VER}"

# Check for CUDA
echo "🎮 Checking for CUDA support..."
if command -v nvidia-smi &>/dev/null; then
    echo -e "${GREEN}✅ NVIDIA GPU detected${NC}"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
else
    echo -e "${YELLOW}⚠️  No NVIDIA GPU detected - consider using 'make corpus-wizard-cpu' instead${NC}"
fi

# Create isolated corpus virtual environment if it doesn't exist
if [ ! -d "$CORPUS_VENV" ] || [ ! -f "$CORPUS_VENV/bin/python" ]; then
    echo "📦 Creating isolated corpus virtual environment..."

    # Remove any incomplete venv
    rm -rf "$CORPUS_VENV" 2>/dev/null || true

    # Try to create venv
    if ! $PYTHON_CMD -m venv $CORPUS_VENV; then
        echo -e "${RED}❌ Cannot create virtual environment${NC}"
        echo ""
        echo "The python3-venv package is not properly installed."
        echo ""
        echo "To fix this, run:"
        echo ""
        echo -e "${GREEN}  sudo apt-get update && sudo apt-get install -y python3.10-venv${NC}"
        echo ""
        echo "Then run 'make corpus-wizard-gpu' again."
        exit 1
    fi

    # Verify venv was created properly
    if [ ! -f "$CORPUS_VENV/bin/python" ] || [ ! -f "$CORPUS_VENV/bin/pip" ]; then
        rm -rf "$CORPUS_VENV" 2>/dev/null || true
        echo -e "${RED}❌ Virtual environment creation incomplete${NC}"
        echo ""
        echo "The virtual environment was created but is missing required components."
        echo "This usually means the python3.10-venv package needs to be installed."
        echo ""
        echo "To fix this, run:"
        echo ""
        echo -e "${GREEN}  sudo apt-get update && sudo apt-get install -y python3.10-venv${NC}"
        echo ""
        echo "Then run 'make corpus-wizard-gpu' again."
        exit 1
    fi
fi

# Activate corpus virtual environment
echo "🔌 Activating corpus virtual environment..."
source $CORPUS_VENV/bin/activate

# Debug: Show which pip we're using
echo "📦 Using pip from: $(which pip)"
echo "📦 Pip version: $(pip --version)"

# Upgrade pip using direct path to ensure we use the right one
echo "📥 Upgrading pip..."
if ! $CORPUS_VENV/bin/python -m pip install --upgrade pip; then
    echo -e "${RED}❌ Failed to upgrade pip${NC}"
    echo "The virtual environment may be corrupted."
    echo "Try running 'make corpus-clean' and then 'make corpus-wizard-gpu' again."
    exit 1
fi

# Install minimal requirements for corpus building
echo "📥 Installing corpus wizard dependencies..."

# Install core dependencies needed for corpus building using explicit python path
# Note: Install basic packages first
if ! $CORPUS_VENV/bin/python -m pip install \
    pyyaml \
    requests \
    gitpython \
    tqdm \
    numpy; then
    echo -e "${RED}❌ Failed to install basic dependencies${NC}"
    echo "There was an error installing the required packages."
    echo "Check your internet connection and try again."
    exit 1
fi

# Install GPU-enabled PyTorch (larger download, includes CUDA)
echo "📥 Installing PyTorch (GPU/CUDA version - larger download)..."
echo "   This will download ~2GB for CUDA-enabled PyTorch..."

# Try to detect CUDA version and install appropriate PyTorch
CUDA_VERSION=""
if command -v nvidia-smi &>/dev/null; then
    CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' | cut -d. -f1,2 | tr -d '.')
    echo "   Detected CUDA version: $CUDA_VERSION"
fi

# Install PyTorch with CUDA support (defaults to CUDA 12.1 if detection fails)
if [ "$CUDA_VERSION" = "118" ]; then
    echo "   Installing PyTorch for CUDA 11.8..."
    TORCH_INDEX="https://download.pytorch.org/whl/cu118"
elif [ "$CUDA_VERSION" = "121" ] || [ -z "$CUDA_VERSION" ]; then
    echo "   Installing PyTorch for CUDA 12.1 (default)..."
    TORCH_INDEX="https://download.pytorch.org/whl/cu121"
else
    echo "   Installing PyTorch for CUDA 12.1 (default)..."
    TORCH_INDEX="https://download.pytorch.org/whl/cu121"
fi

if ! $CORPUS_VENV/bin/python -m pip install torch --index-url $TORCH_INDEX; then
    echo -e "${YELLOW}⚠️  Warning: Failed to install GPU PyTorch, falling back to CPU version${NC}"
    $CORPUS_VENV/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
fi

# Install remaining dependencies
echo "📥 Installing remaining corpus dependencies..."
if ! $CORPUS_VENV/bin/python -m pip install \
    transformers \
    sentence-transformers \
    chromadb \
    langchain \
    langchain-community \
    nltk; then
    echo -e "${RED}❌ Failed to install ML dependencies${NC}"
    echo "There was an error installing the required packages."
    echo "Check your internet connection and try again."
    exit 1
fi

# Verify GPU support
echo ""
echo "🎮 Verifying GPU support..."
$CORPUS_VENV/bin/python -c "
import torch
if torch.cuda.is_available():
    print('✅ PyTorch GPU support confirmed')
    print(f'   GPU: {torch.cuda.get_device_name(0)}')
    print(f'   CUDA: {torch.version.cuda}')
else:
    print('⚠️  PyTorch GPU support NOT available - will use CPU')
" || echo -e "${YELLOW}⚠️  Could not verify GPU support${NC}"

echo ""
echo -e "${GREEN}✅ Corpus wizard environment ready (GPU/CUDA)${NC}"
echo ""

# Check if servers are running
BACKEND_RUNNING=false
FRONTEND_RUNNING=false

if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend server is running${NC}"
    BACKEND_RUNNING=true
else
    echo -e "${YELLOW}⚠️  Backend server not running${NC}"
    echo "   Start with: make b"
fi

if curl -s http://localhost:5173 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend server is running${NC}"
    FRONTEND_RUNNING=true
else
    echo -e "${YELLOW}⚠️  Frontend server not running${NC}"
    echo "   Start with: make f"
fi

echo ""
echo "====================================="
echo ""

# If both servers are running, open the wizard
if [ "$BACKEND_RUNNING" = true ] && [ "$FRONTEND_RUNNING" = true ]; then
    URL="http://localhost:5173/corpus-wizard"

    echo "🌐 Opening corpus wizard at: $URL"
    echo ""

    # Try to open in browser
    if command -v xdg-open > /dev/null; then
        xdg-open "$URL" 2>/dev/null &
    elif command -v open > /dev/null; then
        open "$URL" 2>/dev/null &
    fi
else
    echo "To use the corpus wizard:"
    if [ "$BACKEND_RUNNING" = false ]; then
        echo "  1. Start backend: make b"
    fi
    if [ "$FRONTEND_RUNNING" = false ]; then
        echo "  2. Start frontend: make f (in new terminal)"
    fi
    echo "  3. Open: http://localhost:5173/corpus-wizard"
fi

echo ""
echo "📝 Notes:"
echo "  - GPU/CUDA mode (larger downloads, GPU acceleration enabled)"
echo "  - Corpus wizard uses isolated environment ($CORPUS_VENV)"
echo "  - Clean up with: make corpus-clean"
echo "  - This won't interfere with main dev environment (.venv)"
echo ""