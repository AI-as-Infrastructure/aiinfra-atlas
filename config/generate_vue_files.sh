#!/bin/bash

# Get environment directly - no fallback, must be explicitly set
if [ -z "$ENVIRONMENT" ]; then
    echo "ERROR: ENVIRONMENT variable is not set"
    echo "Please set ENVIRONMENT to 'development', 'staging', or 'production' in your .env(development, staging, production) file"
    exit 1
fi

echo "Using environment: $ENVIRONMENT"

# Get the script's directory to use as base for relative paths
SCRIPT_DIR=$(dirname "$(realpath "$0")")

echo "Script directory: $SCRIPT_DIR"

# Define source and destination paths based on environment
ENV_TEMPLATE="$SCRIPT_DIR/.env.$ENVIRONMENT"
FRONTEND_ENV="$SCRIPT_DIR/../frontend/.env"
LOGOUT_TEMPLATE="$SCRIPT_DIR/../frontend/public/logout.template.html"
LOGOUT_HTML="$SCRIPT_DIR/../frontend/public/logout.html"

# Debug output
echo "Environment file path: $ENV_TEMPLATE"
echo "Frontend env path: $FRONTEND_ENV"
echo "Logout template path: $LOGOUT_TEMPLATE"

# Check if the environment file exists
if [ ! -f "$ENV_TEMPLATE" ]; then
    echo "Error: Environment file $ENV_TEMPLATE not found"
    # List contents of script directory for debugging
    echo "Contents of $SCRIPT_DIR:"
    ls -la "$SCRIPT_DIR/"
    exit 1
fi

# Extract environment variables needed for the logout page
VITE_API_URL=$(grep "^VITE_API_URL=" "$ENV_TEMPLATE" | cut -d "=" -f2)

# Derive VITE_AUTH_METHOD from AUTH_METHOD (single source of truth)
# Operators set AUTH_METHOD once; VITE_AUTH_METHOD is generated automatically for the frontend.
# Shell environment AUTH_METHOD (e.g. from Cloudflare override) takes precedence over the file value.
FILE_AUTH_METHOD=$(grep "^AUTH_METHOD=" "$ENV_TEMPLATE" | cut -d "=" -f2 || echo "none")
AUTH_METHOD="${AUTH_METHOD:-$FILE_AUTH_METHOD}"
AUTH_METHOD="${AUTH_METHOD:-none}"
VITE_AUTH_METHOD="$AUTH_METHOD"
echo "Derived VITE_AUTH_METHOD=$VITE_AUTH_METHOD from AUTH_METHOD=$AUTH_METHOD (file had: $FILE_AUTH_METHOD)"

# Extract Cognito variables if they exist
VITE_COGNITO_LOGOUT_ENDPOINT=$(grep "^VITE_COGNITO_LOGOUT_ENDPOINT=" "$ENV_TEMPLATE" | cut -d "=" -f2 || echo "")
VITE_COGNITO_CLIENT_ID=$(grep "^VITE_COGNITO_CLIENT_ID=" "$ENV_TEMPLATE" | cut -d "=" -f2 || echo "")
VITE_COGNITO_LOGOUT_REDIRECT_URI=$(grep "^VITE_COGNITO_LOGOUT_REDIRECT_URI=" "$ENV_TEMPLATE" | cut -d "=" -f2 || echo "")

# Generate frontend/.env file - only extract VITE_ variables
echo "Generating frontend environment file from $ENV_TEMPLATE..."
grep -E '^VITE_' "$ENV_TEMPLATE" > "$FRONTEND_ENV"
# Append derived VITE_AUTH_METHOD (replacing any existing line from the env file)
# Remove any VITE_AUTH_METHOD line that may have come from the env file (backward compat)
sed -i '/^VITE_AUTH_METHOD=/d' "$FRONTEND_ENV"
# Write the derived value
echo "VITE_AUTH_METHOD=$VITE_AUTH_METHOD" >> "$FRONTEND_ENV"
echo "Extracted VITE_ variables and derived VITE_AUTH_METHOD=$VITE_AUTH_METHOD"

# Generate logout.html from template
echo "Generating logout.html with API URL: $VITE_API_URL"
if [ -f "$LOGOUT_TEMPLATE" ]; then
    # Replace all environment variables in the template
    sed -e "s|__VITE_API_URL__|$VITE_API_URL|g" \
        -e "s|__VITE_AUTH_METHOD__|$VITE_AUTH_METHOD|g" \
        -e "s|__VITE_COGNITO_LOGOUT_ENDPOINT__|$VITE_COGNITO_LOGOUT_ENDPOINT|g" \
        -e "s|__VITE_COGNITO_CLIENT_ID__|$VITE_COGNITO_CLIENT_ID|g" \
        -e "s|__VITE_COGNITO_LOGOUT_REDIRECT_URI__|$VITE_COGNITO_LOGOUT_REDIRECT_URI|g" \
        "$LOGOUT_TEMPLATE" > "$LOGOUT_HTML"
    
    echo "Logout page generated successfully:"
    echo "  - Auth Method: $VITE_AUTH_METHOD (derived from AUTH_METHOD)"
    echo "  - API URL: $VITE_API_URL"
    echo "  - Cognito Logout Endpoint: ${VITE_COGNITO_LOGOUT_ENDPOINT:-Not set}"
    echo "  - Cognito Client ID: ${VITE_COGNITO_CLIENT_ID:-Not set}"
    echo "  - Cognito Logout Redirect URI: ${VITE_COGNITO_LOGOUT_REDIRECT_URI:-Not set}"
else
    echo "Error: Logout template file not found at $LOGOUT_TEMPLATE"
    exit 1
fi

echo "Frontend files generation complete for $ENVIRONMENT environment." 