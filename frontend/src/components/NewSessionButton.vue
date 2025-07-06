<template>
  <div class="session-button-container">
    <div v-if="showRefreshedMessage" class="session-refreshed-message">
      <div class="refreshed-content">
        <span class="check-icon">✓</span>
        <span class="refreshed-text">Session refreshed!</span>
      </div>
    </div>
    <a class="new-session-link nav-link" @click.prevent="newSession">New Session</a>
  </div>
</template>

<script setup>
import { useSessionStore } from '@/stores/session'
import { ref } from 'vue'

const session = useSessionStore()
const showRefreshedMessage = ref(false)

function newSession() {
  session.newSession()
  showRefreshedMessage.value = true
  
  // Hide the message after 3 seconds
  setTimeout(() => {
    showRefreshedMessage.value = false
  }, 3000)
}
</script>

<style scoped>
.session-button-container {
  display: flex;
  align-items: center;
}

.session-refreshed-message {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  padding: 1rem;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 8px;
  animation: slideInFade 0.3s ease-in-out;
}

.refreshed-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #155724;
  font-weight: 500;
}

.check-icon {
  background-color: #28a745;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.refreshed-text {
  font-size: 14px;
}

@keyframes slideInFade {
  from { 
    opacity: 0;
    transform: translateX(100%);
  }
  to { 
    opacity: 1;
    transform: translateX(0);
  }
}
</style>