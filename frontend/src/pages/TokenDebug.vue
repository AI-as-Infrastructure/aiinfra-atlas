<template>
  <div class="debug-container">
    <h1>Token Debugging Page</h1>
    
    <div class="section">
      <h2>Authentication Status</h2>
      <div class="status-box">
        <p><strong>Is Cognito Enabled:</strong> {{ isCognitoEnabled }}</p>
        <p><strong>Is Authenticated:</strong> {{ isAuthenticated }}</p>
        <p><strong>Username:</strong> {{ username }}</p>
      </div>
    </div>
    
    <div class="section">
      <h2>Token Information</h2>
      <div v-if="storedTokens">
        <div class="token-box">
          <p><strong>ID Token:</strong> {{ tokenPreview(storedTokens.idToken) }}</p>
          <p><strong>Access Token:</strong> {{ tokenPreview(storedTokens.accessToken) }}</p>
          <p><strong>Refresh Token:</strong> {{ tokenPreview(storedTokens.refreshToken) }}</p>
          <p><strong>Token Type:</strong> {{ storedTokens.tokenType }}</p>
          <p><strong>Expires In:</strong> {{ storedTokens.expiresIn }}</p>
        </div>
        
        <div v-if="tokenError" class="error-box">
          <h3>Token Validation Error</h3>
          <p>{{ tokenError }}</p>
        </div>
        
        <div v-if="decodedToken" class="token-details">
          <h3>Decoded Token Contents</h3>
          <pre>{{ JSON.stringify(decodedToken, null, 2) }}</pre>
        </div>
      </div>
      <div v-else class="error-box">
        <p>No tokens found in storage.</p>
      </div>
    </div>
    
    <div class="actions">
      <button @click="checkAuthentication" class="action-button">Refresh Status</button>
      <button @click="clearAllTokens" class="action-button danger">Clear Tokens</button>
      <button @click="goToLogin" class="action-button">Go to Login</button>
      <button @click="goToHome" class="action-button primary">Go to Home</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { 
  isCognitoEnabled as checkCognitoEnabled,
  isAuthenticated as checkAuthenticated,
  getStoredTokens,
  clearTokens
} from '../auth/cognito';

const router = useRouter();
const authStore = useAuthStore();

const isCognitoEnabled = ref(false);
const isAuthenticated = ref(false);
const username = ref(null);
const storedTokens = ref(null);
const decodedToken = ref(null);
const tokenError = ref(null);

function checkAuthentication() {
  isCognitoEnabled.value = checkCognitoEnabled();
  isAuthenticated.value = checkAuthenticated();
  username.value = authStore.username;
  storedTokens.value = getStoredTokens();
  
  if (storedTokens.value && storedTokens.value.idToken) {
    try {
      // Decode the token
      const parts = storedTokens.value.idToken.split('.');
      if (parts.length !== 3) {
        tokenError.value = 'Invalid token format (not a valid JWT)';
        return;
      }
      
      const payload = parts[1];
      const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
      
      // Check expiration
      const now = Math.floor(Date.now() / 1000);
      if (decoded.exp && now >= decoded.exp) {
        tokenError.value = `Token expired at ${new Date(decoded.exp * 1000).toLocaleString()}`;
      } else if (decoded.exp) {
        tokenError.value = null;
        const expiresIn = decoded.exp - now;
        const hours = Math.floor(expiresIn / 3600);
        const minutes = Math.floor((expiresIn % 3600) / 60);
        decoded._expiresIn = `${hours}h ${minutes}m (${new Date(decoded.exp * 1000).toLocaleString()})`;
      }
      
      decodedToken.value = decoded;
    } catch (err) {
      tokenError.value = `Error decoding token: ${err.message}`;
      decodedToken.value = null;
    }
  } else {
    decodedToken.value = null;
    tokenError.value = null;
  }
}

function tokenPreview(token) {
  if (!token) return 'Not present';
  if (token.length <= 15) return token;
  return token.substring(0, 10) + '...' + token.substring(token.length - 5);
}

function clearAllTokens() {
  clearTokens();
  checkAuthentication();
}

function goToLogin() {
  router.push('/login');
}

function goToHome() {
  router.push('/');
}

onMounted(() => {
  checkAuthentication();
});
</script>

<style scoped>
.debug-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 1.5rem;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

h1 {
  margin-top: 0;
  color: #2c3e50;
  border-bottom: 1px solid #eee;
  padding-bottom: 1rem;
}

.section {
  margin-bottom: 2rem;
}

h2 {
  color: #2c3e50;
  margin-bottom: 1rem;
}

.status-box, .token-box {
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.error-box {
  background-color: #fee;
  border: 1px solid #ecc;
  border-radius: 4px;
  padding: 1rem;
  color: #c33;
  margin-bottom: 1rem;
}

.token-details {
  margin-top: 1.5rem;
}

pre {
  background-color: #1a1a1a;
  color: #eee;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 2rem;
  justify-content: flex-end;
}

.action-button {
  background-color: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.9rem;
}

.action-button:hover {
  filter: brightness(0.9);
}

.action-button.primary {
  background-color: #2c3e50;
}

.action-button.danger {
  background-color: #dc3545;
}
</style>
