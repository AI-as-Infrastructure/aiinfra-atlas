import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  isCognitoEnabled,
  isAuthenticated,
  getCurrentUser,
  getIdToken,
  login as cognitoLogin,
  logout as cognitoLogout
} from '../auth/amplify-auth';

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
      console.log('isLoggedIn: Authenticated but no user, refreshing user data');
      // Refresh user data asynchronously - we'll return based on authentication for now
      getCurrentUser().then(userInfo => {
        if (userInfo) {
          user.value = userInfo;
        }
      }).catch(err => {
        console.error('Error getting current user:', err);
      });
    }
    
    // We rely primarily on authentication state from Amplify
    return authenticated;
  });

  const showAuthUI = computed(() => {
    return isCognitoEnabled();
  });

  const username = computed(() => {
    return user.value?.email || user.value?.username || null;
  });

  // Actions
  async function initialize() {
    if (!isCognitoEnabled()) {
      // If Cognito is disabled, reset state and exit
      user.value = null;
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      console.log('Initializing auth store...');
      
      // Check if user is authenticated using Amplify's APIs
      const authenticated = await isAuthenticated();
      console.log('Authentication state from isAuthenticated():', authenticated);
      
      if (authenticated) {
        // Get user info using Amplify's API
        try {
          const userInfo = await getCurrentUser();
          console.log('User info retrieved:', userInfo ? 'success' : 'failed');
          if (userInfo) {
            user.value = userInfo;
          } else {
            console.warn('Authenticated but no user info available');
            user.value = null;
          }
        } catch (userErr) {
          console.error('Error getting user info:', userErr);
          user.value = null;
        }
      } else {
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

  async function logout() {
    await cognitoLogout();
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
