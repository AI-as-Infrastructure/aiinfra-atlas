<template>
  <div class="build-progress">
    <h3>Building Vector Store</h3>

    <!-- Overall Progress -->
    <div class="progress-section">
      <div class="progress-header">
        <span>Overall Progress</span>
        <span class="progress-percentage">{{ progressPercentage }}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
      </div>
      <div class="progress-stats">
        <span>{{ progress.processed_documents || 0 }} / {{ progress.total_documents || 0 }} documents</span>
        <span v-if="progress.docs_per_second">
          {{ progress.docs_per_second.toFixed(1) }} docs/sec
        </span>
      </div>
    </div>

    <!-- Current Activity -->
    <div v-if="progress.current_document" class="current-activity">
      <h4>Current Document</h4>
      <div class="document-info">
        <code>{{ progress.current_document }}</code>
        <span v-if="progress.current_chunk > 0">
          Chunk {{ progress.current_chunk }}
        </span>
      </div>
    </div>

    <!-- Performance Metrics -->
    <div class="metrics-grid">
      <div class="metric">
        <div class="metric-label">Time Elapsed</div>
        <div class="metric-value">{{ formatDuration(progress.elapsed_seconds) }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Est. Remaining</div>
        <div class="metric-value">{{ formatDuration(progress.estimated_remaining_seconds) }}</div>
      </div>
      <div v-if="progress.memory" class="metric">
        <div class="metric-label">RAM Usage</div>
        <div class="metric-value">
          {{ Math.round(progress.memory.ram_used_gb) }}GB
          <span class="metric-percent">({{ Math.round(progress.memory.ram_percent) }}%)</span>
        </div>
      </div>
      <div v-if="progress.memory && progress.memory.gpu_allocated_gb" class="metric">
        <div class="metric-label">GPU Usage</div>
        <div class="metric-value">
          {{ progress.memory.gpu_allocated_gb.toFixed(1) }}GB
          <span class="metric-percent">({{ Math.round(progress.memory.gpu_percent) }}%)</span>
        </div>
      </div>
      <div v-if="progress.performance" class="metric">
        <div class="metric-label">CPU Usage</div>
        <div class="metric-value">{{ Math.round(progress.performance.cpu_percent) }}%</div>
      </div>
    </div>

    <!-- Filter Progress -->
    <div v-if="progress.filter_progress && Object.keys(progress.filter_progress).length > 0" class="filter-progress">
      <h4>Progress by Filter</h4>
      <div v-for="(filterData, filterId) in progress.filter_progress" :key="filterId" class="filter-item">
        <div class="filter-name">{{ filterId }}</div>
        <div class="filter-stats">
          {{ filterData.processed }} / {{ filterData.total }} documents
        </div>
        <div class="progress-bar mini">
          <div
            class="progress-fill"
            :style="{ width: (filterData.processed / filterData.total * 100) + '%' }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Logs -->
    <div v-if="showLogs" class="logs-section">
      <h4>Build Logs</h4>
      <div class="logs-container">
        <div v-for="(log, index) in logs" :key="index" class="log-entry" :class="log.level">
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <!-- Warnings/Errors -->
    <div v-if="progress.warnings && progress.warnings > 0" class="warnings">
      <div class="warning-badge">⚠️ {{ progress.warnings }} warnings</div>
    </div>
    <div v-if="progress.errors && progress.errors > 0" class="errors">
      <div class="error-badge">❌ {{ progress.errors }} errors</div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <button
        v-if="!isPaused && progress.status === 'building'"
        @click="$emit('pause')"
        class="btn btn-secondary"
      >
        ⏸ Pause
      </button>
      <button
        v-if="isPaused"
        @click="$emit('resume')"
        class="btn btn-primary"
      >
        ▶ Resume
      </button>
      <button @click="showLogs = !showLogs" class="btn btn-secondary">
        {{ showLogs ? 'Hide' : 'Show' }} Logs
      </button>
      <button
        v-if="progress.status === 'building'"
        @click="$emit('cancel')"
        class="btn btn-danger"
      >
        Cancel
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'BuildProgress',
  props: {
    progress: {
      type: Object,
      default: () => ({})
    },
    logs: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const showLogs = ref(false)

    const progressPercentage = computed(() => {
      return Math.round(props.progress.percentage || 0)
    })

    const isPaused = computed(() => {
      return props.progress.status === 'paused'
    })

    const formatDuration = (seconds) => {
      if (!seconds) return '—'
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      const secs = Math.floor(seconds % 60)

      if (hours > 0) {
        return `${hours}h ${minutes}m`
      } else if (minutes > 0) {
        return `${minutes}m ${secs}s`
      } else {
        return `${secs}s`
      }
    }

    const formatTime = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleTimeString()
    }

    return {
      showLogs,
      progressPercentage,
      isPaused,
      formatDuration,
      formatTime
    }
  }
}
</script>

<style scoped>
.build-progress {
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
}

.progress-section {
  margin-bottom: 2rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.progress-percentage {
  color: #007bff;
  font-weight: bold;
}

.progress-bar {
  height: 24px;
  background: #e9ecef;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007bff, #0056b3);
  transition: width 0.3s ease;
}

.progress-bar.mini {
  height: 8px;
  margin-top: 0.25rem;
}

.progress-stats {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: #6c757d;
}

.current-activity {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.current-activity h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  text-transform: uppercase;
  color: #6c757d;
}

.document-info {
  font-family: monospace;
  font-size: 0.9rem;
  word-break: break-all;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.metric {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
}

.metric-label {
  font-size: 0.8rem;
  color: #6c757d;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: bold;
  color: #212529;
}

.metric-percent {
  font-size: 0.9rem;
  color: #6c757d;
  font-weight: normal;
}

.filter-progress {
  margin-bottom: 1.5rem;
}

.filter-progress h4 {
  margin-bottom: 1rem;
}

.filter-item {
  margin-bottom: 1rem;
}

.filter-name {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.filter-stats {
  font-size: 0.9rem;
  color: #6c757d;
  margin-bottom: 0.25rem;
}

.logs-section {
  margin-bottom: 1.5rem;
}

.logs-container {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 1rem;
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 0.85rem;
}

.log-entry {
  margin-bottom: 0.25rem;
}

.log-time {
  color: #808080;
  margin-right: 1rem;
}

.log-entry.error {
  color: #f48771;
}

.log-entry.warning {
  color: #dcdcaa;
}

.warnings, .errors {
  margin-bottom: 1rem;
}

.warning-badge, .error-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.warning-badge {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffc107;
}

.error-badge {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #dc3545;
}

.controls {
  display: flex;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #dee2e6;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #545b62;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}
</style>