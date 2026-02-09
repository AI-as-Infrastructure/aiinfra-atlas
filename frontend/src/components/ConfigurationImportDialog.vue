<template>
  <div v-if="show" class="modal is-active">
    <div class="modal-background" @click="$emit('close')"></div>
    <div class="modal-card">
      <header class="modal-card-head">
        <p class="modal-card-title">Import Configuration</p>
        <button class="delete" aria-label="close" @click="$emit('close')"></button>
      </header>
      <section class="modal-card-body">
        <!-- File Upload -->
        <div v-if="!configData" class="file-upload-section">
          <div class="field">
            <label class="label">Select Configuration File</label>
            <div class="file has-name is-boxed is-fullwidth">
              <label class="file-label">
                <input
                  class="file-input"
                  type="file"
                  accept=".json"
                  @change="handleFileSelect"
                  ref="fileInput"
                >
                <span class="file-cta">
                  <span class="file-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                      <polyline points="17 8 12 3 7 8"></polyline>
                      <line x1="12" y1="3" x2="12" y2="15"></line>
                    </svg>
                  </span>
                  <span class="file-label">Choose JSON file...</span>
                </span>
                <span class="file-name">
                  {{ fileName || 'No file selected' }}
                </span>
              </label>
            </div>
            <p class="help">Maximum file size: 10MB</p>
          </div>

          <!-- Validation Errors -->
          <div v-if="validationErrors.length > 0" class="notification is-danger mt-4">
            <strong>Validation Errors:</strong>
            <ul>
              <li v-for="error in validationErrors" :key="error">{{ error }}</li>
            </ul>
          </div>
        </div>

        <!-- Configuration Preview -->
        <div v-else class="config-preview">
          <h3 class="subtitle">Configuration Preview</h3>

          <!-- Configuration Info -->
          <div class="config-info">
            <div class="field">
              <label class="label">Configuration Name</label>
              <p>{{ configData.config_name || 'Unnamed Configuration' }}</p>
            </div>

            <div v-if="configData.description" class="field">
              <label class="label">Description</label>
              <p>{{ configData.description }}</p>
            </div>

            <div class="field">
              <label class="label">Exported</label>
              <p>{{ formatDate(configData.exported_at) }}</p>
            </div>

            <div v-if="configData.atlas_version" class="field">
              <label class="label">ATLAS Version</label>
              <p>{{ configData.atlas_version }}</p>
            </div>
          </div>

          <!-- Configuration Sections -->
          <div class="config-sections mt-4">
            <div v-if="configData.corpus" class="config-section">
              <h4 class="has-text-weight-bold">Corpus Configuration</h4>
              <ul>
                <li v-if="configData.corpus.name">Name: {{ configData.corpus.name }}</li>
                <li v-if="configData.corpus.embedding?.model">Embedding Model: {{ configData.corpus.embedding.model }}</li>
                <li v-if="configData.corpus.embedding?.chunk_size">Chunk Size: {{ configData.corpus.embedding.chunk_size }}</li>
              </ul>
            </div>

            <div v-if="configData.test_target" class="config-section mt-3">
              <h4 class="has-text-weight-bold">Test Target</h4>
              <ul>
                <li v-if="configData.test_target.provider">Provider: {{ configData.test_target.provider }}</li>
                <li v-if="configData.test_target.model">Model: {{ configData.test_target.model }}</li>
                <li v-if="configData.test_target.search_k">Search K: {{ configData.test_target.search_k }}</li>
              </ul>
            </div>

            <div v-if="configData.system" class="config-section mt-3">
              <h4 class="has-text-weight-bold">System Settings</h4>
              <ul>
                <li>Telemetry: {{ configData.system.telemetryEnabled ? 'Enabled' : 'Disabled' }}</li>
                <li>Inter-rater Feedback: {{ configData.system.interRaterEnabled ? 'Enabled' : 'Disabled' }}</li>
              </ul>
            </div>
          </div>

          <!-- Validation Warnings -->
          <div v-if="validationWarnings.length > 0" class="notification is-warning mt-4">
            <strong>Warnings:</strong>
            <ul>
              <li v-for="warning in validationWarnings" :key="warning">{{ warning }}</li>
            </ul>
          </div>
        </div>
      </section>
      <footer class="modal-card-foot">
        <button
          v-if="!configData"
          class="button is-primary"
          @click="validateFile"
          :disabled="!selectedFile || loading"
          :class="{ 'is-loading': loading }"
        >
          Validate
        </button>
        <button
          v-else
          class="button is-primary"
          @click="importConfiguration"
          :disabled="loading"
          :class="{ 'is-loading': loading }"
        >
          Import
        </button>
        <button
          v-if="configData"
          class="button"
          @click="reset"
        >
          Choose Different File
        </button>
        <button class="button" @click="$emit('close')">Cancel</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'imported'])

const fileInput = ref(null)
const selectedFile = ref(null)
const fileName = ref('')
const configData = ref(null)
const loading = ref(false)
const validationErrors = ref([])
const validationWarnings = ref([])

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    if (file.size > 10 * 1024 * 1024) {
      validationErrors.value = ['File size exceeds 10MB limit']
      return
    }
    selectedFile.value = file
    fileName.value = file.name
    validationErrors.value = []
  }
}

async function validateFile() {
  if (!selectedFile.value) return

  loading.value = true
  validationErrors.value = []
  validationWarnings.value = []

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const response = await fetch('/api/configuration/validate', {
      method: 'POST',
      body: formData
    })

    const result = await response.json()

    if (!result.valid) {
      validationErrors.value = result.errors || ['Invalid configuration file']
      return
    }

    // Parse the file to get configuration data
    const fileContent = await selectedFile.value.text()
    configData.value = JSON.parse(fileContent)
    validationWarnings.value = result.warnings || []

  } catch (error) {
    console.error('Validation failed:', error)
    validationErrors.value = [`Validation failed: ${error.message}`]
  } finally {
    loading.value = false
  }
}

async function importConfiguration() {
  if (!selectedFile.value) return

  loading.value = true

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const response = await fetch('/api/configuration/import', {
      method: 'POST',
      body: formData
    })

    const result = await response.json()

    if (!result.success && response.status !== 207) {
      throw new Error(result.message || 'Import failed')
    }

    // Show results
    let message = 'Configuration imported successfully!\n\n'
    if (result.corpus_applied) message += '✓ Corpus configuration applied\n'
    if (result.target_applied) message += '✓ Target configuration applied\n'
    if (result.system_applied) message += '✓ System settings applied\n'

    if (result.warnings && result.warnings.length > 0) {
      message += '\nWarnings:\n' + result.warnings.join('\n')
    }

    alert(message)

    // Emit imported event with the configuration data
    emit('imported', configData.value)
    emit('close')

  } catch (error) {
    console.error('Import failed:', error)
    alert(`Import failed: ${error.message}`)
  } finally {
    loading.value = false
  }
}

function reset() {
  configData.value = null
  selectedFile.value = null
  fileName.value = ''
  validationErrors.value = []
  validationWarnings.value = []
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function formatDate(dateString) {
  if (!dateString) return 'Unknown'
  try {
    return new Date(dateString).toLocaleString()
  } catch {
    return dateString
  }
}
</script>

<style scoped>
.modal-card {
  width: 600px;
  max-width: 90vw;
}

.file-upload-section {
  min-height: 200px;
}

.config-info {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 4px;
}

.config-info .field {
  margin-bottom: 0.75rem;
}

.config-info .field:last-child {
  margin-bottom: 0;
}

.config-info .label {
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.config-sections {
  max-height: 300px;
  overflow-y: auto;
}

.config-section {
  padding: 0.75rem;
  background: #fafafa;
  border-radius: 4px;
}

.config-section h4 {
  margin-bottom: 0.5rem;
}

.config-section ul {
  margin-left: 1rem;
}

.config-section li {
  list-style-type: disc;
  margin-bottom: 0.25rem;
}
</style>