#!/bin/bash

# Check if the environment file is provided as an argument.
if [ -z "$1" ]; then
  echo "Usage: $0 <env_file>"
  exit 1
fi

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Handle the environment file path
if [[ "$1" == /* ]]; then
  # Absolute path
  ENV_FILE="$1"
else
  # Relative path - check if it includes 'config/' prefix
  if [[ "$1" == config/* ]] || [[ "$1" == ./config/* ]]; then
    ENV_FILE="$PROJECT_ROOT/$1"
  else
    ENV_FILE="$PROJECT_ROOT/config/$1"
  fi
fi

# Define paths for the template and output file.
TEMPLATE_PATH="$SCRIPT_DIR/public/logout.template.html"
OUTPUT_PATH="$SCRIPT_DIR/public/logout.html"

# Check if the template file exists.
if [ ! -f "$TEMPLATE_PATH" ]; then
  echo "Template file not found at: $TEMPLATE_PATH"
  exit 1
fi

# Check if the environment file exists.
if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found at: $ENV_FILE"
  exit 1
fi

# Extract the REACT_APP_FRONTEND_URL value from the environment file.
FRONTEND_URL=$(grep -oP '^REACT_APP_FRONTEND_URL=\K.*' "$ENV_FILE")

# Use a default value if the environment variable is not set.
if [ -z "$FRONTEND_URL" ]; then
  FRONTEND_URL="frontend-url-not-set"
fi

# Read the template file.
TEMPLATE_CONTENT=$(cat "$TEMPLATE_PATH")

# Replace the placeholder with the actual URL.
OUTPUT_CONTENT=${TEMPLATE_CONTENT//%%REACT_APP_FRONTEND_URL%%/$FRONTEND_URL}

# Write the output to the output file.
echo "$OUTPUT_CONTENT" > "$OUTPUT_PATH"

echo "logout.html generated successfully at: $OUTPUT_PATH"