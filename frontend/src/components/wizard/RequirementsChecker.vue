<template>
  <div class="requirements-checker">
    <h2>System Requirements Check</h2>
    <p class="form-description">Checking if your system meets the requirements for building the corpus</p>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Checking system capabilities...</p>
    </div>

    <div v-else-if="systemInfo" class="requirements-content">
      <!-- System Overview -->
      <div class="system-overview">
        <div class="overview-card" :class="{ 'has-gpu': systemInfo.gpu?.available }">
          <h3>System Configuration</h3>
          <div class="system-grid">
            <div class="system-item">
              <span class="icon">💻</span>
              <div>
                <strong>CPU</strong>
                <p>{{ systemInfo.cpu?.cores }} cores / {{ systemInfo.cpu?.threads }} threads</p>
              </div>
            </div>
            <div class="system-item">
              <span class="icon">🎮</span>
              <div>
                <strong>GPU</strong>
                <p v-if="systemInfo.gpu?.available">
                  {{ systemInfo.gpu.name }} ({{ systemInfo.gpu.memory_gb?.toFixed(1) }} GB)
                </p>
                <p v-else class="not-available">Not available</p>
              </div>
            </div>
            <div class="system-item">
              <span class="icon">💾</span>
              <div>
                <strong>Memory</strong>
                <p>{{ systemInfo.memory?.available_gb?.toFixed(1) }} GB available</p>
                <p class="total">of {{ systemInfo.memory?.total_gb?.toFixed(1) }} GB total</p>
              </div>
            </div>
            <div class="system-item">
              <span class="icon">💿</span>
              <div>
                <strong>Disk Space</strong>
                <p>{{ systemInfo.disk?.free_gb?.toFixed(1) }} GB free</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Requirements Status -->
      <div class="requirements-status">
        <h3>Requirements Check</h3>
        <div class="status-list">
          <div class="status-item" :class="{ passed: systemInfo.memory?.sufficient }">
            <span class="status-icon">
              {{ systemInfo.memory?.sufficient ? '✅' : '❌' }}
            </span>
            <div class="status-content">
              <strong>Memory</strong>
              <p>
                Required: {{ systemInfo.memory?.required_gb?.toFixed(1) }} GB,
                Available: {{ systemInfo.memory?.available_gb?.toFixed(1) }} GB
              </p>
            </div>
          </div>

          <div class="status-item" :class="{ passed: systemInfo.disk?.sufficient }">
            <span class="status-icon">
              {{ systemInfo.disk?.sufficient ? '✅' : '❌' }}
            </span>
            <div class="status-content">
              <strong>Disk Space</strong>
              <p>
                Required: {{ systemInfo.disk?.required_gb?.toFixed(1) }} GB,
                Available: {{ systemInfo.disk?.free_gb?.toFixed(1) }} GB
              </p>
            </div>
          </div>

          <div class="status-item passed">
            <span class="status-icon">✅</span>
            <div class="status-content">
              <strong>CPU</strong>
              <p>{{ systemInfo.cpu?.cores }} cores available</p>
            </div>
          </div>

          <div class="status-item" :class="{ passed: true, optional: !systemInfo.gpu?.available }">
            <span class="status-icon">
              {{ systemInfo.gpu?.available ? '✅' : 'ℹ️' }}
            </span>
            <div class="status-content">
              <strong>GPU (Optional)</strong>
              <p v-if="systemInfo.gpu?.available">
                {{ systemInfo.gpu.name }} detected
              </p>
              <p v-else>Not detected - will use CPU mode</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Processing Mode Selection -->
      <div class="mode-selection">
        <h3>Select Processing Mode</h3>
        <div class="mode-options">
          <div
            class="mode-card"
            :class="{ active: localData.mode === 'cpu', recommended: !systemInfo.gpu?.available }"
            @click="selectMode('cpu')"
          >
            <div class="mode-header">
              <input
                type="radio"
                v-model="localData.mode"
                value="cpu"
                id="cpu-mode"
              />
              <label for="cpu-mode">CPU Mode</label>
              <span v-if="!systemInfo.gpu?.available" class="recommended-badge">Recommended</span>
            </div>
            <div class="mode-details">
              <p>Process using CPU only</p>
              <div class="time-estimate">
                <span class="icon">⏱️</span>
                <span>{{ formatTime(systemInfo.estimated_build_time?.cpu) }}</span>
              </div>
              <div class="speed-info">
                {{ systemInfo.estimated_build_time?.cpu?.docs_per_second?.toFixed(1) }} docs/sec
              </div>
            </div>
          </div>

          <div
            class="mode-card"
            :class="{
              active: localData.mode === 'gpu',
              recommended: systemInfo.gpu?.available,
              disabled: !systemInfo.gpu?.available
            }"
            @click="systemInfo.gpu?.available && selectMode('gpu')"
          >
            <div class="mode-header">
              <input
                type="radio"
                v-model="localData.mode"
                value="gpu"
                id="gpu-mode"
                :disabled="!systemInfo.gpu?.available"
              />
              <label for="gpu-mode">GPU Mode</label>
              <span v-if="systemInfo.gpu?.available" class="recommended-badge">Recommended</span>
            </div>
            <div class="mode-details">
              <p>Accelerated processing with GPU</p>
              <div v-if="systemInfo.gpu?.available">
                <div class="time-estimate">
                  <span class="icon">⚡</span>
                  <span>{{ formatTime(systemInfo.estimated_build_time?.gpu) }}</span>
                </div>
                <div class="speed-info">
                  {{ systemInfo.estimated_build_time?.gpu?.docs_per_second?.toFixed(1) }} docs/sec
                  <span class="speedup">
                    ({{ systemInfo.estimated_build_time?.gpu?.speedup?.toFixed(1) }}x faster)
                  </span>
                </div>
              </div>
              <p v-else class="not-available">GPU not detected</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Advanced Settings -->
      <div class="advanced-settings">
        <h3>Processing Configuration</h3>
        <div class="settings-grid">
          <div class="form-group">
            <label for="max-workers">Max Workers</label>
            <input
              id="max-workers"
              v-model.number="localData.max_workers"
              type="number"
              min="1"
              :max="systemInfo.cpu?.threads"
            />
            <small>Number of parallel workers (max: {{ systemInfo.cpu?.threads }})</small>
          </div>

          <div class="form-group">
            <label for="memory-limit">Memory Limit (GB)</label>
            <input
              id="memory-limit"
              v-model.number="localData.memory_limit_gb"
              type="number"
              min="1"
              :max="Math.floor(systemInfo.memory?.total_gb * 0.8)"
              :placeholder="`Max: ${Math.floor(systemInfo.memory?.total_gb * 0.8)}`"
            />
            <small>Leave empty for automatic allocation</small>
          </div>
        </div>
      </div>

      <!-- Inter-Rater Reliability Settings -->
      <div class="inter-rater-settings">
        <h3>Inter-Rater Reliability</h3>
        <p class="section-description">
          Enable inter-rater reliability studies to allow multiple users to rate the same responses for quality assessment.
        </p>

        <div class="toggle-group">
          <label class="toggle-label">
            <input
              type="checkbox"
              v-model="interRaterEnabled"
              class="toggle-input"
            />
            <span class="toggle-slider"></span>
            <span class="toggle-text">Enable Inter-Rater Feedback</span>
          </label>
        </div>

        <div v-if="interRaterEnabled" class="inter-rater-options">
          <div class="settings-grid">
            <div class="form-group">
              <label for="max-ratings">Maximum Ratings per Session</label>
              <input
                id="max-ratings"
                v-model.number="interRaterMaxRatings"
                type="number"
                min="1"
                max="10"
              />
              <small>How many different users can rate each session (1-10)</small>
            </div>

            <div class="form-group">
              <label for="sessions-per-user">Sessions per User</label>
              <input
                id="sessions-per-user"
                v-model.number="interRaterSessionsPerUser"
                type="number"
                min="1"
                max="50"
              />
              <small>How many sessions each user will be asked to rate (1-50)</small>
            </div>
          </div>

          <div class="inter-rater-note">
            <span class="note-icon">ℹ️</span>
            <span>Inter-rater reliability requires user authentication to ensure different users rate each session.</span>
          </div>
        </div>
      </div>

      <!-- Warnings -->
      <div v-if="systemInfo.warnings?.length > 0" class="warnings-section">
        <h3>⚠️ Warnings</h3>
        <div class="warning-list">
          <div v-for="(warning, index) in systemInfo.warnings" :key="index" class="warning-item">
            <strong>{{ warning.type }}:</strong> {{ warning.message }}
          </div>
        </div>
      </div>

      <!-- Final Summary -->
      <div class="build-summary">
        <h3>Build Summary</h3>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="label">Documents to Process:</span>
            <span class="value">{{ docCount.toLocaleString() }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Processing Mode:</span>
            <span class="value">{{ localData.mode.toUpperCase() }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Estimated Time:</span>
            <span class="value">{{ estimatedTimeFormatted }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Disk Space Required:</span>
            <span class="value">{{ systemInfo.disk?.required_gb?.toFixed(1) }} GB</span>
          </div>
        </div>
      </div>
    </div>

    <div class="form-actions">
      <button @click="$emit('back')" class="btn btn-secondary">Back</button>
      <button
        @click="handleNext"
        class="btn btn-primary"
        :disabled="!canProceed"
      >
        Start Build
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import axios from 'axios';

export default {
  name: 'RequirementsChecker',

  props: {
    docCount: {
      type: Number,
      required: true
    },
    modelValue: {
      type: Object,
      default: () => ({})
    }
  },

  emits: ['update:modelValue', 'next', 'back'],

  setup(props, { emit }) {
    const loading = ref(true);
    const systemInfo = ref(null);
    const localData = ref({
      mode: 'cpu',
      max_workers: 4,
      memory_limit_gb: null,
      ...props.modelValue
    });

    // Inter-rater settings (stored separately for cleaner UI binding)
    const interRaterEnabled = ref(props.modelValue?.interRater?.enabled || false);
    const interRaterMaxRatings = ref(props.modelValue?.interRater?.maxRatings || 3);
    const interRaterSessionsPerUser = ref(props.modelValue?.interRater?.sessionsPerUser || 5);

    const canProceed = computed(() => {
      if (!systemInfo.value) return false;
      // Check if minimum requirements are met
      return systemInfo.value.memory?.sufficient && systemInfo.value.disk?.sufficient;
    });

    const estimatedTimeFormatted = computed(() => {
      if (!systemInfo.value) return 'Calculating...';

      const buildTime = localData.value.mode === 'gpu'
        ? systemInfo.value.estimated_build_time?.gpu
        : systemInfo.value.estimated_build_time?.cpu;

      if (!buildTime) return 'Unknown';
      return buildTime.formatted || formatTime(buildTime);
    });

    const formatTime = (timeData) => {
      if (!timeData) return 'Unknown';

      if (typeof timeData === 'object' && timeData.formatted) {
        return timeData.formatted;
      }

      const seconds = timeData.seconds || timeData;
      if (seconds < 60) {
        return `${Math.round(seconds)} seconds`;
      } else if (seconds < 3600) {
        const minutes = Math.round(seconds / 60);
        return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
      } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.round((seconds % 3600) / 60);
        return `${hours} hour${hours !== 1 ? 's' : ''} ${minutes} min`;
      }
    };

    const selectMode = (mode) => {
      localData.value.mode = mode;
    };

    const checkRequirements = async () => {
      loading.value = true;
      try {
        const response = await axios.get('/api/corpus-wizard/system-requirements', {
          params: { doc_count: props.docCount }
        });
        systemInfo.value = response.data;

        // Set default mode based on recommendation
        if (response.data.recommended_mode) {
          localData.value.mode = response.data.recommended_mode;
        }

        // Set default workers based on CPU count
        if (response.data.cpu?.cores) {
          localData.value.max_workers = Math.min(4, response.data.cpu.cores);
        }
      } catch (error) {
        console.error('Failed to check requirements:', error);
        // Fallback to mock data
        systemInfo.value = {
          cpu: { cores: 4, threads: 8, available: true },
          gpu: { available: false },
          memory: {
            total_gb: 16,
            available_gb: 8,
            required_gb: 4,
            sufficient: true
          },
          disk: {
            free_gb: 100,
            required_gb: props.docCount * 0.005,
            sufficient: true
          },
          estimated_build_time: {
            cpu: {
              seconds: props.docCount / 1.2,
              formatted: formatTime(props.docCount / 1.2),
              docs_per_second: 1.2
            }
          },
          warnings: [],
          recommended_mode: 'cpu'
        };
      } finally {
        loading.value = false;
      }
    };

    const handleNext = () => {
      // Include inter-rater settings in the emitted data
      const dataToEmit = {
        ...localData.value,
        interRater: {
          enabled: interRaterEnabled.value,
          maxRatings: interRaterMaxRatings.value,
          sessionsPerUser: interRaterSessionsPerUser.value
        }
      };
      emit('update:modelValue', dataToEmit);
      emit('next');
    };

    onMounted(() => {
      checkRequirements();
    });

    // Watch for external changes
    watch(
      () => props.modelValue,
      (newValue) => {
        localData.value = { ...localData.value, ...newValue };
      },
      { deep: true }
    );

    // Emit changes
    watch(
      localData,
      (newValue) => {
        emit('update:modelValue', newValue);
      },
      { deep: true }
    );

    return {
      loading,
      systemInfo,
      localData,
      canProceed,
      estimatedTimeFormatted,
      formatTime,
      selectMode,
      handleNext,
      interRaterEnabled,
      interRaterMaxRatings,
      interRaterSessionsPerUser
    };
  }
};
</script>

<style scoped>
.requirements-checker {
  max-width: 900px;
  margin: 0 auto;
}

.requirements-checker h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.form-description {
  color: #666;
  margin-bottom: 2rem;
}

.loading-state {
  text-align: center;
  padding: 3rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.system-overview {
  margin-bottom: 2rem;
}

.overview-card {
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
}

.overview-card.has-gpu {
  border-color: #4caf50;
}

.overview-card h3 {
  margin-top: 0;
  color: #333;
}

.system-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-top: 1rem;
}

.system-item {
  display: flex;
  gap: 1rem;
}

.system-item .icon {
  font-size: 2rem;
}

.system-item strong {
  display: block;
  color: #333;
  margin-bottom: 0.25rem;
}

.system-item p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.system-item .total {
  font-size: 0.8rem;
  color: #999;
}

.not-available {
  color: #999;
  font-style: italic;
}

.requirements-status {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.requirements-status h3 {
  margin-top: 0;
  color: #333;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: white;
  border-radius: 4px;
  border-left: 4px solid #e0e0e0;
}

.status-item.passed {
  border-color: #4caf50;
}

.status-item.optional {
  border-color: #2196f3;
}

.status-icon {
  font-size: 1.5rem;
}

.status-content strong {
  display: block;
  color: #333;
  margin-bottom: 0.25rem;
}

.status-content p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.mode-selection {
  margin-bottom: 2rem;
}

.mode-selection h3 {
  color: #333;
  margin-bottom: 1rem;
}

.mode-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.mode-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.mode-card:hover:not(.disabled) {
  border-color: #3498db;
  background: #f8f9fa;
}

.mode-card.active {
  border-color: #3498db;
  background: #e3f2fd;
}

.mode-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-card.recommended {
  border-color: #4caf50;
}

.mode-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.mode-header label {
  font-weight: 600;
  color: #333;
}

.recommended-badge {
  background: #4caf50;
  color: white;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  margin-left: auto;
}

.mode-details p {
  margin: 0 0 0.5rem;
  color: #666;
  font-size: 0.9rem;
}

.time-estimate {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin: 0.5rem 0;
}

.speed-info {
  font-size: 0.9rem;
  color: #666;
}

.speedup {
  color: #4caf50;
  font-weight: 500;
}

.advanced-settings {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.advanced-settings h3 {
  margin-top: 0;
  color: #333;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.form-group small {
  margin-top: 0.25rem;
  color: #666;
  font-size: 0.875rem;
}

.warnings-section {
  background: #fff3e0;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  border: 1px solid #ffb74d;
}

.warnings-section h3 {
  margin-top: 0;
  color: #f57c00;
}

.warning-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.warning-item {
  color: #666;
}

.build-summary {
  background: white;
  border: 2px solid #3498db;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.build-summary h3 {
  margin-top: 0;
  color: #333;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.summary-item {
  display: flex;
  flex-direction: column;
}

.summary-item .label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.summary-item .value {
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
}

.form-actions {
  margin-top: 2rem;
  display: flex;
  justify-content: space-between;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

/* Inter-Rater Reliability Settings */
.inter-rater-settings {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  border: 1px solid #e0e0e0;
}

.inter-rater-settings h3 {
  margin-top: 0;
  color: #333;
}

.section-description {
  color: #666;
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}

.toggle-group {
  margin-bottom: 1.5rem;
}

.toggle-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 0.75rem;
}

.toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
  background-color: #ccc;
  border-radius: 26px;
  transition: 0.3s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: 0.3s;
}

.toggle-input:checked + .toggle-slider {
  background-color: #4caf50;
}

.toggle-input:checked + .toggle-slider::before {
  transform: translateX(24px);
}

.toggle-text {
  font-weight: 500;
  color: #333;
}

.inter-rater-options {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.inter-rater-note {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem;
  background: #e3f2fd;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #1565c0;
}

.note-icon {
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .mode-options {
    grid-template-columns: 1fr;
  }

  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>