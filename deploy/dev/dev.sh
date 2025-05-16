#!/bin/bash
# filepath: /Users/u1155516/tech-local/aiinfra-atlas/deploy/dev/dev.sh
set -e

# Setup proper directory paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"  # Go up two levels from deploy/dev

# Check for --clean flag to force clean environment
CLEAN_ENV=false
for arg in "$@"; do
  if [ "$arg" == "--clean" ]; then
    CLEAN_ENV=true
    echo "❗ Clean install requested. Will rebuild virtual environment from scratch."
    break
  fi
done

# Run setup_env.sh to ensure proper environment configuration
echo "Setting up development environment configuration..."
"$PROJECT_ROOT/config/setup_env.sh" dev

# Cleanup function to remove the copied .env file from frontend upon exit
cleanup() {
    rm -f "$PROJECT_ROOT/frontend/.env" || true
}
trap cleanup EXIT

# Load environment variables from config/.env file
if [ -f "$PROJECT_ROOT/config/.env" ]; then
    echo "Loading environment variables from config/.env..."
    set -a
    source "$PROJECT_ROOT/config/.env"
    set +a
else
    echo "Error: config/.env file not found!"
    exit 1
fi

# Get required secrets from config/.secrets file
if [ -f "$PROJECT_ROOT/config/.secrets" ]; then
    # Source the .secrets file directly to get all variables
    echo "Loading secrets from config/.secrets..."
    set -a
    source "$PROJECT_ROOT/config/.secrets"
    set +a
    
    # Verify REDIS_PASSWORD is set
    if [ -z "$REDIS_PASSWORD" ]; then
        echo "Error: REDIS_PASSWORD not found in config/.secrets file!"
        exit 1
    fi
    
    # Set REDIS_HOST and REDIS_PORT if not already set
    export REDIS_HOST="${REDIS_HOST:-localhost}"
    export REDIS_PORT="${REDIS_PORT:-6379}"
    
    echo "Using Redis credentials: host=$REDIS_HOST, port=$REDIS_PORT"
    
    # Filter out keys with <DEFAULT> value
    for var in $(compgen -e); do
        if [[ $var == *_API_KEY || $var == *_KEY ]] && [[ "${!var}" == "<DEFAULT>" ]]; then
            echo "Warning: $var is set to default value and will not be used"
            unset "$var"
        fi
    done
else
    echo "Error: config/.secrets file not found!"
    exit 1
fi

# Check if REDIS_HOST and REDIS_PORT are in the .secrets file
secrets_file="$PROJECT_ROOT/config/.secrets"
if ! grep -q "^REDIS_HOST=" "$secrets_file"; then
    echo "Adding REDIS_HOST to .secrets file"
    echo "REDIS_HOST=\"${REDIS_HOST:-localhost}\"" >> "$secrets_file"
fi

if ! grep -q "^REDIS_PORT=" "$secrets_file"; then
    echo "Adding REDIS_PORT to .secrets file"
    echo "REDIS_PORT=\"${REDIS_PORT:-6379}\"" >> "$secrets_file"
fi

# Re-source the updated .secrets file
set -a
source "$secrets_file"
set +a

# Define environment variables for the Flask app
export REDIS_URL="redis://default:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}"
export SOCKETIO_MESSAGE_QUEUE="$REDIS_URL"

# Move to project root for remaining operations
cd "$PROJECT_ROOT"

# --- Python Environment Setup ---

# Set Python binary based on PYTHON_VERSION from .env file
if [ -z "$PYTHON_VERSION" ]; then
    echo "⚠️ Warning: PYTHON_VERSION not found in .env file, defaulting to 3.10"
    PYTHON_VERSION="3.10"
fi
echo "📋 Required Python version: $PYTHON_VERSION"
PYTHON_BINARY="python${PYTHON_VERSION}"

# Check if Python version is available
if ! command -v $PYTHON_BINARY &> /dev/null; then
    echo "❌ Error: ${PYTHON_BINARY} not found. Please install Python ${PYTHON_VERSION}"
    echo "   Homebrew: brew install python@${PYTHON_VERSION}"
    echo "   or visit: https://www.python.org/downloads/"
    exit 1
fi

# Create or recreate virtual environment if needed
if [ "$CLEAN_ENV" = true ] && [ -d ".venv" ]; then
    echo "🧹 Removing existing virtual environment..."
    rm -rf .venv
fi

if [ ! -d ".venv" ]; then
    echo "🔧 Creating virtual environment with Python ${PYTHON_VERSION}..."
    ${PYTHON_BINARY} -m venv .venv
fi

echo "⬆️ Upgrading pip..."
.venv/bin/pip install --upgrade pip

# Enhanced dependency installation with proper error handling
echo "📦 Installing Python dependencies..."

# Check if requirements files exist
if [ ! -f "$PROJECT_ROOT/config/requirements.lock" ]; then
    echo "⚠️ Warning: No lock file found at config/requirements.lock"
    
    if [ ! -f "$PROJECT_ROOT/config/requirements.txt" ]; then
        echo "❌ Error: requirements.txt not found either! Cannot install dependencies."
        exit 1
    fi
    
    echo "🔄 Falling back to requirements.txt and will generate a lock file..."
    if ! .venv/bin/pip install -r "$PROJECT_ROOT/config/requirements.txt"; then
        echo "❌ Failed to install dependencies from requirements.txt"
        exit 1
    fi
    
    echo "🔒 Generating lock file from current environment..."
    .venv/bin/pip freeze > "$PROJECT_ROOT/config/requirements.lock"
    echo "✅ Lock file generated at config/requirements.lock"
else
    echo "🔒 Found lock file - installing from locked dependencies..."
    
    # Two-phase installation for better dependency resolution
    echo "   Phase 1: Installing packages without dependencies..."
    if ! .venv/bin/pip install --no-deps -r "$PROJECT_ROOT/config/requirements.lock"; then
        echo "❌ Failed in phase 1 of dependency installation"
        exit 1
    fi
    
    echo "   Phase 2: Resolving dependencies..."
    if ! .venv/bin/pip install -r "$PROJECT_ROOT/config/requirements.lock"; then
        echo "❌ Failed to resolve dependencies"
        echo "🔄 Your lock file might have conflicts. You can try:"
        echo "   1. Run './deploy/dev/dev.sh --clean' to start fresh"
        echo "   2. Or manually fix the conflicts and regenerate the lock file"
        exit 1
    fi
    
    echo "✅ Successfully installed dependencies from lock file"
fi

# Check for common dependency conflicts
echo "🔍 Checking for common dependency conflicts..."
if .venv/bin/pip check; then
    echo "✅ No dependency conflicts detected"
else
    echo "⚠️ Warning: Dependency conflicts detected"
    echo "   The application might still work, but some features could be unstable"
fi

# --- Frontend Node.js Setup ---

echo "🔍 Checking Node.js environment..."

# Get Node.js version from environment variable
if [ -z "$NODE_VERSION" ]; then
    echo "⚠️ Warning: NODE_VERSION not found in .env file, defaulting to 20.11.1"
    NODE_VERSION="20.11.1"
fi

echo "📋 Required Node.js version: $NODE_VERSION"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed"
    echo "   Please install Node.js $NODE_VERSION using nvm or from https://nodejs.org/"
    exit 1
fi

# Check Node.js version
CURRENT_NODE_VERSION=$(node -v | cut -d 'v' -f 2)
NODE_MAJOR=$(echo $NODE_VERSION | cut -d '.' -f 1)

if ! [[ "$CURRENT_NODE_VERSION" =~ ^$NODE_MAJOR\. ]]; then
    echo "⚠️ Warning: You are using Node.js $CURRENT_NODE_VERSION, but version $NODE_VERSION is recommended"
    echo "   Your version may work, but for best compatibility, please consider upgrading"
    
    # Ask user if they want to continue
    read -p "   Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "   Installation aborted. Please install Node.js $NODE_VERSION and try again."
        exit 1
    fi
fi

echo "📦 Installing Node.js dependencies in frontend..."
cd "$PROJECT_ROOT/frontend"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found in frontend directory!"
    exit 1
fi

# Install dependencies with proper error handling
if ! npm install; then
    echo "❌ Failed to install Node.js dependencies"
    echo "   Try running 'npm cache clean --force' and then retry"
    exit 1
fi

# Return to project root
cd "$PROJECT_ROOT"

echo "✅ Node.js dependencies installed successfully"

# Create frontend environment file using the setup_react_env.sh script
echo "🔧 Setting up React environment variables..."
if [ -f "$PROJECT_ROOT/config/setup_react_env.sh" ]; then
    "$PROJECT_ROOT/config/setup_react_env.sh"
else
    echo "❌ Error: config/setup_react_env.sh script not found!"
    exit 1
fi

# --- Redis Container Setup ---

# Build Redis dev image to avoid conflicts with prod images
echo "🐳 Building Redis dev image..."
# Pass the REDIS_PASSWORD to the Docker build
docker build --build-arg REDIS_PASSWORD="$REDIS_PASSWORD" -t redis-dev:latest -f "$PROJECT_ROOT/deploy/dev/Dockerfile.redis.dev" .

# Remove any existing container using port 6379
echo "🧹 Finding and removing any container using port 6379..."
existing_container=$(docker ps --filter "publish=6379" -q)
if [ -n "$existing_container" ]; then
    docker rm -f $existing_container || true
fi

# Also remove any container named redis-dev
echo "🧹 Removing any existing Redis container named redis-dev..."
docker rm -f redis-dev || true

echo "🚀 Starting Redis container for local development..."
docker run -d --rm --name redis-dev -p6379:6379 \
    -v "$PROJECT_ROOT/redis/dump.rdb":/data/dump.rdb \
    -e REDIS_PASSWORD="$REDIS_PASSWORD" \
    redis-dev:latest

# --- Nginx Container Setup ---

# Build the Nginx dev image using Dockerfile.nginx.dev in deploy/dev
echo "🐳 Building Nginx dev image..."
cd "$PROJECT_ROOT/deploy/dev"
docker build -f Dockerfile.nginx.dev -t nginx-dev:latest .
cd "$PROJECT_ROOT"

# Remove any existing Nginx container named nginx-dev
echo "🧹 Removing any existing Nginx container named nginx-dev..."
docker rm -f nginx-dev || true

echo "🚀 Starting Nginx container for local development..."
docker run -d --rm --name nginx-dev \
    -p 80:80 -p 443:443 \
    --add-host=host.docker.internal:host-gateway \
    -v "${DEV_CERTS_PATH}:/etc/letsencrypt/live/localhost:ro" \
    -e SERVER_NAME=localhost \
    nginx-dev:latest

# --- Launch Flask App ---

echo "⏳ Waiting 5 seconds for Redis and Nginx to initialize..."
sleep 5

echo "🚀 Launching Flask app..."
echo "📊 Telemetry data will be sent to Arize Cloud at ${PHOENIX_COLLECTOR_ENDPOINT}"

# Set Flask environment variables
export FLASK_APP=backend/app.py
export FLASK_ENV=development
export PYTHONPATH="$PROJECT_ROOT"

# Run the app directly with Python
cd "$PROJECT_ROOT"

# Set TEST_TARGET if not already set
if [ -z "$TEST_TARGET" ]; then
    # Default to blert_500 if no TEST_TARGET is set
    TEST_TARGET="backend.targets.blert_500.blert_500"
    export TEST_TARGET
fi

# Display which target we're using
echo -e "\n\033[1;34mUsing test target: $TEST_TARGET\033[0m"

# Simple check for embedding model
echo "🔍 Checking embedding model..."

# Create a temporary file for error output
error_log="/tmp/embedding_check_error.log"

# Directly check if we can load the embedding model - no need to import the target module
$PROJECT_ROOT/.venv/bin/python -c "from langchain_community.embeddings import HuggingFaceEmbeddings; print('Downloading and attempting to load embedding model: Livingwithmachines/bert_1890_1900'); embedding = HuggingFaceEmbeddings(model_name='Livingwithmachines/bert_1890_1900'); test = embedding.embed_query('test'); print('✓ Successfully loaded embedding model')" 2>"$error_log"

if [ $? -eq 0 ]; then
    echo -e "\033[1;32m✓ Embedding model loaded successfully\033[0m"
else
    echo -e "\033[1;31m✗ Warning: Embedding model check failed\033[0m"
    echo "  The application will continue, but vector search functionality may not work correctly."
    echo ""
    echo "Error details:"
    cat "$error_log"
    echo ""
fi

# Set PORT and APP_HOST explicitly to ensure Flask binds to all interfaces
PORT=5001 APP_HOST=0.0.0.0 .venv/bin/python backend/app.py

echo "Development environment setup complete!"
echo "Flask app running on https://localhost:5001"
echo "Press Ctrl+C to stop the Flask app"
echo "Open a new terminal and run 'make frontend' to start the frontend at localhost"