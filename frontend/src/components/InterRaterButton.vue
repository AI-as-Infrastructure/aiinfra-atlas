<template>
  <div v-if="isEnabled" class="inter-rater-nav-item">
    <router-link 
      to="/inter-rater" 
      class="nav-link inter-rater-link"
      :class="{ 'has-sessions': availableSessions > 0 }"
    >
      Inter-rating
      <span v-if="availableSessions > 0" class="session-count">
        ({{ availableSessions }})
      </span>
    </router-link>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  name: 'InterRaterButton',
  setup() {
    const isEnabled = ref(false)
    const availableSessions = ref(0)

    const checkInterRaterStatus = async () => {
      try {
        const response = await fetch('/api/inter-rater/stats')
        const data = await response.json()
        
        isEnabled.value = data.enabled || false
        availableSessions.value = data.available_sessions || 0
      } catch (error) {
        console.error('Error checking inter-rater status:', error)
        isEnabled.value = false
      }
    }

    onMounted(() => {
      checkInterRaterStatus()
      
      // Refresh status periodically if enabled
      if (isEnabled.value) {
        setInterval(checkInterRaterStatus, 300000) // Every 5 minutes
      }
    })

    return {
      isEnabled,
      availableSessions
    }
  }
}
</script>

<style scoped>
.inter-rater-nav-item {
  display: inline-block;
}

.inter-rater-link {
  color: #363636;
  text-decoration: none;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.inter-rater-link:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #3273dc;
}

.inter-rater-link.router-link-active {
  color: #3273dc;
  font-weight: 600;
}

.session-count {
  font-size: 0.875rem;
  color: #3273dc;
  font-weight: 600;
}

.has-sessions {
  position: relative;
}

.has-sessions::after {
  content: '';
  position: absolute;
  top: 8px;
  right: 8px;
  width: 6px;
  height: 6px;
  background-color: #ff3860;
  border-radius: 50%;
}
</style>
