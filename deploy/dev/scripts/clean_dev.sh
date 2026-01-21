#!/bin/bash

# Development environment cleanup script
set -e

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

echo "Cleanup complete!" 