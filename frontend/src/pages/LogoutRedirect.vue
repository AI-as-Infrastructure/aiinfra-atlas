<template>
  <div class="logout-container">
    <div class="logout-content">
      <h1>Logout Complete</h1>
      <p>You have been successfully logged out from Cognito.</p>
      <p>Redirecting to login page...</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

onMounted(() => {
  console.log('Logout redirect page mounted');
  
  // Ensure auth store is reset
  authStore.$reset();
  
  // Clear any remaining tokens
  const cognitoKeys = Object.keys(localStorage).filter(key => 
    key.startsWith('CognitoIdentityServiceProvider') || 
    key.startsWith('amplify-signin-with-hostedUI')
  );
  
  cognitoKeys.forEach(key => localStorage.removeItem(key));
  
  // Short delay for visual feedback
  setTimeout(() => {
    // Redirect to login page
    router.push('/login');
  }, 1500);
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
</style>
