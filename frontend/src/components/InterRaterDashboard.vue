<template>
  <div class="inter-rater-dashboard">
    <!-- #73: only shown when there is genuinely nothing to render. A return
         from FAQ or About keeps the validated allocation and skips this. -->
    <div v-if="loading" class="loading-state">
      <div class="has-text-centered">
        <div class="loading-spinner"></div>
        <p class="mt-3">Loading inter-rating tasks, please wait...</p>
      </div>
    </div>

    <div v-else-if="error" class="error-state">
      <div class="notification error-notice">
        <h4 class="title is-4">Error Loading Sessions</h4>
        <p>{{ error }}</p>
        <div class="buttons mt-3">
          <button @click="loadSessions" class="button is-link">
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
        <button
          v-if="hasCompletedAllSessions && completedSessions > 0"
          class="button is-small history-button mt-3"
          @click="showHistory = true"
        >
          Review my ratings ({{ completedSessions }})
        </button>
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
          <div class="level-right">
            <div class="level-item">
              <button
                class="button is-small history-button"
                :disabled="completedSessions === 0"
                @click="showHistory = true"
              >
                Review my ratings ({{ completedSessions }})
              </button>
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
                <span class="stat-label">Completed</span>
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

    <!-- Read-only, own ratings only, current run only. Opening it consumes
         nothing: the dashboard stays mounted behind the overlay, so the
         reviewer returns to the item and any in-progress scores. -->
    <InterRaterHistory v-if="showHistory" @close="showHistory = false" />

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
import { computed, onMounted, onActivated, ref, watch } from 'vue'
import InterRaterPlayback from './InterRaterPlayback.vue'
import InterRaterHistory from './InterRaterHistory.vue'
import { useInterRaterStore } from '../stores/interRater'
import { useAuthStore } from '../stores/auth'
import { get, post } from '../utils/api'

export default {
  name: 'InterRaterDashboard',
  components: {
    InterRaterPlayback,
    InterRaterHistory
  },
  setup() {
    const store = useInterRaterStore()

    const loading = ref(false)
    const error = ref(null)
    const showSuccessMessage = ref(false)
    const successMessage = ref('')
    const hasCompletedAllSessions = ref(false)
    const showHistory = ref(false)

    let auth = null
    try {
      auth = useAuthStore()
    } catch (e) {
      // Auth store is absent in ad-hoc/no-auth modes; state stays per-browser.
    }

    const sessions = computed(() => store.allocation)
    const currentSessionIndex = computed({
      get: () => store.currentIndex,
      set: (v) => { store.currentIndex = v }
    })
    const completedSessions = computed(() => store.completedCount)
    const currentSession = computed(() => sessions.value[currentSessionIndex.value] || null)
    let loadVersion = 0
    let loadPromise = null

    const flash = (message) => {
      successMessage.value = message
      showSuccessMessage.value = true
      setTimeout(() => { showSuccessMessage.value = false }, 2000)
    }

    const requestSessions = (supersede = false) => {
      if (loadPromise && !supersede) return loadPromise

      const version = supersede ? ++loadVersion : loadVersion
      const request = (async () => {
        loading.value = !store.validated
        error.value = null

        try {
          const data = await get('/inter-rater/sessions')
          if (version !== loadVersion) return

          store.applyAllocation({
            sessions: data.sessions || [],
            snapshot: data.allocation_snapshot_id,
            completed: data.completed_sessions,
            target: data.max_sessions_per_user || (data.sessions || []).length
          })

          hasCompletedAllSessions.value =
            sessions.value.length === 0 &&
            store.targetSessions > 0 &&
            store.completedCount >= store.targetSessions
        } catch (err) {
          if (version !== loadVersion) return
          console.error('Error loading inter-rater sessions:', err)
          if (err.message && err.message.includes('No sessions with feedback found')) {
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
          if (version === loadVersion) loading.value = false
        }
      })()

      loadPromise = request
      request.finally(() => {
        if (loadPromise === request) loadPromise = null
      })
      return request
    }

    const loadSessions = () => requestSessions(false)

    const announceProgress = () => {
      // #67: the header count refreshes on every submission, not only on quota
      // completion, and without waiting for the 5-minute poll.
      window.dispatchEvent(new CustomEvent('inter-rater-completed'))
    }

    const showCompletionMessage = () => {
      hasCompletedAllSessions.value = true
      successMessage.value = `All sessions completed! You've successfully rated ${store.completedCount} sessions.`
      showSuccessMessage.value = true
      store.completeRun()

      setTimeout(() => {
        showSuccessMessage.value = false
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }, 3000)
    }

    const quotaMet = () =>
      store.targetSessions > 0 && store.completedCount >= store.targetSessions

    const afterQueueChange = async () => {
      if (sessions.value.length > 0) {
        window.scrollTo({ top: 0, behavior: 'smooth' })
        return
      }
      if (quotaMet()) {
        showCompletionMessage()
        return
      }

      await loadSessions()
      if (sessions.value.length > 0 || quotaMet()) {
        if (quotaMet() && sessions.value.length === 0) showCompletionMessage()
        return
      }

      // Quota is NOT met and no replacement came back. Do not congratulate a
      // reviewer who is at 19/20 — a capacity or out-of-pool refusal on the
      // last local item lands here. Stay incomplete and recoverable.
      hasCompletedAllSessions.value = false
      error.value =
        'No replacement prompt is available right now. Your progress is saved — ' +
        'use Try Again in a moment.'
    }

    const handleFeedbackSubmission = async (feedbackData) => {
      try {
        const result = await post('/feedback', feedbackData)
        const spanId = feedbackData.original_span_id

        if (result.status === 'success') {
          store.markRated(spanId)
          announceProgress()
          flash('Inter-rating submitted! Loading next session...')
          await afterQueueChange()

        } else if (result.status === 'already_rated') {
          // Confirms this reviewer rated it — reviewer-scoped, survives a
          // snapshot change. Not a concurrency loss, and said so.
          store.markRated(spanId)
          announceProgress()
          flash('You have already rated this prompt.')
          await afterQueueChange()

        } else if (result.status === 'session_unavailable' || result.status === 'out_of_pool') {
          // Someone else filled it, or it left the pool. Not a rating by this
          // reviewer, so it must not enter the recently-rated set.
          store.markUnavailable(spanId)
          flash(result.message || 'That prompt is no longer available.')
          await afterQueueChange()

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
        setTimeout(() => { error.value = null }, 10000)
      }
    }

    // Auth initialises asynchronously; at setup `username` is still null, so
    // state would otherwise be restored under the shared "anon" key and a
    // second reviewer on this browser could inherit it.
    if (auth) {
      watch(
        () => auth.username,
        (name) => {
          if (!store.setReviewer(name)) return

          store.resetReviewerState(store.reviewerResolved())
          hasCompletedAllSessions.value = false
          if (store.reviewerResolved()) {
            requestSessions(true)
          } else {
            loadVersion += 1
            loadPromise = null
            loading.value = false
          }
        },
        { immediate: true }
      )
    }

    onMounted(() => {
      if (!store.validated) loadSessions()
    })

    // #73: a KeepAlive return reuses live state and issues no request.
    onActivated(() => {
      if (!store.validated) loadSessions()
    })

    return {
      store,
      sessions,
      currentSession,
      currentSessionIndex,
      loading,
      error,
      showSuccessMessage,
      successMessage,
      completedSessions,
      hasCompletedAllSessions,
      showHistory,
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

/* Monochrome error panel, matching global.css (#fff / #eee / #888 / #000).
   Bulma's is-danger pink is off-palette for this UI. */
.error-notice {
  max-width: 40rem;
  background-color: #fff;
  color: #000;
  border: 1px solid #eee;
  border-left: 3px solid #000;
  border-radius: 4px;
  padding: 1.5rem;
  text-align: left;
}

.error-notice .title {
  color: #000;
  margin-bottom: 0.75rem;
}

.error-notice p {
  color: #000;
  font-size: 0.95rem;
  word-break: break-word;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #eee;
  border-top: 4px solid #000;
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
