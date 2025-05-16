<template>
  <div class="session-button-container">
    <span v-if="showRefreshedMessage" class="session-refreshed-message">Session refreshed!</span>
    <a class="new-session-link" @click.prevent="newSession">New Session</a>
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
  margin-right: 1rem;
  color: #008000; 
  font-size: 0.9rem;
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>