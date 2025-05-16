<template>
  <div v-if="showAuthUI" class="auth-controls">
    <div v-if="isLoggedIn">
      <button @click="logout" class="auth-button logout-button">Logout</button>
    </div>
    <div v-else>
      <button @click="login" class="auth-button login-button">Login</button>
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
  margin-left: auto;
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

.auth-button {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
  transition: background-color 0.2s;
}

.login-button {
  background-color: #2c3e50;
  color: white;
}

.login-button:hover {
  background-color: #1a252f;
}

.logout-button {
  background-color: #e74c3c;
  color: white;
}

.logout-button:hover {
  background-color: #c0392b;
}
</style>
