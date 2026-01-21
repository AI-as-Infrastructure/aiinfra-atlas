#!/bin/bash
# Corpus swapping utility script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[CORPUS SWAP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if corpus config is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <corpus-config-name>"
    echo "Available configurations:"
    ls -1 corpus_configs/*.yaml 2>/dev/null | sed 's|corpus_configs/||; s|\.yaml||' || echo "No configurations found"
    exit 1
fi

CONFIG_NAME=$1
CONFIG_PATH="corpus_configs/${CONFIG_NAME}.yaml"

# Check if config exists
if [ ! -f "$CONFIG_PATH" ]; then
    print_error "Configuration not found: $CONFIG_PATH"
    exit 1
fi

print_status "Starting corpus swap to: $CONFIG_NAME"

# Step 1: Backup current corpus
print_status "Backing up current corpus..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="corpus_backups/backup_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

if [ -d "backend/targets" ]; then
    cp -r backend/targets "$BACKUP_DIR/targets"
    print_status "Current corpus backed up to: $BACKUP_DIR"
else
    print_warning "No existing corpus to backup"
fi

# Step 2: Build new corpus
print_status "Building new corpus from configuration..."
print_status "This may take a while depending on corpus size..."

# Use corpus virtual environment if it exists, otherwise use main venv
if [ -d ".venv_corpus" ]; then
    print_status "Using corpus virtual environment..."
    source .venv_corpus/bin/activate
elif [ -d ".venv" ]; then
    print_status "Using main virtual environment..."
    source .venv/bin/activate
else
    print_error "No virtual environment found."
    print_error "Run 'make corpus-wizard-cpu' or 'make corpus-wizard-gpu' to set up corpus environment"
    print_error "Or 'make venv' to set up main environment"
    exit 1
fi

# Use Python 3.10 to match the rest of the project
PYTHON_CMD="python3.10"
if ! command -v $PYTHON_CMD &>/dev/null; then
    PYTHON_CMD="python3"
fi

# Check if GPU is available
if $PYTHON_CMD -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    MODE="gpu"
    print_status "GPU detected - using GPU mode for faster processing"
else
    MODE="cpu"
    print_warning "No GPU detected - using CPU mode (slower)"
fi

# Build corpus
$PYTHON_CMD create/create_corpus_store.py --config "$CONFIG_PATH" --mode "$MODE"

# Step 3: Check if build was successful
if [ ! -d "create/output/chroma_db" ]; then
    print_error "Build failed - vector store not created"
    print_status "Restoring from backup..."
    if [ -d "$BACKUP_DIR/targets" ]; then
        rm -rf backend/targets
        cp -r "$BACKUP_DIR/targets" backend/targets
    fi
    exit 1
fi

# Step 4: Swap corpus
print_status "Swapping to new corpus..."
rm -rf backend/targets
mkdir -p backend/targets
cp -r create/output/* backend/targets/

# Step 5: Verify swap
if [ -f "backend/targets/manifest.json" ] && [ -d "backend/targets/chroma_db" ]; then
    print_status "✅ Corpus swap completed successfully!"
    echo ""
    echo "New corpus details:"
    python -c "
import json
with open('backend/targets/manifest.json') as f:
    manifest = json.load(f)
    print(f\"  Name: {manifest['metadata']['name']}\")
    print(f\"  Documents: {manifest['statistics']['total_documents']}\")
    print(f\"  Chunks: {manifest['statistics']['total_chunks']}\")
    if 'filters' in manifest['statistics']:
        print(f\"  Filters: {len(manifest['statistics']['filters'])}\")
"
    echo ""
    print_status "Please restart the server to use the new corpus:"
    echo "  make run-dev"
else
    print_error "Corpus swap verification failed"
    exit 1
fi

# Step 6: Clean up
print_status "Cleaning up temporary files..."
rm -rf create/output

print_status "Done! Corpus has been swapped to: $CONFIG_NAME"