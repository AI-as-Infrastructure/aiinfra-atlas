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
    
    // Force Amplify to handle the current URL with the authorization code
    const currentUrl = window.location.href;
    logDebug('Current URL', currentUrl);
    
    // This will exchange the code for tokens
    const user = await Auth.currentAuthenticatedUser();
    logDebug('User authenticated', user.username);
    
    return user;
  } catch (error) {
    logDebug('Token exchange error', error);
    throw error;
  }
}

onMounted(async () => {
  try {
    logDebug('Callback page mounted');
    
    // Clear any previous authentication data to ensure a fresh state
    localStorage.removeItem('amplify-signin-with-hostedUI');
    
    // Check URL for authorization code
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    
    logDebug('URL parameters', { 
      code: code ? `${code.substring(0, 10)}...` : 'none',
      state: state || 'none'
    });
    
    if (!code) {
      error.value = 'No authorization code found in URL.';
      loading.value = false;
      return;
    }
    
    // Exchange the code for tokens
    try {
      const user = await exchangeCodeForTokens(code, state);
      
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
      throw new Error(`Failed to exchange code: ${exchangeError.message || '400'}`);
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