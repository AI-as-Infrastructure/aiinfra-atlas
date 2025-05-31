/**
 * AWS Cognito authentication using AWS Amplify
 * Following AWS recommended approach for SPA authentication
 */

import { Auth, Hub } from 'aws-amplify';
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
      // Add cookie storage configuration to help with session management
      cookieStorage: {
        // Use a more flexible domain configuration for cross-domain scenarios
        domain: import.meta.env.VITE_COOKIE_DOMAIN || window.location.hostname,
        path: '/',
        expires: 365,
        // Always use secure cookies in production
        secure: import.meta.env.PROD || window.location.protocol === 'https:',
        // Enable cross-domain cookies with SameSite=none (lowercase required by Amplify)
        // Note: SameSite=none requires Secure to be true
        sameSite: import.meta.env.PROD ? 'none' : 'lax'
      },
      // Synchronize session across tabs
      mandatorySignIn: false
    },
  });
  
  // Set up Hub to listen for auth events
  try {
    Hub.listen('auth', (data) => {
      const { payload } = data;
      console.log('Auth event:', payload.event);
      
      switch (payload.event) {
        case 'signIn':
          console.log('User signed in');
          break;
        case 'signOut':
          console.log('User signed out');
          break;
        case 'tokenRefresh':
          console.log('Token refreshed');
          break;
        case 'tokenRefresh_failure':
          console.error('Token refresh failed');
          // Redirect to login on token refresh failure
          window.location.href = '/login';
          break;
      }
    });
  } catch (err) {
    console.error('Error setting up Auth Hub listener:', err);
  }
  
  console.log('Amplify configured with Cognito');
};

/**
 * Check if Cognito auth is enabled
 */
export const isCognitoEnabled = () => {
  return import.meta.env.VITE_USE_COGNITO_AUTH === 'true';
};

/**
 * Get Cognito configuration from environment variables
 * @returns {Object} Cognito configuration object
 */
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
  const logoutEndpoint = import.meta.env.VITE_COGNITO_LOGOUT_ENDPOINT || `https://${config.domain}/logout`;
  
  // Return complete configuration
  return {
    ...config,
    loginRedirectUri,
    logoutRedirectUri,
    logoutEndpoint,
  };
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
    
    // Generate and store PKCE code verifier and challenge before login
    const codeVerifier = Math.random().toString(36).substring(2, 15) + 
                        Math.random().toString(36).substring(2, 15) +
                        Math.random().toString(36).substring(2, 15) +
                        Math.random().toString(36).substring(2, 15);
    sessionStorage.setItem('pkce_code_verifier', codeVerifier);
    console.log('Code verifier generated and stored:', codeVerifier.substring(0, 10) + '...');
    
    // Use Amplify's federatedSignIn for a fresh login attempt
    // This will handle the PKCE flow properly
    console.log('Starting fresh login attempt with Amplify');
    try {
      await Auth.federatedSignIn();
    } catch (amplifyError) {
      console.error('Amplify federatedSignIn error:', amplifyError);
      throw amplifyError; // Re-throw to trigger fallback
    }
  } catch (error) {
    console.error('Login error:', error);
    
    // If Amplify's method fails, fall back to manual URL construction
    try {
      // Get configuration from environment variables
      const config = {
        domain: import.meta.env.VITE_COGNITO_DOMAIN,
        clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
        redirectUri: import.meta.env.VITE_COGNITO_LOGIN_REDIRECT_URI || `${window.location.origin}/callback`,
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
      
      // PKCE: Add code_challenge and code_challenge_method for better security
      const codeVerifier = sessionStorage.getItem('pkce_code_verifier');
      if (codeVerifier) {
        // Simple encoder function for code challenge
        const createChallenge = async (verifier) => {
          const encoder = new TextEncoder();
          const data = encoder.encode(verifier);
          const digest = await window.crypto.subtle.digest('SHA-256', data);
          
          return btoa(String.fromCharCode(...new Uint8Array(digest)))
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=+$/, '');
        };
        
        const codeChallenge = await createChallenge(codeVerifier);
        loginUrl.searchParams.append('code_challenge', codeChallenge);
        loginUrl.searchParams.append('code_challenge_method', 'S256');
      }
      
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
    
    // First try to use Amplify's signOut method with global option to clear all sessions
    // This is critical for proper logout behavior
    try {
      await Auth.signOut({ global: true });
      console.log('Global signout successful');
    } catch (signOutError) {
      // If global signout fails due to scope issues, try local signout
      if (signOutError.code === 'NotAuthorizedException' || signOutError.message?.includes('required scopes')) {
        console.log('Global signout failed due to scope limitations, performing local signout');
        try {
          await Auth.signOut(); // Local signout without global flag
        } catch (localSignOutError) {
          console.error('Local signout also failed:', localSignOutError);
        }
      } else {
        console.error('Signout error:', signOutError);
      }
    }
    
    // Clear all Cognito-related items from local storage
    Object.keys(localStorage)
      .filter(key => key.startsWith('CognitoIdentityServiceProvider') || 
                     key.startsWith('amplify') || 
                     key.startsWith('aws'))
      .forEach(key => localStorage.removeItem(key));
    
    // Clear session storage items
    Object.keys(sessionStorage)
      .filter(key => key.startsWith('CognitoIdentityServiceProvider') || 
                     key.startsWith('amplify') || 
                     key.startsWith('aws') ||
                     key === 'pkce_code_verifier')
      .forEach(key => sessionStorage.removeItem(key));
    
    // Then do a manual redirect to Cognito's logout endpoint for server-side session invalidation
    // Get the exact configured values from environment variables
    const config = {
      domain: import.meta.env.VITE_COGNITO_DOMAIN,
      clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      logoutEndpoint: import.meta.env.VITE_COGNITO_LOGOUT_ENDPOINT,
      logoutRedirectUri: import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI
    };
    
    // Force a direct approach for logout using Cognito's well-defined structure
    const logoutEndpoint = config.logoutEndpoint || `https://${config.domain}/logout`;
    const logoutRedirectUri = config.logoutRedirectUri || `${window.location.origin}/logout.html`;
    
    // Construct the Cognito logout URL manually to ensure it's correct
    const logoutUrl = new URL(logoutEndpoint);
    
    // Add query parameters required by AWS Cognito
    logoutUrl.searchParams.append('client_id', config.clientId);
    logoutUrl.searchParams.append('logout_uri', logoutRedirectUri);
    
    // Debug output
    console.log('Cognito domain:', config.domain);
    console.log('Client ID:', config.clientId);
    
    // Log the full URL for debugging
    console.log('Logout URL:', logoutUrl.toString());
    console.log('Logout redirect URI:', logoutRedirectUri);
    
    console.log('Redirecting to Cognito logout endpoint:', logoutUrl.toString());
    
    // Redirect to Cognito logout endpoint
    window.location.href = logoutUrl.toString();
  } catch (error) {
    console.error('Logout error:', error);
    
    // Fallback to manual logout if Amplify method fails
    localStorage.clear(); // Clear all local storage as a fallback
    sessionStorage.clear(); // Also clear session storage
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
