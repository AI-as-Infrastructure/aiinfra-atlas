/**
 * AWS Cognito authentication using AWS Amplify
 * Following AWS recommended approach for SPA authentication
 */

import { Auth } from 'aws-amplify';
import { Amplify } from 'aws-amplify';

// Initialize Amplify with Cognito configuration
export const configureAmplify = () => {
  // Get configuration from environment variables
  const region = import.meta.env.VITE_COGNITO_REGION;
  const userPoolId = import.meta.env.VITE_COGNITO_USERPOOL_ID;
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
  const domain = import.meta.env.VITE_COGNITO_DOMAIN;
  const redirectSignIn = import.meta.env.VITE_COGNITO_LOGIN_REDIRECT_URI || `${window.location.origin}/callback`;
  const redirectSignOut = import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI || `${window.location.origin}/logout.html`;
  
  // Configure Amplify
  Amplify.configure({
    Auth: {
      region,
      userPoolId,
      userPoolWebClientId: clientId,
      oauth: {
        domain,
        scope: ['email', 'profile', 'openid'],
        redirectSignIn,
        redirectSignOut,
        responseType: 'code',
      },
    },
  });
  
  console.log('Amplify configured with Cognito');
};

/**
 * Check if Cognito auth is enabled
 */
export const isCognitoEnabled = () => {
  return import.meta.env.VITE_USE_COGNITO_AUTH === 'true';
};

/**
 * Initiate login process with Cognito Hosted UI
 * 
 * This function initiates the login process by redirecting to the Cognito Hosted UI.
 * It follows the authorization code flow with PKCE as implemented in the existing solution.
 */
export const login = async () => {
  if (!isCognitoEnabled()) return;
  
  try {
    console.log('Initiating Cognito login...');
    
    // First, completely clear any existing auth state
    try {
      // Sign out from Amplify
      await Auth.signOut({ global: true });
    } catch (e) {
      // Ignore errors during signout
      console.log('Pre-login cleanup:', e);
    }
    
    // Clear all Cognito-related items from local storage
    Object.keys(localStorage)
      .filter(key => key.startsWith('CognitoIdentityServiceProvider') || 
                     key.startsWith('amplify') || 
                     key.startsWith('aws'))
      .forEach(key => localStorage.removeItem(key));
    
    // Clear session storage items that might interfere
    Object.keys(sessionStorage)
      .filter(key => key.startsWith('CognitoIdentityServiceProvider') || 
                     key.startsWith('amplify') || 
                     key.startsWith('aws'))
      .forEach(key => sessionStorage.removeItem(key));
    
    console.log('Storage cleared, reconfiguring Amplify');
    
    // Reconfigure Amplify to ensure fresh state
    configureAmplify();
    
    // Use Amplify's federatedSignIn for a fresh login attempt
    // This will handle the PKCE flow properly
    console.log('Starting fresh login attempt with Amplify');
    await Auth.federatedSignIn();
  } catch (error) {
    console.error('Login error:', error);
    
    // If Amplify's method fails, fall back to manual URL construction
    try {
      // Get configuration from environment variables
      const config = {
        domain: import.meta.env.VITE_COGNITO_DOMAIN,
        clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
        redirectUri: import.meta.env.VITE_COGNITO_LOGIN_REDIRECT_URI,
        scope: import.meta.env.VITE_COGNITO_OAUTH_SCOPE || 'openid email profile'
      };
      
      // Generate a unique state parameter
      const state = Math.random().toString(36).substring(2, 15);
      
      // Construct the Cognito login URL
      const loginUrl = new URL(`https://${config.domain}/oauth2/authorize`);
      
      // Add query parameters
      loginUrl.searchParams.append('client_id', config.clientId);
      loginUrl.searchParams.append('response_type', 'code');
      loginUrl.searchParams.append('scope', config.scope);
      loginUrl.searchParams.append('redirect_uri', config.redirectUri);
      loginUrl.searchParams.append('state', state);
      
      console.log('Fallback: Redirecting to manual login URL');
      window.location.href = loginUrl.toString();
    } catch (fallbackError) {
      console.error('Fallback login error:', fallbackError);
      window.location.href = '/login';
    }
  }
};

/**
 * Handle the callback from Cognito
 * This is called after the user is redirected back from Cognito
 */
export const handleCallback = async () => {
  try {
    console.log('Processing authentication callback...');
    
    // Get the URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    
    if (!code) {
      throw new Error('No authorization code found in URL');
    }
    
    console.log('Authorization code received, exchanging for tokens...');
    
    // First, ensure Amplify is properly configured
    configureAmplify();
    
    // Try to get the current session - this will trigger the code exchange
    try {
      // This will force Amplify to process the current URL and exchange the code for tokens
      await Auth.currentSession();
      console.log('Code exchange successful');
    } catch (sessionError) {
      console.error('Error getting current session:', sessionError);
      // If there's an error with the current session, try a different approach
      try {
        // Try to handle the auth response directly
        console.log('Trying alternative code exchange method...');
        await Auth.handleAuthResponse(window.location.href);
        console.log('Alternative code exchange successful');
      } catch (handleError) {
        console.error('Error handling auth response:', handleError);
        throw new Error(`Failed to exchange code: ${handleError.message || '400'}`);
      }
    }
    
    // After successful code exchange, get the authenticated user
    try {
      const user = await Auth.currentAuthenticatedUser();
      console.log('Authentication successful');
      return user;
    } catch (userError) {
      console.error('Error getting authenticated user:', userError);
      throw new Error('Failed to get user after successful code exchange');
    }
  } catch (error) {
    console.error('Callback error:', error);
    
    // If the error is related to code exchange, provide a more helpful message
    if (error.message && error.message.includes('Failed to exchange code')) {
      throw new Error('Failed to exchange authorization code. This may be due to an expired or already used code. Please try logging in again.');
    }
    
    throw error;
  }
};

/**
 * Logout the user
 * 
 * This implements a secure two-phase logout process using Cognito's logout endpoint:
 * 1. Clear local tokens with Amplify's signOut method
 * 2. Redirect to Cognito's logout endpoint
 * 3. Cognito redirects to our /logout.html route
 * 4. Our Vue router handles the /logout.html route and redirects to login
 */
export const logout = async () => {
  if (!isCognitoEnabled()) return;
  
  try {
    console.log('Logging out...');
    
    // First try to use Amplify's signOut method to clear local tokens
    await Auth.signOut();
    
    // Then do a manual redirect to Cognito's logout endpoint for server-side session invalidation
    const config = {
      domain: import.meta.env.VITE_COGNITO_DOMAIN,
      clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      logoutEndpoint: import.meta.env.VITE_COGNITO_LOGOUT_ENDPOINT,
      // Use the environment variable for the logout redirect URI
      logoutRedirectUri: import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI
    };
    
    // Construct the Cognito logout URL
    const logoutUrl = new URL(config.logoutEndpoint);
    
    // Add query parameters
    logoutUrl.searchParams.append('client_id', config.clientId);
    // Use logout_uri as per AWS documentation
    logoutUrl.searchParams.append('logout_uri', config.logoutRedirectUri);
    
    // Log the full URL for debugging
    console.log('Logout URL:', logoutUrl.toString());
    console.log('Logout redirect URI:', config.logoutRedirectUri);
    
    console.log('Redirecting to Cognito logout endpoint:', logoutUrl.toString());
    
    // Redirect to Cognito logout endpoint
    window.location.href = logoutUrl.toString();
  } catch (error) {
    console.error('Logout error:', error);
    
    // Fallback to manual logout if Amplify method fails
    localStorage.clear(); // Clear all local storage as a fallback
    window.location.href = '/login';
  }
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = async () => {
  if (!isCognitoEnabled()) return false;
  
  try {
    await Auth.currentAuthenticatedUser();
    return true;
  } catch (error) {
    return false;
  }
};

/**
 * Get the current authenticated user
 */
export const getCurrentUser = async () => {
  if (!isCognitoEnabled()) return null;
  
  try {
    return await Auth.currentAuthenticatedUser();
  } catch (error) {
    console.error('Get user error:', error);
    return null;
  }
};

/**
 * Get the current session
 */
export const getCurrentSession = async () => {
  if (!isCognitoEnabled()) return null;
  
  try {
    return await Auth.currentSession();
  } catch (error) {
    console.error('Get session error:', error);
    return null;
  }
};

/**
 * Get ID token
 */
export const getIdToken = async () => {
  try {
    const session = await Auth.currentSession();
    return session.getIdToken().getJwtToken();
  } catch (error) {
    console.error('Get ID token error:', error);
    return null;
  }
};

/**
 * Get access token
 */
export const getAccessToken = async () => {
  try {
    const session = await Auth.currentSession();
    return session.getAccessToken().getJwtToken();
  } catch (error) {
    console.error('Get access token error:', error);
    return null;
  }
};

/**
 * Get user attributes
 */
export const getUserAttributes = async () => {
  try {
    const user = await Auth.currentAuthenticatedUser();
    return user.attributes;
  } catch (error) {
    console.error('Get user attributes error:', error);
    return null;
  }
};
