#!/bin/bash
#=============================================================================
# ATLAS STAGING DEPLOYMENT DIAGNOSTIC TOOL
#=============================================================================
# 
# PURPOSE:
#   This script analyzes a local staging deployment to diagnose issues.
#   It checks for common problems that could cause 500 errors or other failures.
# 
# USAGE:
#   ./deploy/staging/staging_test.sh
# 
# WHAT IT CHECKS:
#   - Environment configuration
#   - Python imports and dependencies
#   - Service status
#   - File permissions
#   - Nginx configuration
#   - System resources
#   - Log analysis
#
#=============================================================================

set -e

# Color codes for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Settings
APP_NAME="atlas"
APP_DIR="/opt/$APP_NAME"
CURRENT_USER=$(whoami)

echo -e "${BLUE}=== ATLAS STAGING DEPLOYMENT DIAGNOSTIC TOOL ===${NC}"
echo "Running comprehensive tests on your staging deployment..."
echo ""

# Create a temporary directory for test files
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Function to check if a command was successful
check_result() {
    local result=$?
    local message=$1
    if [ $result -eq 0 ]; then
        echo -e "  ${GREEN}✓ $message${NC}"
        return 0
    else
        echo -e "  ${RED}✗ $message${NC}"
        return 1
    fi
}

# Function to run a test with header
run_test() {
    local title=$1
    echo -e "${YELLOW}$title${NC}"
}

# 1. Basic system checks
run_test "🖥️  SYSTEM CHECKS"

# Check if the application directory exists
if [ -d "$APP_DIR" ]; then
    echo -e "  ${GREEN}✓ Application directory exists${NC}"
else
    echo -e "  ${RED}✗ Application directory not found at $APP_DIR${NC}"
    echo -e "    Run 'make sl' to deploy the application first"
    exit 1
fi

# Check basic system resources
echo "  System resources:"
echo "    $(free -h | grep Mem | awk '{print "Memory: " $3 " used / " $2 " total"}')"
echo "    $(df -h / | tail -1 | awk '{print "Disk: " $3 " used / " $2 " total (" $5 " used)"}')"
echo "    $(uptime | awk '{print "Load: " $(NF-2) " " $(NF-1) " " $NF}')"

# 2. Service status checks
run_test "🔄 SERVICE STATUS"

# Check if Gunicorn service is active
if systemctl is-active --quiet gunicorn; then
    echo -e "  ${GREEN}✓ Gunicorn service is active${NC}"
else
    echo -e "  ${RED}✗ Gunicorn service is not active${NC}"
    echo "    Status details:"
    systemctl status gunicorn | head -n 10
fi

# Check if Nginx service is active
if systemctl is-active --quiet nginx; then
    echo -e "  ${GREEN}✓ Nginx service is active${NC}"
else
    echo -e "  ${RED}✗ Nginx service is not active${NC}"
    systemctl status nginx | head -n 10
fi

# 3. Configuration checks
run_test "📄 CONFIGURATION CHECKS"

# Check Nginx configuration
echo "  Testing Nginx configuration..."
sudo nginx -t 2>&1 | sed 's/^/    /'
check_result "Nginx configuration is valid"

# Check Gunicorn service file
if [ -f "/etc/systemd/system/gunicorn.service" ]; then
    echo -e "  ${GREEN}✓ Gunicorn service file exists${NC}"
    echo "    Service file details:"
    grep -v "^#" /etc/systemd/system/gunicorn.service | grep -v "^$" | sed 's/^/      /'
else
    echo -e "  ${RED}✗ Gunicorn service file not found${NC}"
fi

# 4. Environment file checks
run_test "🌐 ENVIRONMENT FILE CHECKS"

if [ -f "$APP_DIR/config/.env.staging" ]; then
    echo -e "  ${GREEN}✓ .env.staging file exists${NC}"
    
    # Check important URL settings
    grep -E "VITE_API_URL|CORS_ORIGINS|API_BASE_URL|WS_BASE_URL" "$APP_DIR/config/.env.staging" | sed 's/^/    /'
    
    # Verify HTTPS in VITE_API_URL
    if grep -q "VITE_API_URL=https://" "$APP_DIR/config/.env.staging"; then
        echo -e "  ${GREEN}✓ VITE_API_URL uses HTTPS${NC}"
    else
        echo -e "  ${RED}✗ VITE_API_URL does not use HTTPS${NC}"
        echo "    This will cause frontend to API communication issues"
    fi
else
    echo -e "  ${RED}✗ .env.staging file not found${NC}"
fi

# 5. Python environment checks
run_test "🐍 PYTHON ENVIRONMENT CHECKS"

# Check Python version
if [ -f "$APP_DIR/.venv/bin/python" ]; then
    PYTHON_VERSION=$("$APP_DIR/.venv/bin/python" --version 2>&1)
    echo "  Python version: $PYTHON_VERSION"
    
    # Create a test script to check imports
    cat > "$TEMP_DIR/test_imports.py" << EOL
import sys
import os

print("Python version:", sys.version)
print("Python path:", sys.path)

modules_to_check = [
    "backend", 
    "backend.app",
    "fastapi",
    "uvicorn",
    "gunicorn",
    "pydantic"
]

failed = False
for module in modules_to_check:
    try:
        __import__(module)
        print(f"✓ Successfully imported {module}")
    except ImportError as e:
        print(f"✗ Failed to import {module}: {e}")
        failed = True

# Test if app can be imported and created
try:
    from backend.app import app
    print("✓ Successfully imported app from backend.app")
except Exception as e:
    print(f"✗ Failed to import app from backend.app: {e}")
    failed = True

sys.exit(1 if failed else 0)
EOL

    echo "  Testing Python imports..."
    if cd "$APP_DIR" && .venv/bin/python "$TEMP_DIR/test_imports.py"; then
        echo -e "  ${GREEN}✓ All Python imports successful${NC}"
    else
        echo -e "  ${RED}✗ Some Python imports failed${NC}"
    fi
    
    # Check for the Python path file
    if [ -f "$APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth" ]; then
        echo -e "  ${GREEN}✓ Python path file exists${NC}"
        echo "    Content: $(cat "$APP_DIR/.venv/lib/python3.10/site-packages/atlas.pth")"
    else
        echo -e "  ${RED}✗ Python path file not found${NC}"
        echo "    This may cause import errors."
    fi
else
    echo -e "  ${RED}✗ Python virtual environment not found${NC}"
fi

# 6. File permission checks
run_test "🔒 FILE PERMISSION CHECKS"

# Check app directory ownership
APP_OWNER=$(stat -c '%U:%G' "$APP_DIR")
echo "  App directory owner: $APP_OWNER"
if [ "$APP_OWNER" = "$CURRENT_USER:$CURRENT_USER" ]; then
    echo -e "  ${GREEN}✓ App directory has correct ownership${NC}"
else
    echo -e "  ${YELLOW}⚠️ App directory has unexpected ownership${NC}"
    echo "    Expected: $CURRENT_USER:$CURRENT_USER"
fi

# Check log directory
if [ -d "/var/log/$APP_NAME" ]; then
    LOG_OWNER=$(stat -c '%U:%G' "/var/log/$APP_NAME")
    echo "  Log directory owner: $LOG_OWNER"
else
    echo -e "  ${RED}✗ Log directory not found${NC}"
fi

# 7. SSL certificate checks
run_test "🔐 SSL CERTIFICATE CHECKS"

CERT_DIR="/etc/letsencrypt/live/$APP_NAME"
if [ -d "$CERT_DIR" ]; then
    echo -e "  ${GREEN}✓ Certificate directory exists${NC}"
    
    if [ -f "$CERT_DIR/fullchain.pem" ] && [ -f "$CERT_DIR/privkey.pem" ]; then
        echo -e "  ${GREEN}✓ SSL certificate files exist${NC}"
        # Check certificate expiration
        CERT_EXPIRY=$(sudo openssl x509 -enddate -noout -in "$CERT_DIR/fullchain.pem" | cut -d= -f2)
        echo "  Certificate expires: $CERT_EXPIRY"
        
        # Check permissions
        CERT_PERMS=$(sudo stat -c '%a' "$CERT_DIR/privkey.pem")
        CERT_OWNER=$(sudo stat -c '%U:%G' "$CERT_DIR/privkey.pem")
        echo "  Private key permissions: $CERT_PERMS"
        echo "  Private key owner: $CERT_OWNER"
    else
        echo -e "  ${RED}✗ SSL certificate files missing${NC}"
    fi
else
    echo -e "  ${RED}✗ Certificate directory not found${NC}"
fi

# 8. Log analysis
run_test "📋 LOG ANALYSIS"

# Check Gunicorn logs
echo "  Last 10 lines of Gunicorn logs:"
sudo journalctl -u gunicorn -n 10 --no-pager | sed 's/^/    /'

# Check Nginx error logs
echo "  Last 10 lines of Nginx error logs:"
sudo tail -n 10 /var/log/nginx/error.log | sed 's/^/    /'

# 11. Logs directory check
run_test "📁 LOCAL LOGS DIRECTORY"

LOGS_DIR="$(dirname "$(dirname "$PWD")")/deploy/staging/logs"
if [ -d "$LOGS_DIR" ]; then
    echo -e "  ${GREEN}✓ Logs directory exists${NC}"
    
    # List log files
    echo "  Log files:"
    find "$LOGS_DIR" -name "*.log" | while read log_file; do
        echo "    $(basename "$log_file"): $(du -h "$log_file" | cut -f1)"
        echo "      Last 3 lines:"
        tail -n 3 "$log_file" | sed 's/^/        /'
    done
    
    # Check if logs are being written
    RECENT_LOGS=$(find "$LOGS_DIR" -name "*.log" -mmin -60 | wc -l)
    if [ "$RECENT_LOGS" -gt 0 ]; then
        echo -e "  ${GREEN}✓ $RECENT_LOGS log files updated in the last hour${NC}"
    else
        echo -e "  ${YELLOW}⚠️ No log files updated in the last hour${NC}"
    fi
else
    echo -e "  ${RED}✗ Logs directory not found at $LOGS_DIR${NC}"
    echo "    Create it with: mkdir -p $LOGS_DIR"
fi

# 9. Network checks
run_test "🌐 NETWORK CHECKS"

# Check if port 8000 is listening
if ss -tuln | grep -q ":8000"; then
    echo -e "  ${GREEN}✓ Gunicorn is listening on port 8000${NC}"
else
    echo -e "  ${RED}✗ Gunicorn is not listening on port 8000${NC}"
fi

# Check if ports 80 and 443 are listening
if ss -tuln | grep -q ":80"; then
    echo -e "  ${GREEN}✓ Nginx is listening on port 80${NC}"
else
    echo -e "  ${RED}✗ Nginx is not listening on port 80${NC}"
fi

if ss -tuln | grep -q ":443"; then
    echo -e "  ${GREEN}✓ Nginx is listening on port 443${NC}"
else
    echo -e "  ${RED}✗ Nginx is not listening on port 443${NC}"
fi

# 10. Manual test of API endpoint
run_test "🧪 API ENDPOINT TEST"

echo "  Testing API health endpoint..."
if curl -s -o /dev/null -w "%{http_code}" https://localhost/api/health 2>/dev/null | grep -q "200"; then
    echo -e "  ${GREEN}✓ API health endpoint returns 200 OK${NC}"
else
    echo -e "  ${RED}✗ API health endpoint test failed${NC}"
    echo "    Response from API (ignoring SSL errors):"
    curl -k -v https://localhost/api/health 2>&1 | sed 's/^/    /'
fi

# Final summary
echo ""
echo -e "${BLUE}=== DIAGNOSTIC SUMMARY ===${NC}"
echo "If you're seeing 500 Internal Server Error, check the following common issues:"
echo ""
echo "1. Python version mismatch"
echo "2. Missing Python dependencies"
echo "3. Import errors in the application"
echo "4. Wrong file permissions"
echo "5. Incorrect environment settings"
echo "6. Certificate issues"
echo ""
echo "For more detailed debugging, try running Gunicorn manually with:"
echo "cd $APP_DIR && .venv/bin/python -m gunicorn backend.app:app -k uvicorn.workers.UvicornWorker --log-level debug"
echo ""
echo "Diagnostic complete." 