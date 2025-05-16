<template>
  <div class="callback-container">
    <div v-if="loading" class="loading">
      <h2>Processing Authentication</h2>
      <div class="spinner"></div>
      <p>Please wait while we complete your login...</p>
    </div>
    <div v-else-if="error" class="error">
      <h2>Authentication Error</h2>
      <p>{{ error }}</p>
      <div>
        <button @click="goToLogin" class="btn">Back to Login</button>
        <button @click="goToDebug" class="btn debug">View Debug Info</button>
      </div>
    </div>
    <div v-else class="success">
      <h2>Authentication Successful!</h2>
      <p>Redirecting to the application...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { handleCallback } from '../auth/amplify-auth';
import { useAuthStore } from '../stores/auth';
import { Auth } from 'aws-amplify';

const router = useRouter();
const authStore = useAuthStore();
const loading = ref(true);
const error = ref(null);
const debug = ref({});

// Navigation functions
function goToLogin() {
  router.push('/login');
}

function goToDebug() {
  router.push('/token-debug');
}

// Helper to log and store debug info
function logDebug(message, data = null) {
  console.log(`[Amplify Callback] ${message}`, data);
  debug.value[message] = data;
}

// Exchange authorization code for tokens
async function exchangeCodeForTokens(code, state) {
  try {
    logDebug('Exchanging code for tokens');
    
    // Retrieve the PKCE code verifier from session storage
    const codeVerifier = sessionStorage.getItem('pkce_code_verifier');
    logDebug('Code verifier retrieved', codeVerifier ? `${codeVerifier.substring(0, 10)}...` : 'none');
    
    if (!codeVerifier) {
      logDebug('No code verifier found in session storage');
      console.warn('PKCE code verifier missing during callback');
    }
    
    // Force Amplify to reconfigure before handling the auth response
    try {
      // Import the configuration function from amplify-auth
      const { configureAmplify } = await import('../auth/amplify-auth');
      // Ensure Amplify is properly configured
      configureAmplify();
      logDebug('Amplify reconfigured');
    } catch (configError) {
      logDebug('Error reconfiguring Amplify:', configError);
    }
    
    // Log the current URL and code for debugging
    const currentUrl = window.location.href;
    logDebug('Current URL', currentUrl);
    logDebug('Auth code', code ? `${code.substring(0, 10)}...` : 'none');
    
    // Multi-step approach to handle the authentication code
    // Step 1: Try Auth.handleAuthResponse
    let user = null;
    try {
      await Auth.handleAuthResponse(window.location.href);
      logDebug('Auth response handled with handleAuthResponse');
    } catch (handleError) {
      logDebug('Error handling auth response directly:', handleError);
    }
    
    // Step 2: Try Auth.currentAuthenticatedUser
    try {
      user = await Auth.currentAuthenticatedUser();
      logDebug('User authenticated via currentAuthenticatedUser', user.username);
      return user;
    } catch (userError) {
      logDebug('Error getting current user:', userError);
      
      // Step 3: If all else fails, try Auth.federatedSignIn.hostedUI.currentUser
      try {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('code') && urlParams.has('state')) {
          logDebug('Trying to parse tokens manually');
          // We'll try Auth.currentSession as a last resort
          const session = await Auth.currentSession();
          if (session) {
            logDebug('Session retrieved manually');
            // Success! Now get the user
            user = await Auth.currentAuthenticatedUser();
            return user;
          }
        }
      } catch (finalError) {
        logDebug('Final attempt failed:', finalError);
      }
      
      // If we get here, all attempts failed
      throw new Error('Failed to authenticate user after multiple attempts');
    }
  } catch (error) {
    logDebug('Token exchange error', error);
    throw error;
  }
}

onMounted(async () => {
  try {
    logDebug('Callback page mounted');
    
    // Check URL for authorization code
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const errorParam = urlParams.get('error');
    const errorDescription = urlParams.get('error_description');
    
    logDebug('URL parameters', { 
      code: code ? `${code.substring(0, 10)}...` : 'none',
      state: state || 'none',
      error: errorParam || 'none',
      errorDescription: errorDescription || 'none'
    });
    
    // Check for error in the URL parameters
    if (errorParam) {
      error.value = `Authentication error: ${errorParam}${errorDescription ? ` - ${errorDescription}` : ''}`;
      loading.value = false;
      return;
    }
    
    if (!code) {
      error.value = 'No authorization code found in URL.';
      loading.value = false;
      return;
    }
    
    // Exchange the code for tokens
    try {
      // Clear any previous authentication data to ensure a fresh state
      // We do this AFTER checking for the code to avoid clearing data on errors
      localStorage.removeItem('amplify-signin-with-hostedUI');
      
      const user = await exchangeCodeForTokens(code, state);
      
      // After successful authentication, clear the code verifier
      // as it should only be used once
      sessionStorage.removeItem('pkce_code_verifier');
      
      // Initialize auth store
      await authStore.initialize();
      
      // Show success message briefly
      loading.value = false;
      
      // Redirect to home with a full page reload to ensure clean state
      setTimeout(() => {
        window.location.href = '/';
      }, 1000);
    } catch (exchangeError) {
      logDebug('Error during token exchange', exchangeError);
      
      // Check if it's an expired or already used code
      if (exchangeError.code === 'NotAuthorizedException' || 
          (exchangeError.message && exchangeError.message.includes('expired'))) {
        error.value = 'The authorization code has expired or has already been used. Please try logging in again.';
      } else {
        error.value = `Failed to exchange code: ${exchangeError.message || 'Unknown error'}`;
      }
      
      loading.value = false;
      return;
    }
  } catch (err) {
    console.error('Authentication error:', err);
    error.value = err.message || 'An error occurred during authentication.';
    loading.value = false;
    
    // Save debug info to session storage for debugging page
    sessionStorage.setItem('auth_debug', JSON.stringify(debug.value));
  }
});
</script>

<style scoped>
.callback-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 2rem;
}

.loading, .error, .success {
  text-align: center;
  max-width: 500px;
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.spinner {
  margin: 1rem auto;
  width: 40px;
  height: 40px;
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #3273dc;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background-color: #3273dc;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn.debug {
  background-color: #f14668;
  margin-left: 1rem;
}
</style>