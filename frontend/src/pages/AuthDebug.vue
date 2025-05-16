<template>
  <div class="debug-container">
    <h1>Auth Configuration Debug</h1>
    
    <div class="config-section">
      <h2>Cognito Configuration</h2>
      <pre>{{ configJson }}</pre>
    </div>
    
    <div class="login-section">
      <h2>Login URL</h2>
      <p>This is the URL that will be used for login:</p>
      <div class="url-display">{{ loginUrl }}</div>
      
      <div class="action-buttons">
        <button @click="copyLoginUrl" class="debug-button">Copy URL</button>
        <button @click="openInNewTab" class="debug-button">Open in New Tab</button>
        <button @click="triggerLogin" class="debug-button primary">Normal Login</button>
      </div>
    </div>

    <div class="instructions">
      <h2>Troubleshooting Steps</h2>
      <ol>
        <li>
          <strong>Check AWS Cognito Console:</strong>
          <ul>
            <li>Verify the Client ID matches exactly: <code>{{ config.clientId }}</code></li>
            <li>Ensure the callback URL is configured as: <code>{{ config.loginRedirectUri }}</code> (no trailing slashes)</li>
            <li>Make sure "Implicit grant" (token) is enabled</li>
          </ul>
        </li>
        <li>
          <strong>Try URL directly:</strong> Use "Open in New Tab" to see the exact error from Cognito
        </li>
        <li>
          <strong>After fixing in AWS Console:</strong> Click "Normal Login" to try the fixed flow
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { getCognitoConfig, login } from '@/auth/cognito';

// Get Cognito configuration
const config = getCognitoConfig();
const configJson = computed(() => JSON.stringify(config, null, 2));

// Compute login URL
const loginUrl = ref('');
const codeVerifier = ref('');
const codeChallenge = ref('');

onMounted(async () => {
  // Generate PKCE code verifier and challenge as would happen in actual login
  codeVerifier.value = generateRandomString(64);
  codeChallenge.value = await generateCodeChallenge(codeVerifier.value);
  
  const url = new URL(`https://${config.domain}/oauth2/authorize`);
  url.searchParams.append('client_id', config.clientId);
  url.searchParams.append('response_type', 'code');
  url.searchParams.append('scope', config.oauthScope);
  url.searchParams.append('redirect_uri', config.loginRedirectUri);
  url.searchParams.append('code_challenge', codeChallenge.value);
  url.searchParams.append('code_challenge_method', 'S256');
  
  loginUrl.value = url.toString();
});

// Generate random string for PKCE
function generateRandomString(length) {
  const array = new Uint8Array(length);
  window.crypto.getRandomValues(array);
  return Array.from(array, byte => ('0' + (byte & 0xFF).toString(16)).slice(-2)).join('');
}

// Create SHA-256 hash of code verifier
async function generateCodeChallenge(codeVerifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(codeVerifier);
  const digest = await window.crypto.subtle.digest('SHA-256', data);
  
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

// Functions
function copyLoginUrl() {
  navigator.clipboard.writeText(loginUrl.value);
  alert('URL copied to clipboard');
}

function openInNewTab() {
  window.open(loginUrl.value, '_blank');
}

function triggerLogin() {
  // Store the code verifier for the callback page to use
  sessionStorage.setItem('pkce_code_verifier', codeVerifier.value);
  login();
}
</script>

<style scoped>
.debug-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
  font-family: system-ui, -apple-system, sans-serif;
}

.config-section, .login-section, .instructions {
  margin-bottom: 30px;
  padding: 20px;
  border-radius: 8px;
  background-color: #f8f9fa;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

pre {
  background-color: #2c3e50;
  color: white;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.url-display {
  background-color: #eee;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #ddd;
  word-break: break-all;
  margin-bottom: 15px;
  font-family: monospace;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.debug-button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  background-color: #6c757d;
  color: white;
  cursor: pointer;
}

.debug-button:hover {
  background-color: #5a6268;
}

.debug-button.primary {
  background-color: #2c3e50;
}

.debug-button.primary:hover {
  background-color: #1a252f;
}

h1, h2 {
  color: #2c3e50;
}

ol, ul {
  margin-top: 10px;
}

li {
  margin-bottom: 10px;
}

code {
  background-color: #f1f1f1;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: monospace;
}
</style>
