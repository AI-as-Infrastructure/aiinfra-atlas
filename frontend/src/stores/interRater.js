import { defineStore } from 'pinia'
import { ref } from 'vue'
import { get } from '../utils/api'

export const useInterRaterStore = defineStore('interRater', () => {
  const isEnabled = ref(false)
  const defaultUi = ref(false)
  const availableSessions = ref(0)
  const loaded = ref(false)

  let _fetchPromise = null

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

  return { isEnabled, defaultUi, availableSessions, loaded, fetchConfig, refresh }
})
