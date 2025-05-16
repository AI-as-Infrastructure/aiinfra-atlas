/**
 * AWS Cognito authentication service for ATLAS.
 * Handles login/logout flows and token management.
 */

// Check if Cognito auth is enabled via environment variable
export const isCognitoEnabled = () => {
  return import.meta.env.VITE_USE_COGNITO_AUTH === 'true';
};

// Validate and get Cognito configuration from environment variables
export const getCognitoConfig = () => {
  // Get base URL for the application (works across environments)
  const baseUrl = window.location.origin;
  
  // Define environment variables with validation and fallbacks
  const config = {
    region: import.meta.env.VITE_COGNITO_REGION,
    userPoolId: import.meta.env.VITE_COGNITO_USERPOOL_ID,
    clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
    domain: import.meta.env.VITE_COGNITO_DOMAIN,
    oauthScope: import.meta.env.VITE_COGNITO_OAUTH_SCOPE || 'openid email profile',
  };
  
  // Get redirect URIs from environment with fallbacks
  const loginRedirectUri = import.meta.env.VITE_COGNITO_LOGIN_REDIRECT_URI || `${baseUrl}/callback`;
  const logoutRedirectUri = import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI || `${baseUrl}/logout.html`;
  const logoutEndpoint = import.meta.env.VITE_COGNITO_LOGOUT_ENDPOINT;
  
  // Warn about possible configuration issues
  if (!loginRedirectUri.includes('/callback')) {
    console.warn('Cognito login redirect URI does not contain "/callback" path which may cause issues. Current value:', loginRedirectUri);
  }
  
  if (!logoutRedirectUri.includes('/logout')) {
    console.warn('Cognito logout redirect URI does not contain "/logout" which may cause issues. Current value:', logoutRedirectUri);
  }
  
  // Return complete configuration
  return {
    ...config,
    loginRedirectUri,
    logoutRedirectUri,
    logoutEndpoint,
  };
};

// Constants for token storage
const TOKEN_STORAGE_KEY = 'atlas_cognito_tokens';

/**
 * Store tokens in browser storage
 * @param {Object} tokens - The tokens to store
 */
export const storeTokens = (tokens) => {
  if (!tokens) return;
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
};

/**
 * Get stored tokens from browser storage
 * @returns {Object|null} The stored tokens or null if not found
 */
export const getStoredTokens = () => {
  const tokensStr = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (!tokensStr) return null;
  
  try {
    return JSON.parse(tokensStr);
  } catch (error) {
    console.error('Error parsing stored tokens:', error);
    return null;
  }
};

/**
 * Clear stored tokens from browser storage
 */
export const clearTokens = () => {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
};

/**
 * Parse tokens from URL query params or hash fragment after Cognito redirect
 * @returns {Object|null} Parsed tokens or null if not found
 */
export const parseTokensFromUrl = () => {
  // Skip if Cognito is disabled
  if (!isCognitoEnabled()) return null;

  // Get the URL parts
  const hash = window.location.hash.substring(1);
  const query = window.location.search.substring(1);
  
  // First check for authorization code (preferred method with PKCE)
  if (query) {
    const params = new URLSearchParams(query);
    
    if (params.has('code')) {
      // Note: We now handle code grant in the Callback.vue component
      // by exchanging the code for tokens
      return { authCode: params.get('code') };
    }
  }
  
  // Fallback to implicit flow (legacy method)
  if (hash) {
    const params = new URLSearchParams(hash);
    
    if (params.has('id_token')) {
      return {
        idToken: params.get('id_token'),
        accessToken: params.get('access_token'),
        expiresIn: params.get('expires_in'),
        tokenType: params.get('token_type'),
      };
    }
  }
  
  return null;
};

/**
 * Check if user is authenticated by validating token existence
 * @returns {boolean} True if user has valid tokens
 */
export const isAuthenticated = () => {
  // Always return false if Cognito is disabled
  if (!isCognitoEnabled()) {
    console.log('Cognito authentication is disabled');
    return false;
  }
  
  // First, check directly in localStorage as a fallback
  let tokens = null;
  let directCheck = false;
  
  try {
    const rawTokens = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (rawTokens) {
      directCheck = true;
      tokens = JSON.parse(rawTokens);
      console.log('Direct localStorage check:', {
        found: true,
        hasIdToken: !!tokens?.idToken
      });
    }
  } catch (e) {
    console.error('Error reading directly from localStorage:', e);
  }
  
  // If direct check failed, try the normal method
  if (!directCheck || !tokens) {
    tokens = getStoredTokens();
    console.log('Using getStoredTokens() method:', {
      found: !!tokens,
      hasIdToken: !!tokens?.idToken
    });
  }
  
  const hasTokens = !!tokens && !!tokens.idToken;
  
  // Add debugging to trace authentication issues
  console.log('Auth check - Tokens exist:', hasTokens, 'Token storage key:', TOKEN_STORAGE_KEY);
  
  // If no tokens found, immediately return false
  if (!hasTokens) {
    console.log('No valid tokens found in storage');
    return false;
  }
  
  // Basic token validation - check if it's expired
  try {
    // Extract expiry from JWT without full validation
    const base64Url = tokens.idToken.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(base64));
    
    if (payload.exp) {
      const now = Math.floor(Date.now() / 1000);
      const isExpired = now >= payload.exp;
      console.log('Token expiry check:', isExpired ? 'EXPIRED' : 'valid', 
                 'Expires:', new Date(payload.exp * 1000).toISOString());
      
      if (isExpired) {
        console.log('Token is expired, clearing tokens from storage');
        clearTokens(); // Clear expired tokens to prevent authentication issues
        return false;
      }
      
      return true;
    }
  } catch (err) {
    console.error('Token validation error:', err);
    // Don't return false immediately, try the fallback
  }
  
  // Default fallback - if we have tokens but couldn't validate expiry
  return hasTokens;
};

/**
 * Extract user info from the ID token
 * @returns {Object|null} User information if authenticated
 */
export const getUserInfo = () => {
  if (!isAuthenticated()) {
    console.log('getUserInfo: Not authenticated');
    return null;
  }
  
  const tokens = getStoredTokens();
  if (!tokens || !tokens.idToken) {
    console.log('getUserInfo: No tokens or ID token found');
    return null;
  }
  
  // Check if this is a test token (for development/debugging)
  if (tokens.idToken.startsWith('test-id-token')) {
    console.log('getUserInfo: Detected test token, returning mock user');
    return {
      sub: 'test-user-id',
      email: 'test@example.com',
      name: 'Test User',
      email_verified: true
    };
  }
  
  try {
    // Check if the token has the correct JWT format (should have 2 dots)
    if (!tokens.idToken.includes('.') || tokens.idToken.split('.').length !== 3) {
      console.error('getUserInfo: Invalid JWT format');
      return null;
    }
    
    // ID token is a JWT - parse it without validation
    // (validation happens server-side)
    const base64Url = tokens.idToken.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('')
      .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join(''));
    
    const userInfo = JSON.parse(jsonPayload);
    console.log('getUserInfo: Successfully parsed user info', {
      sub: userInfo.sub?.substring(0, 5) + '...',
      email: userInfo.email ? 'present' : 'missing',
      name: userInfo.name ? 'present' : 'missing'
    });
    
    return userInfo;
  } catch (error) {
    console.error('Error parsing token:', error);
    return null;
  }
};

// Import utility functions for PKCE
import {
  generateRandomString,
  generateCodeChallenge,
  storeCodeVerifier,
  getCodeVerifier,
  clearCodeVerifier
} from './cognito-utils';

// Export the utilities for use in other components
export { generateRandomString, generateCodeChallenge };

/**
 * Redirect to Cognito login page using authorization code flow with PKCE
 */
export const login = async () => {
  if (!isCognitoEnabled()) return;
  
  // Always generate a fresh code verifier and state for security
  const { codeVerifier, state } = storeCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);
  
  console.log('Login process - PKCE flow starting with verifier and state:', {
    verifier: codeVerifier.substring(0, 10) + '...',
    state
  });
  
  const config = getCognitoConfig();
  const loginUrl = new URL(`https://${config.domain}/oauth2/authorize`);
  
  // Add query parameters for authorization code flow with PKCE
  loginUrl.searchParams.append('client_id', config.clientId);
  loginUrl.searchParams.append('response_type', 'code');
  loginUrl.searchParams.append('scope', config.oauthScope);
  loginUrl.searchParams.append('redirect_uri', config.loginRedirectUri);
  loginUrl.searchParams.append('code_challenge', codeChallenge);
  loginUrl.searchParams.append('code_challenge_method', 'S256');
  loginUrl.searchParams.append('state', state); // Include state parameter for improved security
  
  // Redirect to Cognito login
  window.location.href = loginUrl.toString();
};

/**
 * Redirect to Cognito logout page
 * 
 * This implements a two-phase logout process:
 * 1. Clear local tokens
 * 2. Redirect to Cognito's logout endpoint
 * 3. Cognito redirects to our logout-complete page
 * 4. Logout page ensures all cleanup is done and redirects to home
 */
export const logout = () => {
  if (!isCognitoEnabled()) return;
  
  // 1. Clear local tokens first
  clearTokens();
  
  const config = getCognitoConfig();
  
  // 2. Construct the Cognito logout URL
  const logoutUrl = new URL(config.logoutEndpoint);
  
  // Add query parameters
  logoutUrl.searchParams.append('client_id', config.clientId);
  logoutUrl.searchParams.append('logout_uri', config.logoutRedirectUri);
  
  // 3. Redirect to Cognito logout
  window.location.href = logoutUrl.toString();
};
