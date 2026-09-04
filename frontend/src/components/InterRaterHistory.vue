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
        <article v-for="(entry, index) in ratings" :key="entry.span_id" class="history-entry">
          <p class="history-index">{{ index + 1 }} of {{ ratings.length }}</p>
          <h4 class="history-question">{{ entry.question }}</h4>

          <!-- The material being rated: recessive, scrollable, clearly quoted. -->
          <section class="history-source">
            <p class="history-label">Answer you rated</p>
            <div class="history-answer content" v-html="renderAnswer(entry.answer)"></div>
          </section>

          <!-- The reviewer's own judgement: the thing they came to compare. -->
          <section class="history-rating">
            <p class="history-label">Your rating</p>
            <table class="history-scores">
              <tbody>
                <tr v-for="criterion in CRITERIA" :key="criterion.key">
                  <th>{{ criterion.label }}</th>
                  <td class="history-score">
                    <span
                      v-for="n in 5"
                      :key="n"
                      class="score-pip"
                      :class="{ filled: entry.scores[criterion.key] >= n }"
                    ></span>
                    <span class="score-value">{{ display(entry.scores[criterion.key]) }}</span>
                  </td>
                  <td class="history-rationale">{{ entry.rationales[criterion.key] || '—' }}</td>
                </tr>
              </tbody>
            </table>

            <p class="history-faults">
              <span class="history-faults-label">Faults</span>
              <span v-if="entry.faults.length" class="history-fault-tags">
                <span v-for="fault in entry.faults" :key="fault" class="fault-tag">{{ fault }}</span>
              </span>
              <span v-else class="history-none">none recorded</span>
            </p>
            <p v-if="entry.faults_rationale" class="history-note">
              <span class="history-faults-label">Fault rationale</span> {{ entry.faults_rationale }}
            </p>
            <p v-if="entry.additional_comments" class="history-note">
              <span class="history-faults-label">Additional comments</span> {{ entry.additional_comments }}
            </p>
          </section>
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
    const currentPool = Array.isArray(data.pool_span_ids)
      ? new Set(data.pool_span_ids)
      : null

    // A 200 is not proof of completeness. Phoenix propagation lags submission,
    // and the store still holds the spans the server has not exposed yet, so
    // say the list is incomplete rather than letting it read as authoritative.
    syncing.value = [...store.recentlyRated].some(
      (id) => (!currentPool || currentPool.has(id)) && !returned.has(id)
    )

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
  padding: 1.5rem 0 1.75rem;
  border-bottom: 1px solid #e9ecef;
}

.history-entry:last-child {
  border-bottom: none;
}

.history-index {
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #adb5bd;
  margin-bottom: 0.35rem;
}

.history-question {
  font-size: 1rem;
  font-weight: 600;
  color: #111;
  margin-bottom: 0.9rem;
}

/* Small caps label so the two halves of an entry announce themselves without
   adding colour to a deliberately monochrome palette. */
.history-label {
  font-size: 0.68rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: #adb5bd;
  margin-bottom: 0.4rem;
}

/* The rated material: recessive, quoted, and obviously not the reviewer's. */
.history-source {
  padding-left: 0.85rem;
  border-left: 2px solid #dee2e6;
  margin-bottom: 1.1rem;
}

.history-answer {
  max-height: 11rem;
  overflow-y: auto;
  padding: 0.7rem 0.85rem;
  background: #f8f9fa;
  border-radius: 3px;
  font-size: 0.86rem;
  color: #495057;
}

/* The reviewer's own judgement: foreground, on white, framed. */
.history-rating {
  padding: 0.9rem 1rem 0.75rem;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  background: #fff;
}

.history-scores {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.history-scores tr + tr th,
.history-scores tr + tr td {
  border-top: 1px solid #f1f3f5;
}

.history-scores th {
  width: 13rem;
  padding: 0.4rem 0.5rem 0.4rem 0;
  text-align: left;
  font-weight: 500;
  color: #495057;
}

.history-score {
  width: 6.5rem;
  white-space: nowrap;
  padding: 0.4rem 0.75rem 0.4rem 0;
}

/* Five pips make a run of scores scannable down the column, which is the
   whole point of looking back at your own ratings. */
.score-pip {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 3px;
  border-radius: 50%;
  border: 1px solid #ced4da;
  vertical-align: middle;
}

.score-pip.filled {
  background: #363636;
  border-color: #363636;
}

.score-value {
  margin-left: 0.4rem;
  font-variant-numeric: tabular-nums;
  color: #363636;
  font-weight: 600;
}

.history-rationale {
  color: #6c757d;
  padding: 0.4rem 0;
}

.history-faults,
.history-note {
  margin-top: 0.7rem;
  padding-top: 0.7rem;
  border-top: 1px solid #f1f3f5;
  font-size: 0.85rem;
  color: #495057;
}

.history-faults-label {
  display: inline-block;
  min-width: 9.5rem;
  font-size: 0.68rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: #adb5bd;
}

.fault-tag {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  margin-right: 0.35rem;
  border: 1px solid #ced4da;
  border-radius: 3px;
  font-size: 0.78rem;
  color: #363636;
}

.history-none {
  color: #adb5bd;
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
