<template>
  <div class="history-overlay" role="dialog" aria-modal="true" aria-label="Your ratings">
    <div class="history-panel">
      <header class="history-header">
        <div>
          <h3 class="title is-5 mb-1">Your ratings</h3>
          <p class="history-subtitle">
            This run only, and only your own ratings. Read-only — recorded ratings cannot be changed.
          </p>
        </div>
        <button class="button is-small" @click="$emit('close')">Close</button>
      </header>

      <div v-if="loading" class="history-state">
        <div class="loading-spinner"></div>
        <p class="mt-3">Loading your ratings…</p>
      </div>

      <!-- Fail loudly: an empty list must never stand in for a failed read. -->
      <div v-else-if="error" class="notification error-notice">
        <p><strong>Your ratings could not be loaded.</strong></p>
        <p>{{ error }}</p>
        <button class="button is-small mt-3" @click="load">Try again</button>
      </div>

      <div v-else-if="ratings.length === 0 && !syncing" class="history-state">
        <p>You have not completed any ratings in this run yet.</p>
      </div>

      <div v-else-if="ratings.length === 0 && syncing" class="history-state">
        <p><strong>Your most recent ratings are still syncing.</strong></p>
        <p>They are recorded — they are not visible here yet.</p>
        <button class="button is-small mt-3" @click="load">Retry</button>
      </div>

      <div v-else class="history-list">
        <div v-if="syncing" class="notification sync-notice">
          Some of your most recent ratings are still syncing and are not shown
          below yet. This list is incomplete.
          <button class="button is-small ml-2" @click="load">Retry</button>
        </div>
        <article v-for="entry in ratings" :key="entry.span_id" class="history-entry">
          <h4 class="history-question">{{ entry.question }}</h4>

          <div class="history-answer content" v-html="renderAnswer(entry.answer)"></div>

          <table class="history-scores">
            <tbody>
              <tr v-for="criterion in CRITERIA" :key="criterion.key">
                <th>{{ criterion.label }}</th>
                <td class="history-score">{{ display(entry.scores[criterion.key]) }}</td>
                <td class="history-rationale">{{ entry.rationales[criterion.key] || '—' }}</td>
              </tr>
            </tbody>
          </table>

          <p class="history-faults">
            <strong>Faults:</strong>
            <span v-if="entry.faults.length">{{ entry.faults.join(', ') }}</span>
            <span v-else>none recorded</span>
          </p>
          <p v-if="entry.faults_rationale" class="history-note">
            <strong>Fault rationale:</strong> {{ entry.faults_rationale }}
          </p>
          <p v-if="entry.additional_comments" class="history-note">
            <strong>Additional comments:</strong> {{ entry.additional_comments }}
          </p>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
// Read-only view of the reviewer's own ratings for the current run (#72).
// Scoping is enforced server-side by rater_id — this component never asks for
// a reviewer, and offers no control that could alter a recorded rating.
import { ref, onMounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { get } from '../utils/api'
import { useInterRaterStore } from '../stores/interRater'

defineEmits(['close'])

const CRITERIA = [
  { key: 'corpus_fidelity', label: 'Corpus Fidelity' },
  { key: 'citation_quality', label: 'Citation Quality' },
  { key: 'relevance', label: 'Relevance' },
  { key: 'coherence', label: 'Coherence' },
  { key: 'uncertainty', label: 'Uncertainty' },
  { key: 'historical_contextualisation', label: 'Historical Contextualisation' }
]

const store = useInterRaterStore()
const ratings = ref([])
const loading = ref(true)
const error = ref(null)
const syncing = ref(false)

const display = (score) => (score === null || score === undefined ? '—' : score)

const renderAnswer = (text) =>
  DOMPurify.sanitize(marked.parse(text || ''))

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await get('/inter-rater/history')
    ratings.value = data.ratings || []
    const returned = new Set(ratings.value.map((r) => r.span_id))

    // A 200 is not proof of completeness. Phoenix propagation lags submission,
    // and the store still holds the spans the server has not exposed yet, so
    // say the list is incomplete rather than letting it read as authoritative.
    syncing.value = [...store.recentlyRated].some((id) => !returned.has(id))

    // Only ratings the server actually returned may prune the local mask.
    store.pruneConfirmed([...returned])
  } catch (e) {
    console.error('Failed to load inter-rater history:', e)
    error.value = e.message || 'Please try again in a moment.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.history-overlay {
  position: fixed;
  inset: 0;
  z-index: 1500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.45);
}

.history-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.history-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.history-subtitle {
  font-size: 0.85rem;
  color: #6c757d;
}

.history-state {
  padding: 2.5rem 1.5rem;
  text-align: center;
  color: #495057;
}

.history-list {
  overflow-y: auto;
  padding: 0 1.5rem 1.5rem;
}

.history-entry {
  padding: 1.25rem 0;
  border-bottom: 1px solid #e9ecef;
}

.history-entry:last-child {
  border-bottom: none;
}

.history-question {
  font-size: 1rem;
  font-weight: 600;
  color: #111;
  margin-bottom: 0.5rem;
}

.history-answer {
  max-height: 12rem;
  overflow-y: auto;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 0.9rem;
}

.history-scores {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.history-scores th {
  width: 14rem;
  padding: 0.25rem 0.5rem 0.25rem 0;
  text-align: left;
  font-weight: 600;
  color: #495057;
}

.history-score {
  width: 3rem;
  font-variant-numeric: tabular-nums;
}

.history-rationale {
  color: #6c757d;
}

.history-faults,
.history-note {
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  margin: 0 auto;
  border: 3px solid #e9ecef;
  border-top-color: #363636;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.sync-notice {
  margin: 1rem 0;
  padding: 0.75rem 1rem;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  color: #363636;
  font-size: 0.875rem;
}

.error-notice {
  margin: 1.5rem;
  background-color: #f8f9fa;
  color: #363636;
  border: 1px solid #dee2e6;
}
</style>
