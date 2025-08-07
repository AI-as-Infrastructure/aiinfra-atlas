<template>
  <div v-if="showAuthUI" class="auth-controls">
    <div v-if="isLoggedIn">
      <button @click="logout" class="auth-text-button logout-button">Logout</button>
    </div>
    <div v-else>
      <button @click="login" class="auth-text-button login-button">Login</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();

// Computed values from auth store
const isLoggedIn = computed(() => authStore.isLoggedIn);
const showAuthUI = computed(() => authStore.showAuthUI);
const username = computed(() => authStore.username);

// Methods
function login() {
  authStore.login();
}

async function logout() {
  await authStore.logout();
}
</script>

<style scoped>
.auth-controls {
  display: flex;
  align-items: center;
  margin: 0;
  padding: 0;
  vertical-align: top;
  line-height: 1;
  height: 40px;
}

.auth-controls > div {
  display: flex;
  align-items: center;
  height: 100%;
  margin: 0;
  padding: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.username {
  font-size: 0.9rem;
  color: #666;
}

.auth-text-button {
  color: #181818 !important;
  background: none !important;
  border: none !important;
  text-decoration: none !important;
  cursor: pointer;
  font-family: inherit;
  font-weight: 500;
  font-size: 0.875rem;
  padding: 8px 12px;
  border-radius: 0;
  transition: color 0.2s;
  border-bottom: 2px solid transparent;
  position: relative;
  -webkit-appearance: none !important;
  -moz-appearance: none !important;
  appearance: none !important;
  box-shadow: none !important;
  outline: none;
  white-space: nowrap;
  display: flex;
  align-items: center;
  height: 40px;
  margin: 0;
  vertical-align: top;
  line-height: 1;
}

.auth-text-button:hover, .auth-text-button:focus {
  color: #111 !important;
  text-decoration: underline !important;
  border-bottom: none;
  background: none !important;
}
</style>
