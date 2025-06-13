#!/bin/bash
set -e

# ATLAS dev.sh: Node.js and npm must be managed via nvm (Node Version Manager).
echo "[INFO] This script requires Node.js and npm to be managed via nvm (Node Version Manager)."
echo "[INFO] Do NOT install node or npm via your system package manager (e.g., apt-get)."
echo "[INFO] If you do not have nvm installed, see: https://github.com/nvm-sh/nvm#installing-and-updating"

# Attempt to load nvm from common locations for both interactive and non-interactive shells
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh" || true
elif [ -s "/usr/local/opt/nvm/nvm.sh" ]; then
    . "/usr/local/opt/nvm/nvm.sh" || true
elif [ -s "/usr/share/nvm/init-nvm.sh" ]; then
    . "/usr/share/nvm/init-nvm.sh" || true
fi

# Fallback: Try sourcing common user profile files if nvm is still not available
if ! command -v nvm &> /dev/null; then
    for profile in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$profile" ]; then
            . "$profile" || true
            if command -v nvm &> /dev/null; then
                break
            fi
        fi
    done
fi

# Diagnostics and actionable error if nvm is still not found
if ! command -v nvm &> /dev/null; then
    echo "\n[ERROR] nvm (Node Version Manager) is not installed or not available in this shell."
    echo "NVM_DIR is: $NVM_DIR"
    echo "Checked for nvm in:"
    echo "  $HOME/.nvm/nvm.sh"
    echo "  /usr/local/opt/nvm/nvm.sh"
    echo "  /usr/share/nvm/init-nvm.sh"
    echo "  and user profiles (.bashrc, .bash_profile, .zshrc, .profile)"
    echo "\nTo fix this, try running these commands in your terminal, then restart your terminal and try again:"
    echo "  export NVM_DIR=\"$HOME/.nvm\""
    echo "  [ -s \"$NVM_DIR/nvm.sh\" ] && \\. \"$NVM_DIR/nvm.sh\""
    echo "If nvm is not installed, install it with:"
    echo "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"
    echo "See https://github.com/nvm-sh/nvm#installing-and-updating for more info."
    exit 2
fi

# Set project root and cd there
PROJECT_ROOT="$(dirname $(dirname $(dirname $(readlink -f "$0"))))"
cd "$PROJECT_ROOT"

# Set the environment for app.py
export ATLAS_ENV=development

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

# The ENVIRONMENT variable should be set from .env.development
# No fallback - must be explicitly set
if [ -z "$ENVIRONMENT" ]; then
    echo "[ERROR] ENVIRONMENT variable is not set in .env.development"
    echo "[ERROR] Please add ENVIRONMENT=development to your .env.development file"
    exit 1
else
    echo "[INFO] Using ENVIRONMENT=$ENVIRONMENT from .env.development"
fi

if [ -f config/generate_vue_files.sh ]; then
    echo "[INFO] Generating frontend environment variables and templates..."
    bash config/generate_vue_files.sh
else
    echo "[ERROR] config/generate_vue_files.sh not found. Cannot continue."
    echo "Please ensure config/generate_vue_files.sh exists and is executable."
    exit 1
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

# Ensure correct Node.js version is loaded via nvm before using npm
cd frontend
if [ -f .nvmrc ]; then
    REQUIRED_NODE_VERSION=$(cat .nvmrc)
    nvm use "$REQUIRED_NODE_VERSION" || nvm install "$REQUIRED_NODE_VERSION" || {
        echo "[ERROR] Failed to use or install Node.js version $REQUIRED_NODE_VERSION via nvm.";
        exit 3;
    }
else
    nvm use --lts || nvm install --lts || {
        echo "[ERROR] Failed to use or install latest LTS Node.js via nvm.";
        exit 3;
    }
fi

# Check for npm availability
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm not found after running nvm use. Please check your nvm and Node.js installation."
    exit 4
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

echo "[INFO] Environment setup complete!"
echo "[INFO] You can now run:"
echo "  make b  # Start backend server"
echo "  make f  # Start frontend server"