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
    <span v-else class="loading-text">Loading inter-rating tasks...</span>
  </div>
</template>

<script>
import { computed, onMounted } from 'vue'
import { useInterRaterStore } from '../stores/interRater'

export default {
  name: 'InterRaterButton',
  setup() {
    const store = useInterRaterStore()

    const isEnabled = computed(() => store.isEnabled)
    // Server stats are computed per worker: invalidate_user_cache and
    // record_user_rating only reach the worker that took the submission, so a
    // refresh landing elsewhere can still count a span the reviewer just
    // rated. While the task has validated run state, the client's allocation is
    // already filtered and is the more accurate number. No subtraction here —
    // allocation is filtered at source, so it cannot double-count after the
    // history read prunes the local mask.
    const availableSessions = computed(() =>
      store.validated ? store.allocation.length : store.availableSessions
    )
    const isLoading = computed(() => !store.loaded)

    onMounted(() => {
      store.fetchConfig()

      setInterval(() => store.refresh(), 300000) // Every 5 minutes

      window.addEventListener('inter-rater-completed', () => {
        store.refresh()
      })
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
  background-color: #000;
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