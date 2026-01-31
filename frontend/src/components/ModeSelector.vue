<template>
  <div class="mode-selector">
    <div class="mode-container">
      <h1 class="mode-title">ATLAS System Mode</h1>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading system status...</p>
      </div>

      <!-- Already in Deploy Mode -->
      <div v-else-if="currentMode === 'deploy'" class="deploy-mode-active">
        <div class="alert alert-info">
          <div class="alert-icon">🚀</div>
          <div class="alert-content">
            <h3>System is in Deploy Mode</h3>
            <p>Configuration is locked to ensure consistent testing.</p>
            <p class="alert-note">Server restart required to modify configuration.</p>
          </div>
        </div>
        <button @click="continueToApp" class="btn btn-primary btn-lg">
          Continue to Application
        </button>
      </div>

      <!-- Mode Selection -->
      <div v-else class="mode-selection">
        <h2 class="selection-title">Select Operation Mode</h2>
        <p class="selection-subtitle">
          Choose how you want to use ATLAS in this session
        </p>

        <div class="mode-cards">
          <!-- Use Existing Configuration -->
          <div v-if="hasCompleteConfig" class="mode-card">
            <div class="card-icon">🚀</div>
            <h3>Deploy Mode</h3>
            <div class="card-content">
              <p class="card-description">
                Start testing with your configured system
              </p>
              <div class="config-summary">
                <div class="config-item">
                  <span class="config-label">Corpus:</span>
                  <span class="config-value">{{ corpusInfo?.name || 'Unknown' }}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Test Targets:</span>
                  <span class="config-value">{{ targetCount }} configured</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Default Target:</span>
                  <span class="config-value">{{ defaultTarget || 'Not set' }}</span>
                </div>
              </div>
              <button @click="confirmDeployMode" class="btn btn-primary">
                Enter Deploy Mode
              </button>
            </div>
          </div>

          <!-- Configuration Mode -->
          <div class="mode-card">
            <div class="card-icon">⚙️</div>
            <h3>Configuration Mode</h3>
            <div class="card-content">
              <p class="card-description">
                {{ hasCompleteConfig ? 'Modify your configuration' : 'Set up ATLAS for first use' }}
              </p>
              <ul class="config-options">
                <li v-if="!hasCorpus">Build new corpus from sources</li>
                <li v-else>Rebuild existing corpus</li>
                <li>Add or modify test targets</li>
                <li>Adjust retrieval settings</li>
              </ul>
              <button @click="enterConfigMode" class="btn btn-secondary">
                Enter Configuration Mode
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Deploy Mode Confirmation Modal -->
  <Teleport to="body">
    <div v-if="showDeployConfirm" class="modal-overlay" @click.self="showDeployConfirm = false">
      <div class="modal-content">
        <h2 class="modal-title">⚠️ Enter Deploy Mode?</h2>

        <div class="modal-body">
          <p>Once in Deploy mode:</p>
          <ul class="warning-list">
            <li>Configuration will be <strong>locked</strong></li>
            <li>No corpus rebuilding allowed</li>
            <li>No target modifications allowed</li>
            <li><strong>Server restart required</strong> to change configuration</li>
          </ul>

          <div class="alert alert-warning">
            <strong>Important:</strong> This is a one-way operation for this session.
            Make sure your configuration is complete before proceeding.
          </div>
        </div>

        <div class="modal-footer">
          <button @click="showDeployConfirm = false" class="btn btn-outline">
            Cancel
          </button>
          <button @click="enterDeployMode" class="btn btn-primary">
            Yes, Enter Deploy Mode
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'ModeSelector',
  setup() {
    const router = useRouter()

    // State
    const currentMode = ref(null)
    const hasCompleteConfig = ref(false)
    const hasCorpus = ref(false)
    const corpusInfo = ref(null)
    const targetCount = ref(0)
    const defaultTarget = ref(null)
    const showDeployConfirm = ref(false)
    const loading = ref(true)

    // Fetch current mode status
    const fetchModeStatus = async () => {
      try {
        const response = await fetch('/api/mode/status')
        const data = await response.json()

        currentMode.value = data.mode
        hasCompleteConfig.value = data.config_complete
        hasCorpus.value = data.has_corpus
        corpusInfo.value = data.corpus_info
        targetCount.value = data.target_count
        defaultTarget.value = data.default_target

        loading.value = false
      } catch (error) {
        console.error('Failed to fetch mode status:', error)
        alert('Failed to load system status. Please refresh the page.')
        loading.value = false
      }
    }

    // Mode actions
    const continueToApp = () => {
      router.push('/chat')
    }

    const confirmDeployMode = () => {
      showDeployConfirm.value = true
    }

    const enterDeployMode = async () => {
      try {
        const response = await fetch('/api/mode/deploy', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to enter deploy mode')
        }

        const data = await response.json()
        console.log('Entered Deploy Mode:', data)
        showDeployConfirm.value = false
        router.push('/chat')
      } catch (error) {
        console.error('Failed to enter deploy mode:', error)
        alert(error.message)
      }
    }

    const enterConfigMode = async () => {
      try {
        const response = await fetch('/api/mode/configure', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to enter configuration mode')
        }

        // Redirect to appropriate configuration page
        if (!hasCorpus.value) {
          router.push('/corpus-wizard')
        } else {
          router.push('/config-manager')
        }
      } catch (error) {
        console.error('Failed to enter configuration mode:', error)
        alert(error.message)
      }
    }

    // Lifecycle
    onMounted(() => {
      fetchModeStatus()
    })

    return {
      currentMode,
      hasCompleteConfig,
      hasCorpus,
      corpusInfo,
      targetCount,
      defaultTarget,
      showDeployConfirm,
      loading,
      continueToApp,
      confirmDeployMode,
      enterDeployMode,
      enterConfigMode
    }
  }
}
</script>

<style scoped>
/* Mode selector container */
.mode-selector {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.mode-container {
  width: 100%;
  max-width: 900px;
  background: white;
  border-radius: 12px;
  padding: 3rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

/* Loading state */
.loading-state {
  text-align: center;
  padding: 3rem;
}

.spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Typography */
.mode-title {
  font-size: 2.5rem;
  font-weight: 800;
  text-align: center;
  margin-bottom: 2rem;
  color: #1a202c;
}

.selection-title {
  font-size: 1.75rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 0.5rem;
  color: #2d3748;
}

.selection-subtitle {
  text-align: center;
  color: #718096;
  margin-bottom: 2rem;
}

/* Mode cards */
.mode-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.mode-card {
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  padding: 2rem;
  transition: all 0.3s ease;
}

.mode-card:hover {
  border-color: #cbd5e0;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.card-icon {
  font-size: 3rem;
  text-align: center;
  margin-bottom: 1rem;
}

.card-content h3 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #2d3748;
  text-align: center;
}

.card-description {
  color: #4a5568;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

/* Config summary */
.config-summary {
  background: #f7fafc;
  border-radius: 6px;
  padding: 1rem;
  margin: 1rem 0;
}

.config-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e2e8f0;
}

.config-item:last-child {
  border-bottom: none;
}

.config-label {
  font-weight: 600;
  color: #4a5568;
}

.config-value {
  color: #2d3748;
}

/* Config options list */
.config-options {
  list-style: none;
  padding: 0;
  margin: 1rem 0 1.5rem;
}

.config-options li {
  padding: 0.5rem 0;
  padding-left: 1.5rem;
  position: relative;
  color: #4a5568;
}

.config-options li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #48bb78;
  font-weight: bold;
}

/* Deploy mode active */
.deploy-mode-active {
  text-align: center;
}

/* Alerts */
.alert {
  border-radius: 8px;
  padding: 1.5rem;
  margin: 2rem 0;
}

.alert-info {
  background: #ebf8ff;
  border: 1px solid #90cdf4;
}

.alert-warning {
  background: #fffaf0;
  border: 1px solid #feb2b2;
}

.alert-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.alert-content h3 {
  color: #2b6cb6;
  margin-bottom: 0.5rem;
}

.alert-content p {
  color: #2c5282;
  margin: 0.5rem 0;
}

.alert-note {
  font-style: italic;
  font-size: 0.9rem;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #2d3748;
}

.modal-body {
  margin: 1.5rem 0;
}

.warning-list {
  list-style: disc;
  padding-left: 1.5rem;
  margin: 1rem 0;
  color: #4a5568;
}

.warning-list li {
  margin: 0.5rem 0;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

/* Buttons */
.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  display: inline-block;
  text-align: center;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5a67d8;
}

.btn-secondary {
  background: #48bb78;
  color: white;
}

.btn-secondary:hover {
  background: #38a169;
}

.btn-outline {
  background: white;
  color: #4a5568;
  border: 2px solid #e2e8f0;
}

.btn-outline:hover {
  background: #f7fafc;
}

.btn-lg {
  padding: 1rem 2rem;
  font-size: 1.125rem;
}
</style>