<template>
  <div class="config-manager">
    <div class="config-header">
      <h1>Configuration Manager</h1>
      <div class="mode-badge">
        <span class="badge badge-config">Configuration Mode</span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading configuration...</p>
    </div>

    <div v-else class="config-content">
      <!-- Current Corpus -->
      <div class="config-section">
        <h2>Active Corpus</h2>
        <div v-if="corpusInfo" class="corpus-info">
          <div class="info-grid">
            <div class="info-item">
              <label>Name:</label>
              <span>{{ corpusInfo.name }}</span>
            </div>
            <div class="info-item">
              <label>Collection:</label>
              <span>{{ corpusInfo.collection_name }}</span>
            </div>
            <div class="info-item">
              <label>Embedding Model:</label>
              <span>{{ corpusInfo.embedding_model }}</span>
            </div>
            <div class="info-item">
              <label>Documents:</label>
              <span>{{ corpusInfo.document_count || 'Unknown' }}</span>
            </div>
            <div class="info-item">
              <label>Chunk Size:</label>
              <span>{{ corpusInfo.chunk_size }}</span>
            </div>
            <div class="info-item">
              <label>Chunk Overlap:</label>
              <span>{{ corpusInfo.chunk_overlap }}</span>
            </div>
          </div>
          <div class="corpus-actions">
            <button @click="rebuildCorpus" class="btn btn-warning">
              🔄 Rebuild Corpus
            </button>
          </div>
        </div>
        <div v-else class="no-corpus">
          <p>No corpus found.</p>
          <button @click="buildNewCorpus" class="btn btn-primary">
            Build New Corpus
          </button>
        </div>
      </div>

      <!-- Test Targets -->
      <div class="config-section">
        <div class="section-header">
          <h2>Test Targets</h2>
          <button @click="showAddTarget = true" class="btn btn-primary btn-sm">
            + Add Target
          </button>
        </div>

        <div v-if="targets.length > 0" class="targets-list">
          <div v-for="target in targets" :key="target.id" class="target-card">
            <div class="target-header">
              <h3>{{ target.id }}</h3>
              <span v-if="target.id === defaultTarget" class="badge badge-default">Default</span>
            </div>
            <div class="target-details">
              <div class="detail-row">
                <span class="detail-label">Provider:</span>
                <span class="detail-value">{{ target.llm_provider }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Model:</span>
                <span class="detail-value">{{ target.llm_model }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Search K:</span>
                <span class="detail-value">{{ target.search_k }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Algorithm:</span>
                <span class="detail-value">{{ target.algorithm || 'ensemble' }}</span>
              </div>
            </div>
            <div class="target-actions">
              <button
                v-if="target.id !== defaultTarget"
                @click="setDefaultTarget(target.id)"
                class="btn btn-sm btn-outline"
              >
                Set Default
              </button>
              <button @click="editTarget(target)" class="btn btn-sm btn-outline">
                Edit
              </button>
              <button @click="confirmDeleteTarget(target)" class="btn btn-sm btn-danger">
                Delete
              </button>
            </div>
          </div>
        </div>
        <div v-else class="no-targets">
          <p>No test targets configured.</p>
          <button @click="showAddTarget = true" class="btn btn-primary">
            Configure First Target
          </button>
        </div>
      </div>

      <!-- Actions -->
      <div class="config-actions">
        <button @click="confirmDeployMode" class="btn btn-success btn-lg">
          ✅ Configuration Complete - Enter Deploy Mode
        </button>
        <p class="action-note">
          Once in Deploy Mode, configuration will be locked until server restart.
        </p>
      </div>
    </div>

    <!-- Add/Edit Target Modal -->
    <Teleport to="body">
      <div v-if="showAddTarget || editingTarget" class="modal-overlay" @click.self="closeTargetModal">
        <div class="modal-content modal-lg">
          <h2 class="modal-title">{{ editingTarget ? 'Edit' : 'Add' }} Test Target</h2>

          <div class="modal-body">
            <div class="form-group">
              <label>Target Name *</label>
              <input
                v-model="targetForm.id"
                type="text"
                placeholder="e.g., k20_claude4"
                :disabled="editingTarget"
                class="form-control"
              />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>LLM Provider *</label>
                <select v-model="targetForm.llm_provider" class="form-control">
                  <option value="anthropic">Anthropic (Claude)</option>
                  <option value="openai">OpenAI (GPT)</option>
                  <option value="google">Google (Gemini)</option>
                  <option value="bedrock">AWS Bedrock</option>
                  <option value="ollama">Ollama (Local)</option>
                </select>
              </div>

              <div class="form-group">
                <label>Model *</label>
                <input
                  v-model="targetForm.llm_model"
                  type="text"
                  placeholder="e.g., claude-3-haiku"
                  class="form-control"
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Search K *</label>
                <input
                  v-model.number="targetForm.search_k"
                  type="number"
                  min="1"
                  max="100"
                  class="form-control"
                />
              </div>

              <div class="form-group">
                <label>Score Threshold</label>
                <input
                  v-model.number="targetForm.search_score_threshold"
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  class="form-control"
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Retrieval Size (Single)</label>
                <input
                  v-model.number="targetForm.large_retrieval_size_single"
                  type="number"
                  min="10"
                  max="500"
                  class="form-control"
                />
              </div>

              <div class="form-group">
                <label>Retrieval Size (All)</label>
                <input
                  v-model.number="targetForm.large_retrieval_size_all"
                  type="number"
                  min="10"
                  max="500"
                  class="form-control"
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Algorithm</label>
                <select v-model="targetForm.algorithm" class="form-control">
                  <option value="ensemble">Ensemble (Vector + BM25)</option>
                  <option value="vector">Vector Only</option>
                  <option value="bm25">BM25 Only</option>
                  <option value="hnsw">HNSW</option>
                </select>
              </div>

              <div class="form-group">
                <label>Citation Limit</label>
                <input
                  v-model.number="targetForm.citation_limit"
                  type="number"
                  min="1"
                  max="50"
                  class="form-control"
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Temperature</label>
                <input
                  v-model.number="targetForm.temperature"
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  class="form-control"
                />
              </div>

              <div class="form-group">
                <label>Max Tokens</label>
                <input
                  v-model.number="targetForm.max_tokens"
                  type="number"
                  min="100"
                  max="100000"
                  class="form-control"
                />
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeTargetModal" class="btn btn-outline">
              Cancel
            </button>
            <button @click="saveTarget" class="btn btn-primary">
              {{ editingTarget ? 'Update' : 'Add' }} Target
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Deploy Mode Confirmation -->
    <Teleport to="body">
      <div v-if="showDeployConfirm" class="modal-overlay" @click.self="showDeployConfirm = false">
        <div class="modal-content">
          <h2 class="modal-title">⚠️ Enter Deploy Mode?</h2>
          <div class="modal-body">
            <p>This will lock your configuration:</p>
            <ul>
              <li>Corpus: <strong>{{ corpusInfo?.name }}</strong></li>
              <li>Targets: <strong>{{ targets.length }} configured</strong></li>
              <li>Default: <strong>{{ defaultTarget }}</strong></li>
            </ul>
            <div class="alert alert-warning">
              Configuration cannot be changed without restarting the server.
            </div>
          </div>
          <div class="modal-footer">
            <button @click="showDeployConfirm = false" class="btn btn-outline">
              Stay in Configuration
            </button>
            <button @click="enterDeployMode" class="btn btn-success">
              Enter Deploy Mode
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'ConfigManager',
  setup() {
    const router = useRouter()

    // State
    const loading = ref(true)
    const corpusInfo = ref(null)
    const targets = ref([])
    const defaultTarget = ref(null)
    const showAddTarget = ref(false)
    const editingTarget = ref(null)
    const showDeployConfirm = ref(false)

    // Target form
    const targetForm = ref({
      id: '',
      llm_provider: 'anthropic',
      llm_model: '',
      search_k: 20,
      search_score_threshold: 0.7,
      large_retrieval_size_single: 120,
      large_retrieval_size_all: 120,
      algorithm: 'ensemble',
      citation_limit: 10,
      temperature: 0.7,
      max_tokens: 4096
    })

    // Load configuration
    const loadConfiguration = async () => {
      try {
        // Fetch mode status
        const response = await fetch('/api/mode/status')
        const data = await response.json()

        // Check if in deploy mode
        if (data.mode === 'deploy') {
          // Redirect to chat if in deploy mode
          router.push('/chat')
          return
        }

        corpusInfo.value = data.corpus_info
        defaultTarget.value = data.default_target

        // Load targets
        await loadTargets()

        loading.value = false
      } catch (error) {
        console.error('Failed to load configuration:', error)
        alert('Failed to load configuration')
        loading.value = false
      }
    }

    // Load targets
    const loadTargets = async () => {
      try {
        const response = await fetch('/api/corpus-wizard/list-targets')
        if (response.ok) {
          const data = await response.json()
          targets.value = data.targets || []
        }
      } catch (error) {
        console.error('Failed to load targets:', error)
      }
    }

    // Actions
    const buildNewCorpus = () => {
      router.push('/corpus-wizard')
    }

    const rebuildCorpus = () => {
      if (confirm('This will overwrite your existing corpus. Are you sure?')) {
        router.push('/corpus-wizard?rebuild=true')
      }
    }

    const closeTargetModal = () => {
      showAddTarget.value = false
      editingTarget.value = null
      resetTargetForm()
    }

    const resetTargetForm = () => {
      targetForm.value = {
        id: '',
        llm_provider: 'anthropic',
        llm_model: '',
        search_k: 20,
        search_score_threshold: 0.7,
        large_retrieval_size_single: 120,
        large_retrieval_size_all: 120,
        algorithm: 'ensemble',
        citation_limit: 10,
        temperature: 0.7,
        max_tokens: 4096
      }
    }

    const editTarget = (target) => {
      targetForm.value = { ...target }
      editingTarget.value = target
      showAddTarget.value = true
    }

    const saveTarget = async () => {
      try {
        const endpoint = editingTarget.value
          ? `/api/corpus-wizard/update-target/${targetForm.value.id}`
          : '/api/corpus-wizard/add-target'

        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(targetForm.value)
        })

        if (response.ok) {
          await loadTargets()
          closeTargetModal()
        } else {
          const error = await response.json()
          alert(`Failed to save target: ${error.detail}`)
        }
      } catch (error) {
        console.error('Failed to save target:', error)
        alert('Failed to save target')
      }
    }

    const setDefaultTarget = async (targetId) => {
      try {
        const response = await fetch(`/api/corpus-wizard/set-default-target/${targetId}`, {
          method: 'POST'
        })

        if (response.ok) {
          defaultTarget.value = targetId
          await loadTargets()
        }
      } catch (error) {
        console.error('Failed to set default target:', error)
        alert('Failed to set default target')
      }
    }

    const confirmDeleteTarget = (target) => {
      if (confirm(`Delete target "${target.id}"?`)) {
        deleteTarget(target.id)
      }
    }

    const deleteTarget = async (targetId) => {
      try {
        const response = await fetch(`/api/corpus-wizard/delete-target/${targetId}`, {
          method: 'DELETE'
        })

        if (response.ok) {
          await loadTargets()
        }
      } catch (error) {
        console.error('Failed to delete target:', error)
        alert('Failed to delete target')
      }
    }

    const confirmDeployMode = () => {
      if (!corpusInfo.value) {
        alert('No corpus configured. Please build a corpus first.')
        return
      }
      if (targets.value.length === 0) {
        alert('No test targets configured. Please add at least one target.')
        return
      }
      showDeployConfirm.value = true
    }

    const enterDeployMode = async () => {
      try {
        const response = await fetch('/api/mode/deploy', {
          method: 'POST'
        })

        if (response.ok) {
          router.push('/chat')
        } else {
          const error = await response.json()
          alert(`Failed to enter deploy mode: ${error.detail}`)
        }
      } catch (error) {
        console.error('Failed to enter deploy mode:', error)
        alert('Failed to enter deploy mode')
      }
    }

    // Lifecycle
    onMounted(() => {
      loadConfiguration()
    })

    return {
      loading,
      corpusInfo,
      targets,
      defaultTarget,
      showAddTarget,
      editingTarget,
      showDeployConfirm,
      targetForm,
      buildNewCorpus,
      rebuildCorpus,
      closeTargetModal,
      editTarget,
      saveTarget,
      setDefaultTarget,
      confirmDeleteTarget,
      confirmDeployMode,
      enterDeployMode
    }
  }
}
</script>

<style scoped>
.config-manager {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.config-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #1a202c;
}

.mode-badge {
  display: flex;
  align-items: center;
}

.badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
}

.badge-config {
  background: #fef3c7;
  color: #92400e;
}

.badge-default {
  background: #dbeafe;
  color: #1e40af;
}

/* Loading */
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

/* Config sections */
.config-section {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.config-section h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

/* Corpus info */
.corpus-info {
  background: #f7fafc;
  border-radius: 6px;
  padding: 1.5rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.info-item label {
  font-weight: 600;
  color: #4a5568;
}

.info-item span {
  color: #2d3748;
}

.corpus-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

/* Targets */
.targets-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.target-card {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 1rem;
  background: #fff;
}

.target-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.target-header h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

.target-details {
  margin-bottom: 1rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
  font-size: 0.875rem;
}

.detail-label {
  color: #718096;
}

.detail-value {
  color: #2d3748;
  font-weight: 500;
}

.target-actions {
  display: flex;
  gap: 0.5rem;
}

/* No content states */
.no-corpus,
.no-targets {
  text-align: center;
  padding: 2rem;
  color: #718096;
}

/* Actions */
.config-actions {
  text-align: center;
  padding: 2rem;
  background: #f7fafc;
  border-radius: 8px;
}

.action-note {
  color: #718096;
  font-size: 0.875rem;
  margin-top: 1rem;
}

/* Forms */
.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #4a5568;
}

.form-control {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
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
  border-radius: 8px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-lg {
  max-width: 700px;
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

.modal-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

/* Buttons */
.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  display: inline-block;
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

.btn-success {
  background: #48bb78;
  color: white;
}

.btn-success:hover {
  background: #38a169;
}

.btn-warning {
  background: #f6ad55;
  color: white;
}

.btn-warning:hover {
  background: #ed8936;
}

.btn-danger {
  background: #fc8181;
  color: white;
}

.btn-outline {
  background: white;
  color: #4a5568;
  border: 1px solid #e2e8f0;
}

.btn-outline:hover {
  background: #f7fafc;
}

.btn-sm {
  padding: 0.25rem 0.75rem;
  font-size: 0.875rem;
}

.btn-lg {
  padding: 0.75rem 1.5rem;
  font-size: 1.125rem;
}

/* Alerts */
.alert {
  padding: 1rem;
  border-radius: 6px;
  margin: 1rem 0;
}

.alert-warning {
  background: #fef3c7;
  border: 1px solid #fbbf24;
  color: #92400e;
}
</style>