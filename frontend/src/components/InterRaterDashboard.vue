<template>
  <div class="inter-rater-dashboard">
    <div v-if="loading" class="loading-state">
      <div class="has-text-centered">
        <div class="loading-spinner"></div>
        <p class="mt-3">Loading inter-ratings...</p>
      </div>
    </div>

    <div v-else-if="error" class="error-state">
      <div class="notification is-danger">
        <h4 class="title is-4">Error Loading Sessions</h4>
        <p>{{ error }}</p>
        <div class="buttons mt-3">
          <button @click="loadSessions" class="button is-danger is-outlined">
            Try Again
          </button>
        </div>
      </div>
    </div>

    <div v-else-if="sessions.length === 0" class="empty-state">
      <div class="has-text-centered">
        <div class="icon-container mb-4">
          <i v-if="hasCompletedAllSessions" class="fas fa-check-circle fa-3x has-text-success"></i>
          <i v-else class="fas fa-info-circle fa-3x has-text-info"></i>
        </div>
        <h3 v-if="hasCompletedAllSessions" class="title is-4">Thank You!</h3>
        <h3 v-else class="title is-4">No Sessions Available</h3>
        <p v-if="hasCompletedAllSessions" class="subtitle is-6">
          You have successfully completed all your assigned inter-rating sessions. <br></br>
          Your contributions help us explore whether Large Language Models can be safely used in the research and cultural sectors.
        </p>
        <p v-else class="subtitle is-6">
          No sessions are currently available for inter-rating.
        </p>
      </div>
    </div>

    <div v-else class="active-sessions">
      <div class="dashboard-header mb-5">
        <div class="level">
          <div class="level-left">
            <div class="level-item">
              <div>
                <p class="subtitle is-5">
                  Please review these sessions and provide your independent feedback assessment.
                </p>
              </div>
            </div>
          </div>
        </div>
        
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
                <span class="stat-label">Remaining Sessions</span>
              </div>
            </div>
            <div class="column">
              <div class="stat-item">
                <span class="stat-number">{{ completedSessions }}</span>
                <span class="stat-label">Completed This Visit</span>
              </div>
            </div>
          </div>
        </div>

        <progress
          class="progress" style="background-color: #e9ecef;" :style="{ '--progress-value': ((currentSessionIndex + 1) / sessions.length) * 100 + '%' }"
          :value="currentSessionIndex + 1"
          :max="sessions.length"
        >
          {{ Math.round(((currentSessionIndex + 1) / sessions.length) * 100) }}%
        </progress>
      </div>

      <InterRaterPlayback
        v-if="currentSession"
        :session="currentSession"
        :current-index="currentSessionIndex"
        :total-sessions="sessions.length"
        @submit-feedback="handleFeedbackSubmission"
      />
    </div>

    <!-- Success notification - small popup like NewSessionButton -->
    <div v-if="showSuccessMessage" class="inter-rater-success-message">
      <div class="success-content">
        <span class="check-icon">✓</span>
        <span class="success-text">{{ successMessage }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import InterRaterPlayback from './InterRaterPlayback.vue'
import { get, post } from '../utils/api'

export default {
  name: 'InterRaterDashboard',
  components: {
    InterRaterPlayback
  },
  setup() {
    
    const sessions = ref([])
    const currentSessionIndex = ref(0)
    const loading = ref(true)
    const error = ref(null)
    const showSuccessMessage = ref(false)
    const successMessage = ref('')
    const completedSessions = ref(0)  // Track completed in this visit
    const hasCompletedAllSessions = ref(false)  // Track if user has no remaining sessions

    const currentSession = computed(() => {
      return sessions.value[currentSessionIndex.value] || null
    })

    const loadSessions = async () => {
      loading.value = true
      error.value = null

      try {
        const data = await get('/inter-rater/sessions')
        sessions.value = data.sessions || []

        // Reset session index if we have sessions
        if (sessions.value.length > 0) {
          currentSessionIndex.value = 0
        }

      } catch (err) {
        console.error('Error loading inter-rater sessions:', err)
        // Provide more detailed error messages
        if (err.message && err.message.includes('No sessions with feedback found')) {
          // This shouldn't happen anymore with the backend fix, but just in case
          sessions.value = []
          error.value = null
        } else if (err.message && err.message.includes('Phoenix')) {
          error.value = `Phoenix Connection Issue: ${err.message}`
        } else if (err.message && err.message.includes('project')) {
          error.value = `Project Configuration Issue: ${err.message}`
        } else if (err.message && err.message.includes('500')) {
          error.value = 'No sessions are currently available for inter-rating. Please check back later or contact your administrator.'
        } else {
          error.value = err.message || 'Failed to load sessions. Please check the server logs for details.'
        }
      } finally {
        loading.value = false
      }
    }

    const handleFeedbackSubmission = async (feedbackData) => {
      try {
        console.log('Submitting inter-rater feedback:', feedbackData)

        const result = await post('/feedback', feedbackData)
        console.log('API Response:', result)

        if (result.status === 'success') {
          // Remove submitted session locally — re-fetching risks returning it again
          // before Phoenix propagates the new annotation to the cache
          sessions.value.splice(currentSessionIndex.value, 1)
          completedSessions.value++

          if (sessions.value.length === 0) {
            successMessage.value = 'All inter-ratings complete!'
            showSuccessMessage.value = true
            setTimeout(() => {
              showSuccessMessage.value = false
              showCompletionMessage()
            }, 2000)
          } else {
            currentSessionIndex.value = 0
            successMessage.value = 'Inter-rating submitted! Loading next session...'
            showSuccessMessage.value = true
            setTimeout(() => {
              showSuccessMessage.value = false
              window.scrollTo({ top: 0, behavior: 'smooth' })
            }, 2000)
          }

        } else if (result.status === 'session_unavailable') {
          // Session deleted from Phoenix after allocation - remove locally, don't re-fetch
          sessions.value.splice(currentSessionIndex.value, 1)
          if (sessions.value.length > 0) {
            currentSessionIndex.value = 0
            successMessage.value = 'Session no longer available, loading next...'
            showSuccessMessage.value = true
            setTimeout(() => { showSuccessMessage.value = false }, 2000)
          } else {
            // No sessions remain — dispatch event so nav button updates
            window.dispatchEvent(new CustomEvent('inter-rater-completed'))
          }

        } else {
          throw new Error(result.message || 'Failed to submit inter-rating')
        }

      } catch (err) {
        console.error('Error submitting inter-rater feedback:', err)

        let errorMsg = 'Failed to submit inter-rating'
        if (err.message.includes('HTTP 500')) {
          errorMsg = 'Server error occurred. Please try again in a moment.'
        } else if (err.message.includes('HTTP 400')) {
          errorMsg = 'Invalid feedback data. Please check all fields are completed.'
        } else {
          errorMsg = `${errorMsg}: ${err.message}`
        }

        error.value = errorMsg

        // Clear error after 10 seconds
        setTimeout(() => {
          error.value = null
        }, 10000)
      }
    }


    const showCompletionMessage = () => {
      // Show completion notification and set completion flag
      hasCompletedAllSessions.value = true
      successMessage.value = `All sessions completed! You've successfully rated ${completedSessions.value} sessions this visit.`
      showSuccessMessage.value = true

      // Clear sessions to prevent showing old content
      sessions.value = []
      currentSessionIndex.value = 0

      setTimeout(() => {
        showSuccessMessage.value = false

        // Scroll to top to show the thank you message properly
        window.scrollTo({
          top: 0,
          behavior: 'smooth'
        })

        // Emit event to update button counter
        window.dispatchEvent(new CustomEvent('inter-rater-completed'))
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
      hasCompletedAllSessions,
      loadSessions,
      handleFeedbackSubmission
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

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #6c757d;
  border-radius: 50%;
  margin: 0 auto 1rem auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.icon-container {
  opacity: 0.7;
}

.dashboard-header {
  text-align: center;
  margin-bottom: 2rem;
}

.stats-bar {
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
  color: #495057;
  line-height: 1;
}

/* Custom progress bar styling */
.progress::-webkit-progress-value {
  background-color: #28a745;
}

.progress::-moz-progress-bar {
  background-color: #28a745;
}

.stat-label {
  font-size: 0.875rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 0.25rem;
}

/* Success notification styling - matching NewSessionButton */
.inter-rater-success-message {
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

.success-content {
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

.success-text {
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
