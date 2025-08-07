<template>
  <div v-if="isEnabled || isLoading" class="inter-rater-nav-item">
    <router-link 
      v-if="!isLoading"
      to="/inter-rater" 
      class="nav-text-link inter-rater-link"
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

    const checkInterRaterStatus = async (forceUpdate = false) => {
      isLoading.value = true
      try {
        const response = await fetch('/api/inter-rater/stats')
        const data = await response.json()
        
        isEnabled.value = data.enabled || false
        
        // Don't override if we already set it to 0 due to completion, unless forced
        if (forceUpdate || availableSessions.value !== 0) {
          availableSessions.value = data.available_sessions || 0
        }
        
        // Pre-load sessions if there are any available (improves UX when user clicks button)
        if (data.enabled && data.available_sessions > 0) {
          console.log('Pre-loading inter-rater sessions for better UX...')
          preloadInterRaterSessions()
        }
      } catch (error) {
        console.error('Error checking inter-rater status:', error)
        isEnabled.value = false
      } finally {
        isLoading.value = false
      }
    }

    const preloadInterRaterSessions = async () => {
      try {
        // Pre-load the sessions data in the background
        const response = await fetch('/api/inter-rater/sessions')
        if (response.ok) {
          console.log('Inter-rater sessions pre-loaded successfully')
          // Data will be cached by the backend for faster access when user navigates
        } else {
          console.warn('Failed to pre-load inter-rater sessions:', response.status)
        }
      } catch (error) {
        console.warn('Error pre-loading inter-rater sessions:', error)
        // Non-critical error, don't show to user
      }
    }

    onMounted(() => {
      checkInterRaterStatus()
      
      // Refresh status periodically if enabled
      if (isEnabled.value) {
        setInterval(checkInterRaterStatus, 300000) // Every 5 minutes
      }
      
      // Listen for completion events to refresh immediately
      window.addEventListener('inter-rater-completed', () => {
        // Immediately set counter to 0 for instant feedback
        availableSessions.value = 0
        
        // No need to check backend - user has completed all their sessions
        // Backend state might be inconsistent briefly, but user experience is more important
      })
    })

    return {
      isEnabled,
      availableSessions,
      isLoading,
      checkInterRaterStatus
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
  /* Use underlined text style - inherits from nav-text-link in App.vue */
  white-space: nowrap;
  min-width: auto;
  width: auto;
}

/* Removed session-count styling - now integrated into main button text */

.has-sessions {
  position: relative;
}

.has-sessions::after {
  content: '';
  position: absolute;
  top: 8px;
  right: 5px;
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
