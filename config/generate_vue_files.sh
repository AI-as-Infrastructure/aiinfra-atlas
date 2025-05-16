#!/bin/bash

# Define source and destination paths
ENV_TEMPLATE="config/.env.development"
FRONTEND_ENV="frontend/.env"
LOGOUT_TEMPLATE="frontend/public/logout.template.html"
LOGOUT_HTML="frontend/public/logout.html"

# Get the VITE_API_URL from the environment template
VITE_API_URL=$(grep "VITE_API_URL" $ENV_TEMPLATE | cut -d "=" -f2)

# Generate frontend/.env file
echo "Generating frontend environment file..."
cp $ENV_TEMPLATE $FRONTEND_ENV

# Generate logout.html from template
echo "Generating logout.html with API URL: $VITE_API_URL"
if [ -f "$LOGOUT_TEMPLATE" ]; then
    sed "s|__VITE_API_URL__|$VITE_API_URL|g" $LOGOUT_TEMPLATE > $LOGOUT_HTML
    echo "Logout page generated successfully."
else
    echo "Error: Logout template file not found at $LOGOUT_TEMPLATE"
    exit 1
fi

echo "Frontend files generation complete." 