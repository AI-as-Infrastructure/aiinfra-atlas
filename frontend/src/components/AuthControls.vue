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
  margin: 0;
  padding: 0;
  vertical-align: top;
  line-height: 1;
  height: 40px;
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
  background-color: #000 !important;
  color: #fff !important;
  border: none !important;
  padding: 0;
  border-radius: 2px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100px;
  height: 40px;
  transition: background-color 0.2s;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  -webkit-appearance: none !important;
  -moz-appearance: none !important;
  appearance: none !important;
  box-shadow: none !important;
}

.auth-button:hover {
  background-color: #888 !important;
  color: #fff !important;
}
</style>
