#!/bin/bash

# Development environment cleanup script
set -e

# Stop any running processes
echo "Stopping running processes..."
pkill -f "uvicorn backend.app:app" || true
pkill -f "npm run dev" || true

# Remove virtual environment
echo "Removing virtual environment..."
rm -rf .venv

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