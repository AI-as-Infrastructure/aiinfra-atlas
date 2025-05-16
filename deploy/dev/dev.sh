#!/bin/bash
set -e

# ATLAS dev.sh: Node.js and npm must be managed via nvm (Node Version Manager).
echo "[INFO] This script requires Node.js and npm to be managed via nvm (Node Version Manager)."
echo "[INFO] Do NOT install node or npm via your system package manager (e.g., apt-get)."
echo "[INFO] If you do not have nvm installed, see: https://github.com/nvm-sh/nvm#installing-and-updating"

# Load nvm if available (for non-interactive shells)
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
fi

# Check if nvm is installed
if ! command -v nvm &> /dev/null; then
    echo "[ERROR] nvm is not installed. Please install nvm before running this script."
    exit 1
fi

# Set project root and cd there
PROJECT_ROOT="$(dirname $(dirname $(dirname $(readlink -f "$0"))))"
cd "$PROJECT_ROOT"

# Function to check version requirements
check_version() {
    local required_version=$1
    local current_version=$2
    local component=$3
    
    if [ "$(printf '%s\n' "$required_version" "$current_version" | sort -V | head -n1)" != "$required_version" ]; then
        echo "Error: $component version $required_version is required, but found $current_version"
        return 1
    fi
    return 0
}

# Load environment variables from config/.env.development
if [ -f config/.env.development ]; then
    # More robust way to load environment variables with special characters
    set -a
    source config/.env.development
    set +a
else
    echo "[ERROR] config/.env.development not found! Please create it from config/.env.template."
    exit 1
fi

# Set default Python version if not specified
PYTHON_VERSION=${PYTHON_VERSION:-3.10}

# Generate frontend environment file using the centralized script
if [ -f config/generate_frontend_env.sh ]; then
    echo "[INFO] Generating frontend environment variables for Vue app..."
    bash config/generate_frontend_env.sh "development"
else
    echo "[WARN] config/generate_frontend_env.sh not found. Falling back to basic extraction."
    if [ -f config/.env.development ]; then
        grep -E '^VITE_' config/.env.development > frontend/.env
        echo "[INFO] Extracted VITE_ variables from config/.env.development to frontend/.env"
    fi
fi

# Check Python version
CURRENT_PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if ! check_version "$PYTHON_VERSION" "$CURRENT_PYTHON_VERSION" "Python"; then
    echo "[WARN] Python $PYTHON_VERSION not found. Attempting to install required Python version..."
    sudo apt-get update
    sudo apt-get install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install -y python$PYTHON_VERSION python$PYTHON_VERSION-venv python$PYTHON_VERSION-distutils
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating Python $PYTHON_VERSION virtual environment..."
    python$PYTHON_VERSION -m venv .venv
fi

# Activate venv and install dependencies
. .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.lock

# Check Node.js version
cd frontend
if [ -f .nvmrc ]; then
    # Enforce Node.js version using nvm for frontend development
    NODE_VERSION=$(node --version 2>&1 | sed 's/v//')
    REQUIRED_NODE_VERSION=$(cat .nvmrc)
    if ! check_version "$REQUIRED_NODE_VERSION" "$NODE_VERSION" "Node.js"; then
        echo "[ERROR] Node.js version $REQUIRED_NODE_VERSION is required for this project."
        echo "[INFO] Please use nvm to install and activate the required version:"
        echo "    nvm install $REQUIRED_NODE_VERSION"
        echo "    nvm use $REQUIRED_NODE_VERSION"
        echo "[INFO] If you do not have nvm, see: https://github.com/nvm-sh/nvm#installing-and-updating"
        exit 1
    fi
fi

# Install Node.js dependencies
npm install --loglevel=warn

# Return to project root
cd "$PROJECT_ROOT"

# Ensure Chroma database is available
CHROMA_DIR="$PROJECT_ROOT/$CHROMA_PERSIST_DIRECTORY"
STATS_FILE="$PROJECT_ROOT/backend/targets/$CHROMA_COLLECTION_NAME.txt"

if [ ! -d "$CHROMA_DIR" ]; then
    echo "[WARN] Chroma database not found at $CHROMA_DIR"
    echo "Please run 'make store' to create the Chroma database"
    mkdir -p "$CHROMA_DIR"
    echo "[INFO] Created empty directory at $CHROMA_DIR"
    echo "You may need to create it with 'make store' or pull it from Git LFS"
fi

# Check if statistics file exists
if [ ! -f "$STATS_FILE" ]; then
    echo "[WARN] Statistics file not found at $STATS_FILE"
    echo "[WARN] This file is needed for the retriever to function properly"
    echo "You may need to create it with 'make store' or pull it from Git LFS"
fi

# Start FastAPI app with Uvicorn
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000