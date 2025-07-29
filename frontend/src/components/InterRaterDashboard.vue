<template>
  <div class="inter-rater-dashboard">
    <div v-if="loading" class="loading-state">
      <div class="has-text-centered">
        <button class="button is-loading is-large">Loading</button>
        <p class="mt-3">Loading sessions for inter-rating...</p>
      </div>
    </div>

    <div v-else-if="error" class="error-state">
      <div class="notification is-danger">
        <h4 class="title is-4">Error Loading Sessions</h4>
        <p>{{ error }}</p>
        <button @click="loadSessions" class="button is-danger is-outlined mt-3">
          Try Again
        </button>
      </div>
    </div>

    <div v-else-if="sessions.length === 0" class="empty-state">
      <div class="has-text-centered">
        <div class="icon-container mb-4">
          <i class="fas fa-info-circle fa-3x has-text-info"></i>
        </div>
        <h3 class="title is-4">No Sessions Available</h3>
        <p class="subtitle is-6">
          No sessions are currently available for inter-rating.
        </p>
        <div class="notification is-info is-light mt-4" style="text-align: left; max-width: 600px; margin: 0 auto;">
          <h4 class="title is-6">Sessions become available when:</h4>
          <ul>
            <li>• Other users provide feedback that needs validation</li>
            <li>• There are existing sessions with user feedback in Phoenix</li>
            <li>• The Phoenix project contains data for the configured time period</li>
          </ul>
        </div>
        <router-link to="/" class="button is-primary mt-4">
          Return to Home
        </router-link>
      </div>
    </div>

    <div v-else class="active-sessions">
      <div class="dashboard-header mb-5">
        <h2 class="title is-3">Inter-rater Reliability</h2>
        <p class="subtitle is-5">
          Please review these sessions and provide your independent feedback assessment.
        </p>
        
        <div class="stats-bar">
          <div class="columns">
            <div class="column">
              <div class="stat-item">
                <span class="stat-number">{{ currentSessionIndex + 1 }}</span>
                <span class="stat-label">Current Session</span>
              </div>
            </div>
            <div class="column">
              <div class="stat-item">
                <span class="stat-number">{{ sessions.length }}</span>
                <span class="stat-label">Total Sessions</span>
              </div>
            </div>
            <div class="column">
              <div class="stat-item">
                <span class="stat-number">{{ completedSessions }}</span>
                <span class="stat-label">Completed</span>
              </div>
            </div>
          </div>
        </div>

        <progress 
          class="progress is-primary" 
          :value="completedSessions" 
          :max="sessions.length"
        >
          {{ Math.round((completedSessions / sessions.length) * 100) }}%
        </progress>
      </div>

      <InterRaterPlayback
        v-if="currentSession"
        :session="currentSession"
        :current-index="currentSessionIndex"
        :total-sessions="sessions.length"
        @submit-feedback="handleFeedbackSubmission"
        @skip-session="handleSkipSession"
      />
    </div>

    <!-- Success notification -->
    <div v-if="showSuccessMessage" class="notification is-success is-overlay">
      <button @click="showSuccessMessage = false" class="delete"></button>
      <strong>Success!</strong> {{ successMessage }}
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import InterRaterPlayback from './InterRaterPlayback.vue'

export default {
  name: 'InterRaterDashboard',
  components: {
    InterRaterPlayback
  },
  setup() {
    const router = useRouter()
    
    const sessions = ref([])
    const currentSessionIndex = ref(0)
    const loading = ref(true)
    const error = ref(null)
    const showSuccessMessage = ref(false)
    const successMessage = ref('')
    const completedSessions = ref(0)

    const currentSession = computed(() => {
      return sessions.value[currentSessionIndex.value] || null
    })

    const loadSessions = async () => {
      loading.value = true
      error.value = null
      
      try {
        const response = await fetch('/api/inter-rater/sessions')
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        sessions.value = data.sessions || []
        
        // Reset session index if we have sessions
        if (sessions.value.length > 0) {
          currentSessionIndex.value = 0
        }
        
      } catch (err) {
        console.error('Error loading inter-rater sessions:', err)
        // Provide more detailed error messages
        if (err.message && err.message.includes('Phoenix')) {
          error.value = `Phoenix Connection Issue: ${err.message}`
        } else if (err.message && err.message.includes('project')) {
          error.value = `Project Configuration Issue: ${err.message}`
        } else {
          error.value = err.message || 'Failed to load sessions. Please check the server logs for details.'
        }
      } finally {
        loading.value = false
      }
    }

    const handleFeedbackSubmission = async (feedbackData) => {
      try {
        const response = await fetch('/api/feedback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(feedbackData)
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const result = await response.json()
        
        if (result.status === 'success') {
          successMessage.value = 'Rating submitted successfully!'
          showSuccessMessage.value = true
          
          // Auto-hide success message and move to next session
          setTimeout(() => {
            showSuccessMessage.value = false
            moveToNextSession()
          }, 1500)
          
        } else {
          throw new Error(result.message || 'Failed to submit feedback')
        }

      } catch (err) {
        console.error('Error submitting inter-rater feedback:', err)
        error.value = `Failed to submit feedback: ${err.message}`
      }
    }

    const handleSkipSession = () => {
      moveToNextSession()
    }

    const moveToNextSession = () => {
      completedSessions.value++
      
      if (currentSessionIndex.value < sessions.value.length - 1) {
        currentSessionIndex.value++
      } else {
        // All sessions completed
        showCompletionMessage()
      }
    }

    const showCompletionMessage = () => {
      // Show completion notification and redirect
      successMessage.value = `🎉 All sessions completed! You've successfully rated ${completedSessions.value} sessions.`
      showSuccessMessage.value = true
      setTimeout(() => {
        showSuccessMessage.value = false
        router.push('/')
      }, 3000)
    }

    onMounted(() => {
      loadSessions()
    })

    return {
      sessions,
      currentSession,
      currentSessionIndex,
      loading,
      error,
      showSuccessMessage,
      successMessage,
      completedSessions,
      loadSessions,
      handleFeedbackSubmission,
      handleSkipSession
    }
  }
}
</script>

<style scoped>
.inter-rater-dashboard {
  min-height: 80vh;
  padding: 2rem 1rem;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.icon-container {
  opacity: 0.7;
}

.dashboard-header {
  text-align: center;
  margin-bottom: 2rem;
}

.stats-bar {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  margin: 1rem 0;
}

.stat-item {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  color: #3273dc;
  line-height: 1;
}

.stat-label {
  font-size: 0.875rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 0.25rem;
}

.notification.is-overlay {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  max-width: 400px;
}

@media (max-width: 768px) {
  .inter-rater-dashboard {
    padding: 1rem 0.5rem;
  }
  
  .stats-bar .columns {
    text-align: center;
  }
  
  .stat-number {
    font-size: 1.5rem;
  }
}
</style>
