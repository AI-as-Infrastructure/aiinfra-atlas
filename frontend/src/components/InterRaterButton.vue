<template>
  <div v-if="isEnabled || isLoading" class="inter-rater-nav-item">
    <router-link 
      v-if="!isLoading"
      to="/inter-rater" 
      class="nav-link inter-rater-link"
      :class="{ 'has-sessions': availableSessions > 0 }"
    >
      Inter-rate ({{ availableSessions }})
    </router-link>
    <span v-else class="loading-text">Loading...</span>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  name: 'InterRaterButton',
  setup() {
    const isEnabled = ref(false)
    const availableSessions = ref(0)
    const isLoading = ref(true)

    const checkInterRaterStatus = async () => {
      isLoading.value = true
      try {
        const response = await fetch('/api/inter-rater/stats')
        const data = await response.json()
        
        isEnabled.value = data.enabled || false
        availableSessions.value = data.available_sessions || 0
      } catch (error) {
        console.error('Error checking inter-rater status:', error)
        isEnabled.value = false
      } finally {
        isLoading.value = false
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
      availableSessions,
      isLoading
    }
  }
}
</script>

<style scoped>
.inter-rater-nav-item {
  display: flex;
  align-items: center;
  margin: 0;
  padding: 0;
  vertical-align: top;
  line-height: 1;
  height: 40px;
}

.inter-rater-link {
  background-color: #000 !important;
  color: #fff !important;
  border: none !important;
  text-decoration: none !important;
  padding: 0;
  border-radius: 2px;
  font-weight: 500;
  font-size: 0.875rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100px;
  height: 40px;
  cursor: pointer;
  outline: none;
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

.inter-rater-link:hover {
  background-color: #888 !important;
  color: #fff !important;
  text-decoration: none !important;
}

.inter-rater-link.router-link-active {
  background-color: #888 !important;
  color: #fff !important;
  font-weight: 600;
}

.inter-rater-link.router-link-exact-active {
  background-color: #888 !important;
  color: #fff !important;
}

/* Removed session-count styling - now integrated into main button text */

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

.loading-text {
  font-size: 0.875rem;
  color: #6c757d;
  font-style: italic;
  font-weight: normal;
}

/* Removed unused pulse animation */
</style>
