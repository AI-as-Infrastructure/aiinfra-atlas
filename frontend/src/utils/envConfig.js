/**
 * Environment Configuration Utility
 * 
 * This utility provides a consistent way to access environment variables in the React application.
 * It handles fallbacks and provides helpful console warnings in development mode when
 * required environment variables are missing.
 */

// Helper to get environment variables with fallbacks and warnings
const getEnvVar = (name, fallback = null, required = false) => {
  const value = process.env[name] || fallback;
  
  // In development, warn about missing required environment variables
  if (process.env.NODE_ENV === 'development' && required && !value) {
    console.warn(`⚠️ Required environment variable ${name} is not set!`);
  }
  
  return value;
};

// Application configuration derived from environment variables
const envConfig = {
  // Application settings
  appTitle: getEnvVar('REACT_APP_SITE_TITLE', 'ATLAS'),
  
  // Authentication settings
  auth: {
    issuerUrl: getEnvVar('REACT_APP_ISSUER_URL', '', true),
    clientId: getEnvVar('REACT_APP_CLIENT_ID', '', true),
    redirectUri: getEnvVar('REACT_APP_REDIRECT_URI', window.location.origin + '/callback', true),
    logoutUrl: getEnvVar('REACT_APP_LOGOUT_URL', '', true),
    oauthScope: getEnvVar('REACT_APP_OAUTH_SCOPE', 'openid profile email', true),
  },
  
  // API configuration
  api: {
    baseUrl: getEnvVar('REACT_APP_API_URL', window.location.origin),
    frontendUrl: getEnvVar('REACT_APP_FRONTEND_URL', window.location.origin),
  },
  
  // Feature flags
  features: {
    enableTelemetry: getEnvVar('REACT_APP_ENABLE_TELEMETRY', 'false') === 'true',
  }
};

export default envConfig;
