import { defineStore } from 'pinia'
import { ref } from 'vue'
import { get } from '../utils/api'

// Persisted run state has two scopes with two lifetimes:
//
//   position      belongs to one allocation snapshot. A reseed invalidates it.
//   recentlyRated belongs to the reviewer. "I already rated this" stays true
//                 across any pool change, and it masks a real server race:
//                 check_user_already_rated consults a process-local set while
//                 production runs 8-16 gunicorn workers, so a worker that did
//                 not receive the submission waits on Phoenix propagation.
//
// Conflating them is what made a capacity refusal look like the reviewer's own
// rating, so they are stored under separate keys.
const POSITION_KEY = 'atlas:ir:position'
const RATED_KEY = 'atlas:ir:rated'

// Non-reversible marker so a second reviewer on the same browser cannot pick up
// the first one's state. Never store the email itself — users must not be
// identifiable in stored data.
function reviewerKey(identity) {
  if (!identity) return 'anon'
  let hash = 2166136261
  for (let i = 0; i < identity.length; i++) {
    hash ^= identity.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(36)
}

function readJson(key) {
  const raw = sessionStorage.getItem(key)
  return raw ? JSON.parse(raw) : null
}

export const useInterRaterStore = defineStore('interRater', () => {
  // --- config ---
  const isEnabled = ref(false)
  const defaultUi = ref(false)
  const availableSessions = ref(0)
  const loaded = ref(false)

  // --- run state ---
  const allocation = ref([])
  const currentIndex = ref(0)
  const completedCount = ref(0)
  const targetSessions = ref(0)
  const snapshotId = ref(null)
  const recentlyRated = ref(new Set())
  const unavailable = ref(new Set())
  // True once a server response has validated whatever we restored. Nothing
  // persisted may be rendered before this.
  const validated = ref(false)
  const storageAvailable = ref(true)

  let _fetchPromise = null
  let _key = 'anon'

  // Auth initialises asynchronously, so the first call usually arrives with a
  // null identity. Callers must keep calling as the identity resolves — until
  // it does, state lives under the shared "anon" key, and a second reviewer on
  // the same browser must not inherit it.
  function setReviewer(identity) {
    const next = reviewerKey(identity)
    if (next !== _key) {
      _key = next
      restore()
    }
  }

  function reviewerResolved() {
    return _key !== 'anon'
  }

  // --- persistence -------------------------------------------------------

  function restore() {
    try {
      const rated = readJson(`${RATED_KEY}:${_key}`)
      recentlyRated.value = new Set(Array.isArray(rated) ? rated : [])

      // Always reset position fields, so switching reviewers cannot leave the
      // previous one's snapshot, index or unavailable set in place.
      const position = readJson(`${POSITION_KEY}:${_key}`)
      snapshotId.value = position?.snapshotId ?? null
      currentIndex.value = position?.currentIndex ?? 0
      unavailable.value = new Set(position?.unavailable || [])
      storageAvailable.value = true
    } catch (e) {
      // Private windows and blocked site data throw on access. Say so rather
      // than presenting an empty history as authoritative.
      console.error('Inter-rater state storage unavailable:', e)
      storageAvailable.value = false
      recentlyRated.value = new Set()
      unavailable.value = new Set()
      snapshotId.value = null
      currentIndex.value = 0
    }
  }

  function persist() {
    if (!storageAvailable.value) return
    try {
      sessionStorage.setItem(
        `${RATED_KEY}:${_key}`,
        JSON.stringify([...recentlyRated.value])
      )
      sessionStorage.setItem(
        `${POSITION_KEY}:${_key}`,
        JSON.stringify({
          snapshotId: snapshotId.value,
          currentIndex: currentIndex.value,
          unavailable: [...unavailable.value],
        })
      )
    } catch (e) {
      console.error('Could not persist inter-rater state:', e)
      storageAvailable.value = false
    }
  }

  // --- run state transitions --------------------------------------------

  /**
   * Adopt a server allocation. Saved position is honoured only when the
   * server's snapshot matches; the rated set is applied either way.
   */
  function applyAllocation({ sessions, snapshot, completed, target }) {
    const sameSnapshot = snapshot && snapshot === snapshotId.value

    if (!sameSnapshot) {
      // Pool changed: position and unavailability belonged to the old one.
      currentIndex.value = 0
      unavailable.value = new Set()
      snapshotId.value = snapshot ?? null
    }

    allocation.value = (sessions || []).filter(
      (s) => !recentlyRated.value.has(s.span_id) && !unavailable.value.has(s.span_id)
    )
    completedCount.value = completed ?? completedCount.value
    targetSessions.value = target ?? targetSessions.value

    if (currentIndex.value >= allocation.value.length) currentIndex.value = 0
    validated.value = true
    persist()
  }

  /** A rating this reviewer actually made. Survives a snapshot change. */
  function markRated(spanId) {
    recentlyRated.value = new Set(recentlyRated.value).add(spanId)
    allocation.value = allocation.value.filter((s) => s.span_id !== spanId)
    completedCount.value += 1
    if (currentIndex.value >= allocation.value.length) currentIndex.value = 0
    persist()
  }

  /** Refused for capacity or pool membership — not a rating by this reviewer. */
  function markUnavailable(spanId) {
    unavailable.value = new Set(unavailable.value).add(spanId)
    allocation.value = allocation.value.filter((s) => s.span_id !== spanId)
    if (currentIndex.value >= allocation.value.length) currentIndex.value = 0
    persist()
  }

  /**
   * Drop local entries the server can now see for itself. Only an authoritative
   * history response may prune — never a size cap or timeout, which could lift
   * the mask before Phoenix propagation completes.
   */
  function pruneConfirmed(confirmedSpanIds) {
    const confirmed = new Set(confirmedSpanIds || [])
    if (!confirmed.size) return
    const next = new Set([...recentlyRated.value].filter((id) => !confirmed.has(id)))
    recentlyRated.value = next
    persist()
  }

  function resetRun() {
    allocation.value = []
    currentIndex.value = 0
    validated.value = false
  }

  // --- config fetch ------------------------------------------------------

  async function fetchConfig() {
    if (_fetchPromise) return _fetchPromise
    _fetchPromise = _doFetch()
    return _fetchPromise
  }

  async function _doFetch() {
    try {
      const data = await get('/inter-rater/stats')
      isEnabled.value = data.enabled || false
      defaultUi.value = data.default_ui || false
      availableSessions.value = data.available_sessions || 0
    } catch (e) {
      console.error('Failed to fetch inter-rater config:', e)
    } finally {
      loaded.value = true
    }
  }

  async function refresh() {
    _fetchPromise = null
    await fetchConfig()
  }

  restore()

  return {
    isEnabled,
    defaultUi,
    availableSessions,
    loaded,
    allocation,
    currentIndex,
    completedCount,
    targetSessions,
    snapshotId,
    recentlyRated,
    unavailable,
    validated,
    storageAvailable,
    setReviewer,
    reviewerResolved,
    applyAllocation,
    markRated,
    markUnavailable,
    pruneConfirmed,
    resetRun,
    fetchConfig,
    refresh,
  }
})
