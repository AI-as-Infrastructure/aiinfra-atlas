#!/bin/bash

# Development environment cleanup script
set -e

# Check if being called with --force flag (from reset script)
if [ "$1" != "--force" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧹 DEVELOPMENT ENVIRONMENT CLEANUP"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "This will REMOVE:"
    echo "  • Python virtual environments (.venv)"
    echo "  • Node modules and package-lock.json"
    echo "  • Frontend build artifacts (dist/)"
    echo "  • Telemetry database"
    echo "  • Python package metadata"
    echo ""
    echo "This will PRESERVE:"
    echo "  ✓ Corpus data"
    echo "  ✓ Configuration files"
    echo "  ✓ Custom retrievers"
    echo "  ✓ Test targets"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "💡 TIP: Use 'make reset' for complete cleanup including corpus/configs"
    echo ""
    read -p "Continue with environment cleanup? (y/N): " confirmation

    if [ "$confirmation" != "y" ] && [ "$confirmation" != "Y" ]; then
        echo "Cleanup cancelled."
        exit 0
    fi
fi

echo ""
# Stop any running processes
echo "Stopping running processes..."
pkill -f "uvicorn backend.app:app" || true
pkill -f "npm run dev" || true

# Remove ALL virtual environments (matches any .venv* or venv* pattern)
echo "Removing all virtual environments..."
rm -rf .venv 2>/dev/null || true
rm -rf .venv_* 2>/dev/null || true
rm -rf .venv-* 2>/dev/null || true
rm -rf venv 2>/dev/null || true
rm -rf venv_* 2>/dev/null || true

# Clean up frontend
echo "Cleaning up frontend..."
cd frontend
rm -rf node_modules
rm -f package-lock.json
rm -rf dist
rm -f .env
cd ..

# Clean up telemetry span registry
echo "Cleaning up telemetry database..."
rm -f telemetry_span_registry.db

# Clean up Python package metadata
echo "Cleaning up Python package metadata..."
rm -rf *.egg-info 2>/dev/null || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CLEANUP COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Environment cleaned. Your corpus and configuration were preserved."
echo ""
echo "To restart development:"
echo "  1. Run 'make b' to start the backend"
echo "  2. Run 'make f' to start the frontend"
echo ""
echo "To do a complete reset (remove corpus/configs too):"
echo "  Run 'make reset'" 