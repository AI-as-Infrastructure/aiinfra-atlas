<template>
  <div class="logout-container">
    <div class="logout-content">
      <h1>Logging Out</h1>
      <div class="spinner"></div>
      <p>Please wait while we complete the logout process...</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Auth } from 'aws-amplify';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

onMounted(async () => {
  try {
    console.log('LogoutPage: Cleaning up authentication state');
    
    // Clear Amplify auth tokens
    await Auth.signOut({ global: true });
    
    // Clear any remaining Cognito tokens from localStorage
    const cognitoKeys = Object.keys(localStorage).filter(key => 
      key.startsWith('CognitoIdentityServiceProvider') || 
      key.startsWith('amplify-signin-with-hostedUI')
    );
    
    cognitoKeys.forEach(key => localStorage.removeItem(key));
    
    // Reset auth store state
    authStore.$reset();
    
    console.log('LogoutPage: Logout cleanup complete');
    
    // Short delay for visual feedback and to ensure cleanup is complete
    setTimeout(() => {
      // Redirect to login page after successful logout
      router.push('/login');
    }, 1500);
  } catch (error) {
    console.error('LogoutPage: Error during logout cleanup:', error);
    
    // Fallback - force redirect to login even if there was an error
    setTimeout(() => {
      router.push('/login');
    }, 1500);
  }
});
</script>

<style scoped>
.logout-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 2rem;
}

.logout-content {
  text-align: center;
  max-width: 500px;
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  font-size: 1.8rem;
  margin-bottom: 1.5rem;
  color: #2c3e50;
}

p {
  margin-top: 1.5rem;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 1rem auto;
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #2c3e50;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
