#!/bin/bash
# setup_env.sh - Configure environment-specific variables for ATLAS

# Usage: ./setup_env.sh [dev|staging|prod]
# If no environment is specified, defaults to dev

set -e

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load the environment from .env file if it exists
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    # Extract ENVIRONMENT value from .env file
    ENV=$(grep -E '^ENVIRONMENT=' "$ENV_FILE" | cut -d '=' -f2)
    # Remove any quotes
    ENV=$(echo "$ENV" | tr -d '"' | tr -d "'")
    # Default to dev if not found or empty
    ENV=${ENV:-dev}
else
    # Default to dev if .env doesn't exist
    ENV="dev"
    echo -e "${YELLOW}Warning: .env file not found. Using default environment: ${ENV}${NC}"
fi

# Convert environment to uppercase using portable method
ENV_UPPER=$(echo "$ENV" | tr '[:lower:]' '[:upper:]')

echo -e "${YELLOW}Setting up environment for: ${ENV}${NC}"

# Validate environment
if [[ "$ENV" != "dev" && "$ENV" != "staging" && "$ENV" != "prod" ]]; then
    echo -e "${RED}Error: Invalid environment value in .env file. Use 'dev', 'staging', or 'prod'${NC}"
    exit 1
fi

# Function to update environment variables in .env file
update_env_vars() {
    local env_file="$SCRIPT_DIR/.env"
    
    # Check if .env file exists
    if [ ! -f "$env_file" ]; then
        echo -e "${RED}Error: .env file not found at $env_file${NC}"
        echo -e "${YELLOW}Please copy .env.template to .env first${NC}"
        exit 1
    fi
    
    # Update ENVIRONMENT variable if it exists - macOS compatible version
    if grep -q "^ENVIRONMENT=" "$env_file"; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s/^ENVIRONMENT=.*/ENVIRONMENT=$ENV/" "$env_file"
        else
            sed -i "s/^ENVIRONMENT=.*/ENVIRONMENT=$ENV/" "$env_file"
        fi
    else
        echo "ENVIRONMENT=$ENV" >> "$env_file"
    fi
    
    # Update SERVER_NAME based on environment - macOS compatible version
    if [[ "$ENV" == "dev" ]]; then
        if grep -q "^SERVER_NAME=" "$env_file"; then
            if [[ "$(uname)" == "Darwin" ]]; then
                sed -i '' "s/^SERVER_NAME=.*/SERVER_NAME=localhost/" "$env_file"
            else
                sed -i "s/^SERVER_NAME=.*/SERVER_NAME=localhost/" "$env_file"
            fi
        else
            echo "SERVER_NAME=localhost" >> "$env_file"
        fi
    elif [[ "$ENV" == "staging" ]]; then
        if grep -q "^SERVER_NAME=" "$env_file"; then
            if [[ "$(uname)" == "Darwin" ]]; then
                sed -i '' "s/^SERVER_NAME=.*/SERVER_NAME=ubuntu.local/" "$env_file"
            else
                sed -i "s/^SERVER_NAME=.*/SERVER_NAME=ubuntu.local/" "$env_file"
            fi
        else
            echo "SERVER_NAME=ubuntu.local" >> "$env_file"
        fi
    elif [[ "$ENV" == "prod" ]]; then
        # You can customize this for your production domain
        if grep -q "^SERVER_NAME=" "$env_file"; then
            if [[ "$(uname)" == "Darwin" ]]; then
                sed -i '' "s/^SERVER_NAME=.*/SERVER_NAME=your-production-domain.com/" "$env_file"
            else
                sed -i "s/^SERVER_NAME=.*/SERVER_NAME=your-production-domain.com/" "$env_file"
            fi
        else
            echo "SERVER_NAME=your-production-domain.com" >> "$env_file"
        fi
    fi
    
    # Update HOST to match SERVER_NAME - macOS compatible version
    if grep -q "^HOST=" "$env_file"; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s/^HOST=.*/HOST=\${SERVER_NAME}/" "$env_file"
        else
            sed -i "s/^HOST=.*/HOST=\${SERVER_NAME}/" "$env_file"
        fi
    else
        echo "HOST=\${SERVER_NAME}" >> "$env_file"
    fi
    
    # Update PHOENIX_PROJECT_NAME based on environment - macOS compatible version
    if grep -q "^PHOENIX_PROJECT_NAME=" "$env_file"; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s/^PHOENIX_PROJECT_NAME=.*/PHOENIX_PROJECT_NAME=\${PHOENIX_PROJECT_NAME_$ENV_UPPER}/" "$env_file"
        else
            sed -i "s/^PHOENIX_PROJECT_NAME=.*/PHOENIX_PROJECT_NAME=\${PHOENIX_PROJECT_NAME_$ENV_UPPER}/" "$env_file"
        fi
    else
        echo "PHOENIX_PROJECT_NAME=\${PHOENIX_PROJECT_NAME_$ENV_UPPER}" >> "$env_file"
    fi
    
    echo -e "${GREEN}Updated environment variables in .env for ${ENV} environment${NC}"
}

# Function to verify Redis password in .secrets file and set REDIS_PASSWORD
verify_redis_password() {
    local secrets_file="$SCRIPT_DIR/.secrets"
    local redis_var="REDIS_${ENV_UPPER}_PASSWORD"
    
    # Check if .secrets file exists
    if [ ! -f "$secrets_file" ]; then
        echo -e "${RED}Error: .secrets file not found at $secrets_file${NC}"
        echo -e "${YELLOW}Please copy .secrets.template to .secrets first${NC}"
        exit 1
    fi
    
    # Check if Redis password for the environment exists
    if ! grep -q "^$redis_var=" "$secrets_file"; then
        echo -e "${RED}Error: $redis_var not found in .secrets file${NC}"
        exit 1
    fi
    
    # Extract the environment-specific Redis password
    local redis_pwd=$(grep "^$redis_var=" "$secrets_file" | cut -d= -f2 | tr -d '"')
    
    # Set the generic REDIS_PASSWORD in .secrets file - macOS compatible version
    if grep -q "^REDIS_PASSWORD=" "$secrets_file"; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=\"$redis_pwd\"/" "$secrets_file"
        else
            sed -i "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=\"$redis_pwd\"/" "$secrets_file"
        fi
    else
        echo "REDIS_PASSWORD=\"$redis_pwd\"" >> "$secrets_file"
    fi
    
    echo -e "${GREEN}Verified Redis password for ${ENV} environment${NC}"
}

verify_api_keys() {
    local secrets_file="$SCRIPT_DIR/.secrets"
    local template_file="$SCRIPT_DIR/.secrets.template"
    local missing_keys=0
    
    # Check if template file exists
    if [ ! -f "$template_file" ]; then
        echo -e "${YELLOW}Warning: .secrets.template file not found at $template_file${NC}"
        echo -e "${YELLOW}Cannot verify API keys against template${NC}"
        return
    fi
    
    # Extract all API key entries from the template file
    # This assumes API keys have "_API_KEY" or "_KEY" in their name
    local api_keys=$(grep -E "_(API_)?KEY=" "$template_file" | cut -d= -f1)
    
    # Check each API key
    for key in $api_keys; do
        # Skip REDIS passwords as they're handled separately
        if [[ "$key" == REDIS* ]]; then
            continue
        fi
        
        # Check if the key exists and is not set to default
        if ! grep -q "^$key=" "$secrets_file" || grep -q "^$key=\"<DEFAULT>\"" "$secrets_file"; then
            # Get a friendly name for the service
            local service_name=$(echo "$key" | sed -E 's/_API_KEY|_KEY//' | tr '[:upper:]' '[:lower:]')
            service_name="${service_name^}"
            
            echo -e "${YELLOW}Warning: $key not found or set to default in .secrets file${NC}"
            echo -e "${YELLOW}$service_name services may not be available${NC}"
            missing_keys=$((missing_keys+1))
        fi
    done
    
    if [ $missing_keys -gt 0 ]; then
        echo -e "${YELLOW}Some API keys are missing or set to default values. The application may have limited functionality.${NC}"
        echo -e "${YELLOW}Edit $secrets_file to add the missing API keys${NC}"
    else
        echo -e "${GREEN}All API keys verified${NC}"
    fi
}

# Main execution

# 1. Update environment variables in .env file
update_env_vars

# 2. Verify Redis password in .secrets file
verify_redis_password

# 3. Verify required API keys
verify_api_keys

# 4. Run the React environment setup script
if [ -f "$SCRIPT_DIR/setup_react_env.sh" ]; then
    echo -e "${YELLOW}Setting up React environment...${NC}"
    # Export environment variables for child script to use
    export ENV ENV_UPPER
    # Ensure bash is used to run the React setup script
    chmod +x "$SCRIPT_DIR/setup_react_env.sh"
    bash "$SCRIPT_DIR/setup_react_env.sh"
fi

echo -e "${GREEN}Environment setup complete for: ${ENV}${NC}"
echo -e "${YELLOW}You can now run 'make ${ENV}' to start the application${NC}"