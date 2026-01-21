<template>
  <div class="corpus-wizard">
    <!-- Header -->
    <div class="wizard-header">
      <h1>ATLAS Corpus Configuration Wizard</h1>
      <p class="subtitle">Configure and swap text corpora for your research</p>
    </div>

    <!-- Progress Steps -->
    <div class="wizard-steps">
      <div
        v-for="(step, index) in steps"
        :key="index"
        :class="['step', {
          'active': currentStep === index + 1,
          'completed': currentStep > index + 1
        }]"
      >
        <div class="step-number">{{ index + 1 }}</div>
        <div class="step-label">{{ step }}</div>
      </div>
    </div>

    <!-- Wizard Content -->
    <div class="wizard-content">
      <!-- Step 1: Metadata -->
      <div v-if="currentStep === 1" class="wizard-step">
        <h2>Tell us about your corpus</h2>
        <div class="form-group">
          <label>Corpus Name *</label>
          <input
            v-model="metadata.name"
            type="text"
            placeholder="e.g., Darwin Correspondence Project"
            class="form-control"
          />
        </div>

        <div class="form-group">
          <label>Description</label>
          <textarea
            v-model="metadata.description"
            placeholder="Brief description of your corpus"
            class="form-control"
            rows="3"
          ></textarea>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Time Period From</label>
            <input
              v-model.number="metadata.time_period_from"
              type="number"
              placeholder="e.g., 1825"
              class="form-control"
            />
          </div>
          <div class="form-group">
            <label>Time Period To</label>
            <input
              v-model.number="metadata.time_period_to"
              type="number"
              placeholder="e.g., 1882"
              class="form-control"
            />
          </div>
        </div>

        <div class="form-group">
          <label>Material Type</label>
          <select v-model="metadata.material_type" class="form-control">
            <option value="">Select type...</option>
            <option value="parliamentary">Parliamentary records</option>
            <option value="personal_correspondence">Personal correspondence</option>
            <option value="news_articles">News articles</option>
            <option value="academic_papers">Academic papers</option>
            <option value="literary_works">Literary works</option>
            <option value="general">General/Mixed</option>
          </select>
        </div>

        <div class="form-group">
          <label>Key People (comma-separated)</label>
          <input
            v-model="metadata.people_text"
            type="text"
            placeholder="e.g., Charles Darwin, Thomas Huxley, Alfred Wallace"
            class="form-control"
            @blur="parsePeople"
          />
        </div>

        <div class="form-group">
          <label>Topics (comma-separated)</label>
          <input
            v-model="metadata.topics_text"
            type="text"
            placeholder="e.g., evolution, natural selection, biology"
            class="form-control"
            @blur="parseTopics"
          />
        </div>

        <div class="form-group">
          <label>Copyright Status</label>
          <select v-model="metadata.copyright_status" class="form-control">
            <option value="">Select status...</option>
            <option value="public_domain">Public Domain</option>
            <option value="cc_by">Creative Commons BY</option>
            <option value="cc_by_sa">Creative Commons BY-SA</option>
            <option value="cc_by_nc">Creative Commons BY-NC</option>
            <option value="proprietary">Proprietary/Licensed</option>
            <option value="mixed">Mixed</option>
          </select>
        </div>

        <div class="form-group">
          <label>DOI (Optional)</label>
          <input
            v-model="metadata.doi"
            type="text"
            placeholder="e.g., 10.5281/zenodo.1234567"
            class="form-control"
          />
        </div>
      </div>

      <!-- Step 2: Source Selection -->
      <div v-if="currentStep === 2" class="wizard-step">
        <h2>Where is your corpus located?</h2>

        <div class="source-type-selector">
          <div
            :class="['source-option', { active: source.type === 'local' }]"
            @click="source.type = 'local'"
          >
            <i class="icon">📁</i>
            <h3>Local Directory</h3>
            <p>Corpus files on this machine</p>
          </div>
          <div
            :class="['source-option', { active: source.type === 'github' }]"
            @click="source.type = 'github'"
          >
            <i class="icon">🌐</i>
            <h3>GitHub Repository</h3>
            <p>Corpus hosted on GitHub</p>
          </div>
        </div>

        <div v-if="source.type === 'local'" class="form-group">
          <label>Directory Path</label>
          <input
            v-model="source.location"
            type="text"
            placeholder="/path/to/corpus/files"
            class="form-control"
          />
        </div>

        <div v-if="source.type === 'github'" class="github-inputs">
          <div class="form-group">
            <label>Repository URL</label>
            <input
              v-model="source.location"
              type="text"
              placeholder="https://github.com/owner/repository"
              class="form-control"
            />
          </div>
          <div class="form-group">
            <label>Branch</label>
            <input
              v-model="source.branch"
              type="text"
              placeholder="main"
              class="form-control"
            />
          </div>
          <div class="form-group">
            <label>Path within repository (optional)</label>
            <input
              v-model="source.path"
              type="text"
              placeholder="corpus/"
              class="form-control"
            />
          </div>
        </div>

        <div class="form-group">
          <label>File Types to Include</label>
          <div class="checkbox-group">
            <label class="checkbox">
              <input type="checkbox" v-model="source.file_types" value="txt" />
              Text files (.txt)
            </label>
            <label class="checkbox">
              <input type="checkbox" v-model="source.file_types" value="xml" />
              XML files (.xml)
            </label>
            <label class="checkbox">
              <input type="checkbox" v-model="source.file_types" value="pdf" />
              PDF files (.pdf)
            </label>
          </div>
        </div>

        <div class="form-actions">
          <button @click="analyzeCorpus" :disabled="analyzing" class="btn btn-primary">
            {{ analyzing ? 'Analyzing...' : 'Analyze Corpus' }}
          </button>
        </div>

        <div v-if="analysisResult" class="analysis-result">
          <h3>Analysis Results</h3>
          <p>Found {{ analysisResult.total_files }} files</p>
          <div v-if="analysisResult.suggested_filters">
            <h4>Suggested Filters:</h4>
            <ul>
              <li v-for="filter in analysisResult.suggested_filters" :key="filter.id">
                {{ filter.label }} ({{ filter.type }})
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Step 3: System Requirements -->
      <div v-if="currentStep === 3" class="wizard-step">
        <h2>System Requirements Check</h2>

        <div v-if="!systemInfo" class="loading">
          Checking system capabilities...
        </div>

        <div v-if="systemInfo" class="system-info">
          <div class="info-section">
            <h3>Hardware Detected</h3>
            <div class="hardware-info">
              <div class="info-item">
                <span class="label">CPU:</span>
                <span>{{ systemInfo.cpu.cores }} cores, {{ systemInfo.cpu.threads }} threads</span>
              </div>
              <div class="info-item">
                <span class="label">RAM:</span>
                <span>{{ Math.round(systemInfo.memory.available_gb) }}GB / {{ Math.round(systemInfo.memory.total_gb) }}GB available</span>
              </div>
              <div class="info-item">
                <span class="label">GPU:</span>
                <span v-if="systemInfo.gpu.available">
                  {{ systemInfo.gpu.name }} ({{ Math.round(systemInfo.gpu.memory_gb) }}GB)
                </span>
                <span v-else class="warning">No GPU detected</span>
              </div>
              <div class="info-item">
                <span class="label">Disk:</span>
                <span>{{ Math.round(systemInfo.disk.free_gb) }}GB free</span>
              </div>
            </div>
          </div>

          <div class="info-section">
            <h3>Processing Options</h3>
            <div class="processing-modes">
              <div
                :class="['mode-option', {
                  active: processingMode === 'cpu',
                  disabled: !systemInfo.cpu.available
                }]"
                @click="processingMode = 'cpu'"
              >
                <h4>CPU Mode</h4>
                <p>Estimated time: {{ systemInfo.estimated_build_time.cpu.formatted }}</p>
                <p>Speed: {{ systemInfo.estimated_build_time.cpu.docs_per_second.toFixed(1) }} docs/sec</p>
              </div>
              <div
                v-if="systemInfo.gpu.available"
                :class="['mode-option', {
                  active: processingMode === 'gpu',
                  recommended: true
                }]"
                @click="processingMode = 'gpu'"
              >
                <h4>GPU Mode</h4>
                <p>Estimated time: {{ systemInfo.estimated_build_time.gpu.formatted }}</p>
                <p>Speed: {{ systemInfo.estimated_build_time.gpu.docs_per_second.toFixed(1) }} docs/sec</p>
                <span class="badge">Recommended</span>
              </div>
            </div>
          </div>

          <div v-if="systemInfo.warnings && systemInfo.warnings.length > 0" class="warnings">
            <h3>⚠️ Warnings</h3>
            <div v-for="warning in systemInfo.warnings" :key="warning.type" class="warning-item">
              {{ warning.message }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <div class="wizard-navigation">
      <button
        v-if="currentStep > 1"
        @click="previousStep"
        class="btn btn-secondary"
      >
        Previous
      </button>
      <button
        v-if="currentStep < steps.length"
        @click="nextStep"
        :disabled="!canProceed"
        class="btn btn-primary"
      >
        Next
      </button>
      <button
        v-if="currentStep === steps.length"
        @click="startBuild"
        class="btn btn-success"
        :disabled="building"
      >
        {{ building ? 'Building...' : 'Build Corpus' }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'

export default {
  name: 'CorpusWizard',
  setup() {
    // Wizard state
    const currentStep = ref(1)
    const steps = [
      'Metadata',
      'Source',
      'Requirements',
      'Filters',
      'Model',
      'Build',
      'Activate'
    ]

    // Form data
    const metadata = ref({
      name: '',
      description: '',
      time_period_from: null,
      time_period_to: null,
      material_type: '',
      people_text: '',
      people: [],
      topics_text: '',
      topics: [],
      copyright_status: '',
      doi: ''
    })

    const source = ref({
      type: 'local',
      location: '',
      branch: 'main',
      path: '',
      file_types: ['txt']
    })

    const systemInfo = ref(null)
    const processingMode = ref('cpu')
    const analysisResult = ref(null)
    const analyzing = ref(false)
    const building = ref(false)

    // Parse comma-separated values
    const parsePeople = () => {
      metadata.value.people = metadata.value.people_text
        .split(',')
        .map(p => p.trim())
        .filter(p => p)
    }

    const parseTopics = () => {
      metadata.value.topics = metadata.value.topics_text
        .split(',')
        .map(t => t.trim())
        .filter(t => t)
    }

    // Check if can proceed to next step
    const canProceed = computed(() => {
      switch (currentStep.value) {
        case 1:
          return metadata.value.name && metadata.value.name.length > 0
        case 2:
          return source.value.location && source.value.location.length > 0
        default:
          return true
      }
    })

    // Navigation
    const nextStep = () => {
      if (canProceed.value && currentStep.value < steps.length) {
        currentStep.value++
        if (currentStep.value === 3) {
          checkSystemRequirements()
        }
      }
    }

    const previousStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--
      }
    }

    // API calls
    const analyzeCorpus = async () => {
      analyzing.value = true
      try {
        const response = await fetch('/api/corpus-wizard/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            source_type: source.value.type,
            source_location: source.value.location,
            file_types: source.value.file_types,
            metadata: {
              ...metadata.value,
              branch: source.value.branch,
              repo_path: source.value.path
            }
          })
        })
        analysisResult.value = await response.json()
      } catch (error) {
        console.error('Analysis failed:', error)
        alert('Failed to analyze corpus: ' + error.message)
      } finally {
        analyzing.value = false
      }
    }

    const checkSystemRequirements = async () => {
      try {
        const docCount = analysisResult.value?.total_files || 1000
        const response = await fetch(`/api/corpus-wizard/system-requirements?doc_count=${docCount}`)
        systemInfo.value = await response.json()

        // Set default mode based on recommendation
        if (systemInfo.value.recommended_mode) {
          processingMode.value = systemInfo.value.recommended_mode
        }
      } catch (error) {
        console.error('Failed to check system requirements:', error)
      }
    }

    const startBuild = async () => {
      building.value = true
      // TODO: Implement build process
      console.log('Starting build with mode:', processingMode.value)
    }

    // Enable wizard mode on mount
    onMounted(async () => {
      try {
        await fetch('/api/corpus-wizard/mode', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ enabled: true })
        })
      } catch (error) {
        console.error('Failed to enable wizard mode:', error)
      }
    })

    return {
      currentStep,
      steps,
      metadata,
      source,
      systemInfo,
      processingMode,
      analysisResult,
      analyzing,
      building,
      canProceed,
      parsePeople,
      parseTopics,
      nextStep,
      previousStep,
      analyzeCorpus,
      checkSystemRequirements,
      startBuild
    }
  }
}
</script>

<style scoped>
.corpus-wizard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.wizard-header {
  text-align: center;
  margin-bottom: 3rem;
}

.wizard-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  font-size: 1.1rem;
}

/* Progress Steps */
.wizard-steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 3rem;
  padding: 0 2rem;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  opacity: 0.5;
  transition: opacity 0.3s;
}

.step.active,
.step.completed {
  opacity: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.step.active .step-number {
  background: #007bff;
  color: white;
}

.step.completed .step-number {
  background: #28a745;
  color: white;
}

.step-label {
  font-size: 0.9rem;
}

/* Form Elements */
.wizard-content {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 2rem;
  min-height: 400px;
}

.wizard-step h2 {
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: #007bff;
}

textarea.form-control {
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.checkbox-group {
  display: flex;
  gap: 1.5rem;
}

.checkbox {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.checkbox input {
  margin-right: 0.5rem;
}

/* Source Selection */
.source-type-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 2rem;
}

.source-option {
  padding: 1.5rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.source-option:hover {
  border-color: #007bff;
}

.source-option.active {
  border-color: #007bff;
  background: #f0f8ff;
}

.source-option .icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.source-option h3 {
  margin: 0.5rem 0;
}

.source-option p {
  color: #666;
  margin: 0;
}

/* System Info */
.system-info {
  display: grid;
  gap: 2rem;
}

.info-section h3 {
  margin-bottom: 1rem;
}

.hardware-info {
  background: white;
  padding: 1rem;
  border-radius: 4px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  font-weight: 500;
}

.processing-modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.mode-option {
  padding: 1.5rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}

.mode-option:hover {
  border-color: #007bff;
}

.mode-option.active {
  border-color: #007bff;
  background: #f0f8ff;
}

.mode-option.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-option.recommended {
  border-color: #28a745;
}

.mode-option h4 {
  margin-top: 0;
}

.badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: #28a745;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

/* Warnings */
.warnings {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  padding: 1rem;
}

.warning-item {
  padding: 0.5rem 0;
}

/* Navigation */
.wizard-navigation {
  display: flex;
  justify-content: space-between;
  margin-top: 2rem;
  padding: 0 2rem;
}

.btn {
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #545b62;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #218838;
}

/* Loading States */
.loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.analysis-result {
  margin-top: 2rem;
  padding: 1rem;
  background: white;
  border-radius: 4px;
}

.analysis-result h3 {
  margin-top: 0;
}

.analysis-result ul {
  list-style: none;
  padding: 0;
}

.analysis-result li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}
</style>