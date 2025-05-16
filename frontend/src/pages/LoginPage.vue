<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>Welcome to ATLAS</h1>
        <h2>Analysis and Testing of Language Models for Archival Systems</h2>
      </div>
      
      <div class="login-content">
        <p>
          ATLAS is a specialized platform for exploring historical parliamentary debates using AI.
          This system is part of the AI as Infrastructure (AIINFRA) research project.
        </p>
        
        <p>
          To proceed, you need to authenticate with your credentials.
        </p>
        
        <div class="login-actions">
          <button class="login-button" @click="handleLogin">
            Sign In
          </button>
          <div v-if="authStatus === 'failed'" class="login-error">
            Authentication failed. Please try again.
          </div>
          <div v-if="isLoading" class="login-loading">
            <div class="spinner"></div>
            <span>Initiating login...</span>
          </div>
        </div>
        
        <div class="login-footer">
          <p>
            <small>© 2024-2026 AIINFRA Project. All rights reserved.</small>
          </p>
          <p>
            <small>
              <a href="https://aiinfra.anu.edu.au" target="_blank" rel="noreferrer">Learn more about AIINFRA</a>
            </small>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { login, isAuthenticated } from '../auth/amplify-auth';

const router = useRouter();
const isLoading = ref(false);
const authStatus = ref(null);

// Clear all auth data and check if already authenticated
onMounted(async () => {
  try {
    // Always clear authentication data on the login page
    console.log('LoginPage: Clearing all authentication data');
    
    // Check for logout query parameter as a signal to do more aggressive cleanup
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('logout')) {
      console.log('Logout parameter detected, performing full cleanup');
      
      // Try to sign out of Amplify directly
      try {
        const { Auth } = await import('aws-amplify');
        await Auth.signOut({ global: true });
        console.log('Amplify signOut completed');
      } catch (e) {
        console.error('Error during Amplify signOut:', e);
      }
    }
    
    // Clear all storage in any case
    localStorage.clear();
    sessionStorage.clear();
    document.cookie.split(';').forEach(c => {
      document.cookie = c.trim().split('=')[0] + '=;expires=' + new Date(0).toUTCString() + ';path=/';
    });
    console.log('All auth data cleared');
    
    // After clearing, check if still authenticated (shouldn't be)
    const authenticated = await isAuthenticated();
    if (authenticated) {
      console.log('Still authenticated after cleanup, redirecting to home');
      router.push('/');
    }
  } catch (error) {
    console.error('Error checking authentication status:', error);
  }
});

// Handle login button click
async function handleLogin() {
  try {
    isLoading.value = true;
    authStatus.value = 'pending';
    await login();
  } catch (error) {
    console.error('Login error:', error);
    authStatus.value = 'failed';
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
  padding: 2rem;
  background-color: #f8f9fa;
}

.login-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  width: 100%;
  max-width: 600px;
}

.login-header {
  background-color: #2c3e50;
  color: white;
  padding: 2rem;
  text-align: center;
}

.login-header h1 {
  margin: 0;
  font-size: 2rem;
}

.login-header h2 {
  margin: 0.5rem 0 0;
  font-weight: normal;
  font-size: 1rem;
  opacity: 0.9;
}

.login-content {
  padding: 2rem;
}

.login-content p {
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.login-actions {
  margin: 2rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-button {
  background-color: #2c3e50;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
  min-width: 150px;
}

.login-button:hover {
  background-color: #1a252f;
}

.login-error {
  margin-top: 1rem;
  color: #e74c3c;
  font-size: 0.9rem;
}

.login-loading {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 0.9rem;
  color: #7f8c8d;
}

.spinner {
  width: 24px;
  height: 24px;
  margin-bottom: 0.5rem;
  border: 3px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #2c3e50;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-footer {
  margin-top: 2rem;
  text-align: center;
  color: #6c757d;
}

.login-footer a {
  color: #2c3e50;
  text-decoration: none;
}

.login-footer a:hover {
  text-decoration: underline;
}
</style>
