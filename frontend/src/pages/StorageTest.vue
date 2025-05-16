<template>
  <div class="storage-test">
    <h1>Browser Storage Test</h1>
    
    <div class="test-section">
      <h2>Local Storage Test</h2>
      <div class="test-controls">
        <button @click="testLocalStorage" class="test-button">Test Local Storage</button>
        <button @click="clearLocalStorage" class="test-button clear">Clear Local Storage</button>
      </div>
      <div v-if="localStorageResult" class="result-box" :class="{ success: localStorageSuccess, error: !localStorageSuccess }">
        <h3>{{ localStorageSuccess ? 'Success!' : 'Error!' }}</h3>
        <pre>{{ localStorageResult }}</pre>
      </div>
    </div>
    
    <div class="test-section">
      <h2>Current Storage Contents</h2>
      <div class="storage-contents">
        <h3>Local Storage</h3>
        <pre>{{ localStorageContents }}</pre>
      </div>
    </div>
    
    <div class="test-section">
      <h2>Manual Token Test</h2>
      <div class="test-controls">
        <button @click="createTestToken" class="test-button">Create Test Token</button>
        <button @click="checkTestToken" class="test-button">Check Test Token</button>
      </div>
      <div v-if="tokenTestResult" class="result-box">
        <pre>{{ tokenTestResult }}</pre>
      </div>
    </div>
    
    <div class="actions">
      <button @click="goToLogin" class="nav-button">Go to Login</button>
      <button @click="goToTokenDebug" class="nav-button">Go to Token Debug</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const localStorageResult = ref('');
const localStorageSuccess = ref(false);
const localStorageContents = ref('');
const tokenTestResult = ref('');

// Test if localStorage is working
function testLocalStorage() {
  try {
    // Clear previous results
    localStorageResult.value = '';
    localStorageSuccess.value = false;
    
    // Test writing to localStorage
    const testValue = 'test-' + Date.now();
    localStorage.setItem('storage_test', testValue);
    
    // Test reading from localStorage
    const readValue = localStorage.getItem('storage_test');
    
    if (readValue === testValue) {
      localStorageSuccess.value = true;
      localStorageResult.value = `LocalStorage is working correctly!\nWrote: ${testValue}\nRead: ${readValue}`;
    } else {
      localStorageSuccess.value = false;
      localStorageResult.value = `LocalStorage read/write mismatch!\nWrote: ${testValue}\nRead: ${readValue || 'null'}`;
    }
  } catch (error) {
    localStorageSuccess.value = false;
    localStorageResult.value = `LocalStorage error: ${error.message}`;
  }
  
  // Refresh storage contents display
  refreshStorageContents();
}

// Clear localStorage
function clearLocalStorage() {
  try {
    localStorage.clear();
    localStorageResult.value = 'LocalStorage cleared successfully';
    localStorageSuccess.value = true;
  } catch (error) {
    localStorageResult.value = `Error clearing localStorage: ${error.message}`;
    localStorageSuccess.value = false;
  }
  
  // Refresh storage contents display
  refreshStorageContents();
}

// Create a test token in localStorage
function createTestToken() {
  try {
    const testToken = {
      idToken: 'test-id-token-' + Date.now(),
      accessToken: 'test-access-token',
      refreshToken: 'test-refresh-token',
      expiresIn: 3600,
      tokenType: 'Bearer'
    };
    
    localStorage.setItem('atlas_cognito_tokens', JSON.stringify(testToken));
    tokenTestResult.value = `Test token created: ${JSON.stringify(testToken, null, 2)}`;
    
    // Refresh storage contents display
    refreshStorageContents();
  } catch (error) {
    tokenTestResult.value = `Error creating test token: ${error.message}`;
  }
}

// Check if the test token exists
function checkTestToken() {
  try {
    const tokenStr = localStorage.getItem('atlas_cognito_tokens');
    if (tokenStr) {
      const token = JSON.parse(tokenStr);
      tokenTestResult.value = `Token found: ${JSON.stringify(token, null, 2)}`;
    } else {
      tokenTestResult.value = 'No token found in localStorage';
    }
  } catch (error) {
    tokenTestResult.value = `Error checking token: ${error.message}`;
  }
}

// Refresh the display of storage contents
function refreshStorageContents() {
  try {
    const items = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      let value = localStorage.getItem(key);
      
      // Try to parse JSON values
      try {
        value = JSON.parse(value);
      } catch (e) {
        // Keep as string if not valid JSON
      }
      
      items[key] = value;
    }
    
    localStorageContents.value = JSON.stringify(items, null, 2);
  } catch (error) {
    localStorageContents.value = `Error reading storage: ${error.message}`;
  }
}

// Navigation functions
function goToLogin() {
  router.push('/login');
}

function goToTokenDebug() {
  router.push('/token-debug');
}

// Initialize
onMounted(() => {
  refreshStorageContents();
});
</script>

<style scoped>
.storage-test {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}

h1 {
  color: #2c3e50;
  border-bottom: 1px solid #eee;
  padding-bottom: 1rem;
  margin-bottom: 2rem;
}

.test-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

h2 {
  margin-top: 0;
  color: #2c3e50;
  font-size: 1.5rem;
}

.test-controls {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.test-button {
  padding: 0.5rem 1rem;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.test-button:hover {
  background-color: #45a049;
}

.test-button.clear {
  background-color: #f44336;
}

.test-button.clear:hover {
  background-color: #d32f2f;
}

.result-box {
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 1rem;
  margin-top: 1rem;
}

.result-box.success {
  border-color: #4CAF50;
  background-color: #f1f8e9;
}

.result-box.error {
  border-color: #f44336;
  background-color: #ffebee;
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
  background-color: #f5f5f5;
  padding: 0.5rem;
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
  justify-content: center;
}

.nav-button {
  padding: 0.75rem 1.5rem;
  background-color: #2c3e50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.nav-button:hover {
  background-color: #1a202c;
}
</style>
