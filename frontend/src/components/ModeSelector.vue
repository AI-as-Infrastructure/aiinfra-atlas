<template>
  <div class="mode-selector">
    <div class="mode-container">
      <h1 class="mode-title">ATLAS System Mode</h1>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <p>Loading system status...</p>
      </div>

      <!-- Already in Deploy Mode -->
      <div v-else-if="currentMode === 'deploy'" class="deploy-mode-active">
        <div class="alert alert-info">
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
              <button @click="enterConfigMode" class="btn btn-primary">
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
      <div class="modal-dialog">
        <h2 class="modal-title">Enter Deploy Mode?</h2>

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
      window.location.href = '/chat'
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
        // Full page reload to ensure all components re-fetch from backend
        setTimeout(() => {
          window.location.href = '/chat'
        }, 2000)
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
.mode-selector {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 2rem;
  font-family: "Times New Roman", Times, serif;
  color: #000;
}

.mode-container {
  width: 100%;
  max-width: 900px;
  background: #fff;
  padding: 3rem;
}

.loading-state {
  text-align: center;
  padding: 3rem;
}

.mode-title {
  font-size: 2rem;
  font-weight: bold;
  text-align: center;
  margin-bottom: 2rem;
  color: #000;
}

.selection-title {
  font-size: 1.5rem;
  font-weight: bold;
  text-align: center;
  margin-bottom: 0.5rem;
  color: #000;
}

.selection-subtitle {
  text-align: center;
  color: #555;
  margin-bottom: 2rem;
}

.mode-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.mode-card {
  border: 1px solid #eee;
  padding: 2rem;
}

.mode-card:hover {
  border-color: #ccc;
}

.mode-card h3 {
  font-size: 1.25rem;
  font-weight: bold;
  margin-bottom: 1rem;
  color: #000;
  text-align: center;
}

.card-description {
  color: #333;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.config-summary {
  background: #fafafa;
  padding: 1rem;
  margin: 1rem 0;
  border: 1px solid #eee;
}

.config-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}

.config-item:last-child {
  border-bottom: none;
}

.config-label {
  font-weight: bold;
  color: #000;
}

.config-value {
  color: #333;
}

.config-options {
  list-style: disc;
  padding-left: 1.5rem;
  margin: 1rem 0 1.5rem;
}

.config-options li {
  padding: 0.25rem 0;
  color: #333;
}

.deploy-mode-active {
  text-align: center;
}

.alert {
  padding: 1.5rem;
  margin: 2rem 0;
  border: 1px solid #eee;
}

.alert-info {
  background: #fff;
  border-color: #ccc;
}

.alert-warning {
  background: #fff;
  border-color: #ccc;
  font-size: 0.95rem;
}

.alert-content h3 {
  color: #000;
  margin-bottom: 0.5rem;
}

.alert-content p {
  color: #333;
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
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-dialog {
  background: #fff;
  border: 1px solid #eee;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: bold;
  margin-bottom: 1rem;
  color: #000;
}

.modal-body {
  margin: 1.5rem 0;
}

.warning-list {
  list-style: disc;
  padding-left: 1.5rem;
  margin: 1rem 0;
  color: #333;
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

/* Buttons - match main app theme */
.btn {
  padding: 0.5rem 1.25rem;
  font-weight: 500;
  font-size: 1rem;
  cursor: pointer;
  border: none;
  display: inline-block;
  text-align: center;
  font-family: "Times New Roman", Times, serif;
}

.btn-primary {
  background: #000;
  color: #fff;
}

.btn-primary:hover {
  background: #888;
  color: #fff;
}

.btn-outline {
  background: #fff;
  color: #000;
  border: 1px solid #ccc;
}

.btn-outline:hover {
  background: #f5f5f5;
}

.btn-lg {
  padding: 0.75rem 1.75rem;
  font-size: 1.1rem;
}
</style>
