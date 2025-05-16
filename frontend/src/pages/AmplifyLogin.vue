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
          <button @click="handleLogin" class="login-button">Sign In</button>
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
import { login, isAuthenticated } from '../auth/amplify-auth';
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

// Check if already authenticated
onMounted(async () => {
  const authenticated = await isAuthenticated();
  if (authenticated) {
    console.log('Already authenticated, redirecting to home');
    router.push('/');
  }
});

// Handle login button click
function handleLogin() {
  login();
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
  justify-content: center;
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
}

.login-button:hover {
  background-color: #1a252f;
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
