#!/bin/bash
set -e

# Frontend development startup script
echo "🔍 Checking frontend environment..."

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo "❌ Error: frontend directory not found!"
    exit 1
fi

# Load nvm from common locations
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

# Verify nvm is loaded
if ! command -v nvm &> /dev/null; then
    echo "❌ Error: nvm (Node Version Manager) is not installed or not available in this shell."
    echo "💡 Please install nvm: https://github.com/nvm-sh/nvm"
    exit 1
fi

# Change to frontend directory
cd frontend

# Use correct Node.js version
echo "📦 Using Node.js version from .nvmrc..."
if [ -f ".nvmrc" ]; then
    nvm use || nvm install || {
        echo "❌ Error: Failed to use or install Node.js version from .nvmrc"
        exit 1
    }
else
    echo "❌ Error: .nvmrc not found in frontend directory"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📥 Installing dependencies..."
    npm install
fi

# Start development server
echo "🚀 Starting development server..."
npm run dev 