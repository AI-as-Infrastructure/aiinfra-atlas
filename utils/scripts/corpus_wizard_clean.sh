#!/bin/bash
# Clean up corpus wizard environment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🧹 Cleaning up corpus wizard environment..."
echo ""

# Remove corpus virtual environment
if [ -d ".venv_corpus" ]; then
    echo "📦 Removing corpus virtual environment (.venv_corpus)..."
    rm -rf .venv_corpus
    echo -e "${GREEN}✅ Corpus environment removed${NC}"
else
    echo -e "${YELLOW}ℹ️  No corpus environment found${NC}"
fi

# Clean up any corpus build artifacts
if [ -d "create/output" ]; then
    echo "🗑️  Removing corpus build artifacts..."
    rm -rf create/output
    echo -e "${GREEN}✅ Build artifacts removed${NC}"
fi

# Clean up temporary corpus downloads
if [ -d "create/temp_corpus" ]; then
    echo "🗑️  Removing temporary corpus downloads..."
    rm -rf create/temp_corpus
    echo -e "${GREEN}✅ Temporary downloads removed${NC}"
fi

# Clean up corpus build logs
if ls create/*.log 1> /dev/null 2>&1; then
    echo "📝 Removing corpus build logs..."
    rm -f create/*.log
    echo -e "${GREEN}✅ Build logs removed${NC}"
fi

echo ""
echo -e "${GREEN}✅ Corpus wizard cleanup complete!${NC}"
echo ""
echo "Note: This does not affect:"
echo "  - Your main development environment (.venv)"
echo "  - Your corpus configurations (corpus_configs/)"
echo "  - Your active corpus (backend/targets/)"
echo "  - Your corpus backups (corpus_backups/)"
echo ""