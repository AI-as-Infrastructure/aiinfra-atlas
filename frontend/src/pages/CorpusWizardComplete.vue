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
        </div>
      </div>

      <!-- Step 3: Filter Configuration -->
      <div v-if="currentStep === 3" class="wizard-step">
        <h2>Configure Search Filters</h2>

        <div v-if="!filters || filters.length === 0" class="loading">
          Discovering filters...
        </div>

        <div v-if="filters && filters.length > 0" class="filter-config">
          <p class="help-text">
            These filters will be available when searching your corpus. You can edit or remove them as needed.
          </p>

          <div class="filter-list">
            <div v-for="(filter, index) in filters" :key="filter.id" class="filter-item">
              <div class="filter-header">
                <input
                  v-model="filter.label"
                  type="text"
                  class="filter-label-input"
                  placeholder="Filter label"
                />
                <button @click="removeFilter(index)" class="btn-remove">×</button>
              </div>
              <div class="filter-details">
                <span class="filter-id">ID: {{ filter.id }}</span>
                <span class="filter-type">Type: {{ filter.type }}</span>
                <span v-if="filter.document_count" class="filter-count">
                  ~{{ filter.document_count }} docs
                </span>
              </div>
            </div>
          </div>

          <button @click="addCustomFilter" class="btn btn-secondary">
            + Add Custom Filter
          </button>
        </div>
      </div>

      <!-- Step 4: Model Selection -->
      <div v-if="currentStep === 4" class="wizard-step">
        <h2>Select Embedding Model</h2>

        <div v-if="!modelRecommendations" class="loading">
          Getting model recommendations...
        </div>

        <div v-if="modelRecommendations && modelRecommendations.length > 0" class="model-selection">
          <div
            v-for="model in modelRecommendations"
            :key="model.model"
            :class="['model-option', {
              active: selectedModel === model.model,
              recommended: model === modelRecommendations[0]
            }]"
            @click="selectedModel = model.model"
          >
            <div class="model-header">
              <h4>{{ model.model.split('/').pop() }}</h4>
              <span v-if="model === modelRecommendations[0]" class="badge">Recommended</span>
            </div>
            <p class="model-reason">{{ model.reason }}</p>
            <div class="model-stats">
              <span>Match Score: {{ Math.round(model.score * 100) }}%</span>
              <span v-if="model.characteristics">
                Size: {{ model.characteristics.size_mb }}MB
              </span>
            </div>
          </div>

          <div class="custom-model-section">
            <h4>Or use a custom model:</h4>
            <input
              v-model="customModel"
              type="text"
              placeholder="huggingface-org/model-name"
              class="form-control"
              @input="selectedModel = customModel"
            />
          </div>
        </div>
      </div>

      <!-- Step 5: System Requirements -->
      <div v-if="currentStep === 5" class="wizard-step">
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

      <!-- Step 6: Build Progress -->
      <div v-if="currentStep === 6" class="wizard-step">
        <BuildProgress
          :progress="buildProgress"
          :logs="buildLogs"
          @pause="pauseBuild"
          @resume="resumeBuild"
          @cancel="cancelBuild"
        />
      </div>

      <!-- Step 7: Test & Activate -->
      <div v-if="currentStep === 7" class="wizard-step">
        <h2>Test & Activate Corpus</h2>

        <div v-if="buildProgress.status === 'completed'" class="completion-section">
          <div class="success-message">
            ✅ Corpus built successfully!
          </div>

          <div class="build-summary">
            <h3>Build Summary</h3>
            <ul>
              <li>Documents processed: {{ buildProgress.processed_documents }}</li>
              <li>Time taken: {{ formatDuration(buildProgress.elapsed_seconds) }}</li>
              <li>Vector store size: {{ buildResults?.vector_store_size || 'Unknown' }}</li>
            </ul>
          </div>

          <div class="test-section">
            <h3>Test Search</h3>
            <input
              v-model="testQuery"
              type="text"
              placeholder="Enter a test query..."
              class="form-control"
              @keyup.enter="runTestSearch"
            />
            <button @click="runTestSearch" class="btn btn-primary">
              Test Search
            </button>

            <div v-if="testResults" class="test-results">
              <h4>Results:</h4>
              <div v-for="(result, index) in testResults" :key="index" class="test-result">
                {{ index + 1 }}. {{ result.excerpt }}
              </div>
            </div>
          </div>

          <div class="activation-section">
            <h3>Ready to Activate?</h3>
            <p>This will replace your current corpus. The old corpus will be backed up.</p>
            <button @click="activateCorpus" class="btn btn-success">
              Activate Corpus
            </button>
            <button @click="saveConfiguration" class="btn btn-secondary">
              Save Configuration Only
            </button>
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
        v-if="currentStep < steps.length - 1"
        @click="nextStep"
        :disabled="!canProceed"
        class="btn btn-primary"
      >
        Next
      </button>
      <button
        v-if="currentStep === 5"
        @click="startBuild"
        class="btn btn-success"
        :disabled="building"
      >
        {{ building ? 'Starting...' : 'Start Build' }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import BuildProgress from '@/components/wizard/BuildProgress.vue'

export default {
  name: 'CorpusWizardComplete',
  components: {
    BuildProgress
  },
  setup() {
    // Wizard state
    const currentStep = ref(1)
    const steps = [
      'Metadata',
      'Source',
      'Filters',
      'Model',
      'Requirements',
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

    const filters = ref([])
    const selectedModel = ref('')
    const customModel = ref('')
    const modelRecommendations = ref(null)
    const systemInfo = ref(null)
    const processingMode = ref('cpu')
    const analysisResult = ref(null)
    const analyzing = ref(false)
    const building = ref(false)
    const buildProgress = ref({})
    const buildLogs = ref([])
    const buildId = ref(null)
    const buildResults = ref(null)
    const testQuery = ref('')
    const testResults = ref(null)

    // SSE connection for build progress
    let eventSource = null

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
        case 3:
          return filters.value.length > 0
        case 4:
          return selectedModel.value && selectedModel.value.length > 0
        default:
          return true
      }
    })

    // Navigation
    const nextStep = async () => {
      if (canProceed.value && currentStep.value < steps.length) {
        // Perform step-specific actions
        if (currentStep.value === 2 && !analysisResult.value) {
          await analyzeCorpus()
        } else if (currentStep.value === 3) {
          await getModelRecommendations()
        } else if (currentStep.value === 4) {
          await checkSystemRequirements()
        }

        currentStep.value++
      }
    }

    const previousStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--
      }
    }

    // Filter management
    const removeFilter = (index) => {
      filters.value.splice(index, 1)
    }

    const addCustomFilter = () => {
      filters.value.push({
        id: `custom_${Date.now()}`,
        label: 'New Filter',
        type: 'custom',
        pattern: '**/*.txt'
      })
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

        // Get filter suggestions
        if (analysisResult.value.total_files > 0) {
          await suggestFilters()
        }
      } catch (error) {
        console.error('Analysis failed:', error)
        alert('Failed to analyze corpus: ' + error.message)
      } finally {
        analyzing.value = false
      }
    }

    const suggestFilters = async () => {
      try {
        const response = await fetch('/api/corpus-wizard/suggest-filters', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            metadata: metadata.value,
            structure_analysis: analysisResult.value
          })
        })
        const result = await response.json()
        filters.value = result.filters || []
      } catch (error) {
        console.error('Failed to get filter suggestions:', error)
      }
    }

    const getModelRecommendations = async () => {
      try {
        const response = await fetch('/api/corpus-wizard/recommend-model', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(metadata.value)
        })
        const result = await response.json()
        modelRecommendations.value = result.recommendations
        if (result.recommendations && result.recommendations.length > 0) {
          selectedModel.value = result.recommendations[0].model
        }
      } catch (error) {
        console.error('Failed to get model recommendations:', error)
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
      currentStep.value++

      try {
        // Prepare configuration
        const config = {
          metadata: {
            ...metadata.value,
            created_by: 'corpus_wizard'
          },
          source: source.value,
          filters: filters.value,
          embeddings: {
            model: selectedModel.value,
            pooling: 'mean',
            chunk_size: 1000,
            chunk_overlap: 100,
            batch_size: 100
          },
          vector_store: {
            type: 'chromadb',
            collection_name: metadata.value.name.toLowerCase().replace(/\s+/g, '_'),
            persist_directory: 'backend/targets/chroma_db'
          },
          search: {
            type: 'hybrid',
            k_default: 10,
            large_single_corpus: 120,
            large_all_corpus: 80
          }
        }

        // Start build
        const response = await fetch('/api/corpus-wizard/build', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            config: config,
            mode: processingMode.value
          })
        })

        const result = await response.json()
        buildId.value = result.build_id

        // Start SSE connection for progress updates
        connectProgressStream()
      } catch (error) {
        console.error('Failed to start build:', error)
        alert('Failed to start build: ' + error.message)
        building.value = false
        currentStep.value--
      }
    }

    const connectProgressStream = () => {
      if (!buildId.value) return

      eventSource = new EventSource(`/api/corpus-wizard/progress-stream/${buildId.value}`)

      eventSource.onmessage = (event) => {
        const progress = JSON.parse(event.data)
        buildProgress.value = progress

        // Add log entry
        if (progress.current_document) {
          buildLogs.value.push({
            timestamp: new Date(),
            level: 'info',
            message: `Processing: ${progress.current_document}`
          })
        }

        // Check if completed
        if (progress.status === 'completed') {
          building.value = false
          buildResults.value = progress.results
          eventSource.close()
        } else if (progress.status === 'failed') {
          building.value = false
          alert('Build failed: ' + progress.error)
          eventSource.close()
        }
      }

      eventSource.onerror = (error) => {
        console.error('SSE error:', error)
        eventSource.close()
      }
    }

    const pauseBuild = () => {
      // TODO: Implement pause
      console.log('Pausing build...')
    }

    const resumeBuild = () => {
      // TODO: Implement resume
      console.log('Resuming build...')
    }

    const cancelBuild = () => {
      if (confirm('Are you sure you want to cancel the build?')) {
        if (eventSource) {
          eventSource.close()
        }
        building.value = false
        currentStep.value--
      }
    }

    const runTestSearch = async () => {
      // TODO: Implement test search
      console.log('Running test search:', testQuery.value)
      testResults.value = [
        { excerpt: 'Sample result 1...' },
        { excerpt: 'Sample result 2...' }
      ]
    }

    const activateCorpus = async () => {
      if (confirm('This will replace your current corpus. Continue?')) {
        try {
          const response = await fetch(`/api/corpus-wizard/activate/${metadata.value.name}`, {
            method: 'POST'
          })
          const result = await response.json()
          alert('Corpus activated! Please restart the server.')
        } catch (error) {
          console.error('Failed to activate corpus:', error)
          alert('Failed to activate corpus: ' + error.message)
        }
      }
    }

    const saveConfiguration = async () => {
      try {
        const config = {
          metadata: metadata.value,
          source: source.value,
          filters: filters.value,
          embeddings: {
            model: selectedModel.value
          }
        }

        const response = await fetch('/api/corpus-wizard/save-config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(config)
        })
        const result = await response.json()
        alert(`Configuration saved to ${result.path}`)
      } catch (error) {
        console.error('Failed to save configuration:', error)
      }
    }

    const formatDuration = (seconds) => {
      if (!seconds) return '—'
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      const secs = Math.floor(seconds % 60)

      if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`
      } else if (minutes > 0) {
        return `${minutes}m ${secs}s`
      } else {
        return `${secs}s`
      }
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

    // Cleanup on unmount
    onUnmounted(() => {
      if (eventSource) {
        eventSource.close()
      }
    })

    return {
      currentStep,
      steps,
      metadata,
      source,
      filters,
      selectedModel,
      customModel,
      modelRecommendations,
      systemInfo,
      processingMode,
      analysisResult,
      analyzing,
      building,
      buildProgress,
      buildLogs,
      buildResults,
      testQuery,
      testResults,
      canProceed,
      parsePeople,
      parseTopics,
      nextStep,
      previousStep,
      removeFilter,
      addCustomFilter,
      analyzeCorpus,
      startBuild,
      pauseBuild,
      resumeBuild,
      cancelBuild,
      runTestSearch,
      activateCorpus,
      saveConfiguration,
      formatDuration
    }
  }
}
</script>

<style scoped>
/* Import styles from original CorpusWizard.vue */
/* ... (same styles as before) ... */

.filter-config {
  padding: 1rem;
}

.help-text {
  color: #6c757d;
  margin-bottom: 1.5rem;
}

.filter-list {
  margin-bottom: 1.5rem;
}

.filter-item {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.filter-label-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  font-weight: 500;
}

.btn-remove {
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  font-size: 1.25rem;
  cursor: pointer;
  margin-left: 1rem;
}

.filter-details {
  display: flex;
  gap: 1rem;
  font-size: 0.9rem;
  color: #6c757d;
}

.model-selection {
  display: grid;
  gap: 1rem;
}

.model-option {
  padding: 1.5rem;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.model-option:hover {
  border-color: #007bff;
}

.model-option.active {
  border-color: #007bff;
  background: #f0f8ff;
}

.model-option.recommended {
  border-color: #28a745;
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.model-header h4 {
  margin: 0;
}

.model-reason {
  margin-bottom: 0.5rem;
  color: #495057;
}

.model-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.9rem;
  color: #6c757d;
}

.custom-model-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #dee2e6;
}

.completion-section {
  padding: 2rem;
}

.success-message {
  background: #d4edda;
  color: #155724;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  text-align: center;
  font-size: 1.25rem;
  font-weight: bold;
}

.build-summary {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.build-summary h3 {
  margin-top: 0;
}

.build-summary ul {
  list-style: none;
  padding: 0;
}

.build-summary li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}

.test-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.test-section h3 {
  margin-top: 0;
}

.test-section .form-control {
  margin-bottom: 1rem;
}

.test-results {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.test-result {
  padding: 0.5rem 0;
  border-bottom: 1px solid #dee2e6;
}

.activation-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
}

.activation-section h3 {
  margin-top: 0;
}

.activation-section p {
  color: #6c757d;
  margin-bottom: 1rem;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover {
  background: #218838;
}
</style>