import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  isCognitoEnabled,
  isAuthenticated,
  getUserInfo,
  login as cognitoLogin,
  logout as cognitoLogout,
  parseTokensFromUrl,
  storeTokens,
  clearTokens
} from '../auth/cognito';

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null);
  const loading = ref(false);
  const error = ref(null);
  
  // Reset function for logout
  function $reset() {
    user.value = null;
    loading.value = false;
    error.value = null;
  }

  // Getters
  const isLoggedIn = computed(() => {
    // Always false if Cognito is disabled
    if (!isCognitoEnabled()) {
      console.log('isLoggedIn: Cognito is disabled');
      return false;
    }
    
    const authenticated = isAuthenticated();
    const hasUser = !!user.value;
    
    console.log('isLoggedIn check:', {
      authenticated,
      hasUser,
      result: authenticated && hasUser
    });
    
    // If authenticated but no user, try to get user info
    if (authenticated && !hasUser) {
      console.log('isLoggedIn: Authenticated but no user, trying to get user info');
      const userInfo = getUserInfo();
      if (userInfo) {
        user.value = userInfo;
        return true;
      }
    }
    
    // Check both user value and actual authentication state
    return hasUser && authenticated;
  });

  const showAuthUI = computed(() => {
    return isCognitoEnabled();
  });

  const username = computed(() => {
    return user.value?.email || user.value?.username || null;
  });

  // Actions
  function initialize() {
    if (!isCognitoEnabled()) {
      // If Cognito is disabled, reset state and exit
      user.value = null;
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      console.log('Initializing auth store...');
      
      // Check for tokens in URL (after redirect from Cognito)
      const tokens = parseTokensFromUrl();
      if (tokens) {
        // Store tokens and clear URL
        storeTokens(tokens);
        console.log('Tokens from URL stored');
        // Replace current URL to remove token data from browser history
        window.history.replaceState({}, document.title, window.location.pathname);
      }

      // Directly check localStorage for tokens
      const storedTokensStr = localStorage.getItem('atlas_cognito_tokens');
      console.log('Checking localStorage directly:', {
        tokensExist: !!storedTokensStr,
        length: storedTokensStr?.length || 0
      });
      
      // Check if user is authenticated
      const authenticated = isAuthenticated();
      console.log('Authentication state from isAuthenticated():', authenticated);
      
      if (authenticated) {
        // Get user info from token
        const userInfo = getUserInfo();
        console.log('User info retrieved:', userInfo ? 'success' : 'failed');
        user.value = userInfo;
      } else {
        // Try one more time with direct localStorage access
        if (storedTokensStr) {
          try {
            const directTokens = JSON.parse(storedTokensStr);
            if (directTokens && directTokens.idToken) {
              console.log('Found valid tokens in localStorage but isAuthenticated() returned false');
              // Try to extract user info directly
              const base64Url = directTokens.idToken.split('.')[1];
              const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
              const payload = JSON.parse(atob(base64));
              
              if (payload) {
                console.log('Successfully extracted user info from token payload');
                user.value = payload;
                return; // Exit early with successful authentication
              }
            }
          } catch (parseErr) {
            console.error('Error parsing stored tokens:', parseErr);
          }
        }
        
        console.log('User not authenticated, clearing user state');
        user.value = null;
      }
    } catch (err) {
      console.error('Auth initialization error:', err);
      error.value = 'Failed to initialize authentication';
      user.value = null;
    } finally {
      loading.value = false;
    }
  }

  function login() {
    if (!isCognitoEnabled()) return;
    cognitoLogin();
  }

  function logout() {
    if (!isCognitoEnabled()) return;
    user.value = null;
    cognitoLogout();
  }

  // Initialize auth state when store is first created
  initialize();

  return {
    // State
    user,
    loading,
    error,
    
    // Getters
    isLoggedIn,
    showAuthUI,
    username,
    
    // Actions
    initialize,
    login,
    logout
  };
});
