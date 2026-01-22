#!/bin/bash

# Stop wizard/development servers gracefully
# This script stops both backend (port 8000) and frontend (port 5173) servers

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🛑 Stopping wizard servers..."

# Function to gracefully stop a process on a specific port
stop_port() {
    local port=$1
    local service=$2

    # Find processes listening on the port
    pids=$(lsof -ti:$port 2>/dev/null)

    if [ -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  No $service server found on port $port${NC}"
        return 0
    fi

    echo -e "📍 Found $service server on port $port (PID: $pids)"

    # Try graceful shutdown first (SIGTERM)
    echo -e "   Sending graceful shutdown signal..."
    kill -TERM $pids 2>/dev/null

    # Wait up to 5 seconds for graceful shutdown
    for i in {1..5}; do
        sleep 1
        if ! kill -0 $pids 2>/dev/null; then
            echo -e "${GREEN}✅ $service server stopped gracefully${NC}"
            return 0
        fi
        echo -n "."
    done
    echo ""

    # If still running, force kill (SIGKILL)
    if kill -0 $pids 2>/dev/null; then
        echo -e "${YELLOW}   Process still running, forcing shutdown...${NC}"
        kill -9 $pids 2>/dev/null
        sleep 1
        if ! kill -0 $pids 2>/dev/null; then
            echo -e "${GREEN}✅ $service server stopped (forced)${NC}"
            return 0
        else
            echo -e "${RED}❌ Failed to stop $service server${NC}"
            return 1
        fi
    fi
}

# Stop backend server (port 8000)
stop_port 8000 "Backend"

# Stop frontend server (port 5173)
stop_port 5173 "Frontend"

echo ""
echo -e "${GREEN}✅ Wizard servers stopped${NC}"
echo ""
echo "To restart the wizard:"
echo "  1. Backend: make b"
echo "  2. Frontend: make f"
echo "  3. Open: http://localhost:5173/corpus-wizard"
