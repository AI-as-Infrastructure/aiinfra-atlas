<template>
  <div class="corpus-wizard">
    <!-- Header -->
    <div class="wizard-header">
      <h1>ATLAS Corpus Configuration Wizard</h1>
      <p class="subtitle">Configure and swap text corpora for your research</p>
    </div>
    <!-- Force reload trigger -->

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
      <!-- Step 1: Workflow Type Selection -->
      <div v-if="currentStep === 1" class="wizard-step">
        <h2>Select Workflow Type</h2>
        <p class="help-text">Choose how you want to process your corpus documents.</p>

        <div class="workflow-selector">
          <div
            :class="['workflow-option', { active: workflowType === 'text' }]"
            @click="workflowType = 'text'"
          >
            <i class="icon">📄</i>
            <h3>Text Workflow</h3>
            <p>For plain text documents (.txt)</p>
            <ul>
              <li>Simple text extraction</li>
              <li>URL and date parsing</li>
              <li>Directory-based organization</li>
            </ul>
          </div>
          <div
            :class="['workflow-option', { active: workflowType === 'xml', disabled: true }]"
            @click="() => {}"
          >
            <i class="icon">🏷️</i>
            <h3>XML Workflow</h3>
            <p>For structured XML documents</p>
            <ul>
              <li>Structured data extraction</li>
              <li>Metadata from tags</li>
              <li>Schema validation</li>
            </ul>
            <span class="coming-soon">Coming Soon</span>
          </div>
        </div>
      </div>

      <!-- Step 2: Metadata -->
      <div v-if="currentStep === 2" class="wizard-step">
        <h2>Basic Corpus Information</h2>
        <p class="help-text">Provide essential information about your corpus.</p>

        <div class="form-group">
          <label>Title *</label>
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

        <div class="form-group">
          <label>Copyright Status *</label>
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

      <!-- Step 3: Source Configuration -->
      <div v-if="currentStep === 3" class="wizard-step">
        <h2>Configure Document Sources</h2>
        <p class="help-text">Specify where your documents are located and how to process them.</p>

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
          <label>Directory Path *</label>
          <input
            v-model="source.location"
            type="text"
            placeholder="/path/to/corpus/files"
            class="form-control"
          />
        </div>

        <div v-if="source.type === 'github'" class="github-inputs">
          <div class="form-group">
            <label>Repository URL *</label>
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

        <!-- File Filters and Processing Options -->
        <div class="processing-options">
          <h3>Document Processing</h3>

          <div class="form-group">
            <label>File Extensions to Include</label>
            <input
              v-model="source.file_extensions"
              type="text"
              placeholder=".txt (comma-separated for multiple)"
              class="form-control"
            />
          </div>

          <div class="form-group">
            <label class="checkbox">
              <input type="checkbox" v-model="source.include_subdirectories" />
              Include subdirectories
            </label>
          </div>

          <div class="form-group">
            <label class="checkbox">
              <input type="checkbox" v-model="source.extract_inline_urls" />
              Extract URL from first line of documents (if present)
            </label>
          </div>

          <div class="form-group">
            <label>Date Pattern in Filename (Optional)</label>
            <select v-model="source.date_pattern" class="form-control">
              <option value="">No date extraction</option>
              <option value="YYYY-MM-DD">YYYY-MM-DD (e.g., 2024-01-15)</option>
              <option value="DD-MM-YYYY">DD-MM-YYYY (e.g., 15-01-2024)</option>
              <option value="YYYYMMDD">YYYYMMDD (e.g., 20240115)</option>
              <option value="custom">Custom pattern</option>
            </select>
          </div>

          <div v-if="source.date_pattern === 'custom'" class="form-group">
            <label>Custom Date Pattern</label>
            <div class="regex-input-group">
              <input
                v-model="source.custom_date_pattern"
                type="text"
                placeholder="e.g., (\d+\w*\s+\w+,\s*\d+)"
                class="form-control"
                :class="{ 'is-invalid': regexValidation.tested && !regexValidation.valid }"
                @input="clearRegexValidation"
              />
              <button
                @click="validateRegexPattern"
                :disabled="!source.custom_date_pattern"
                class="btn btn-secondary"
                type="button"
              >
                Validate Pattern
              </button>
            </div>

            <div v-if="regexValidation.tested" class="validation-feedback">
              <div v-if="regexValidation.valid" class="success-message">
                ✅ Valid pattern
                <span v-if="regexValidation.matches && regexValidation.matches.length > 0">
                  - Found: {{ regexValidation.matches.join(', ') }}
                </span>
              </div>
              <div v-else class="error-message">
                ❌ Invalid pattern: {{ regexValidation.error }}
              </div>
            </div>

            <small class="help-text">
              Example patterns:<br/>
              • <code>(\d+\w*\s+\w+,\s*\d+)</code> - Matches "6th June, 1901"<br/>
              • <code>(\d{4}-\d{2}-\d{2})</code> - Matches "1901-06-06"<br/>
              • <code>(\w+\s+\d+,\s*\d{4})</code> - Matches "June 6, 1901"
            </small>

            <div v-if="source.custom_date_pattern && !regexValidation.tested" class="warning-message">
              ⚠️ Please validate your pattern before proceeding
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4: Document Preview -->
      <div v-if="currentStep === 4" class="wizard-step">
        <h2>Preview Documents</h2>

        <div v-if="!previewData" class="preview-loading">
          <div class="preview-settings">
            <h3>Current Settings</h3>
            <ul>
              <li><strong>Source Type:</strong> {{ source.type }}</li>
              <li><strong>Location:</strong> {{ source.location || '(not specified)' }}</li>
              <li><strong>File Extensions:</strong> {{ source.file_extensions }}</li>
              <li><strong>Include Subdirectories:</strong> {{ source.include_subdirectories ? 'Yes' : 'No' }}</li>
              <li><strong>Extract URLs:</strong> {{ source.extract_inline_urls ? 'Yes' : 'No' }}</li>
              <li><strong>Date Pattern:</strong> {{ source.date_pattern || 'None' }}</li>
            </ul>
          </div>
          <button @click="loadPreview" :disabled="loadingPreview || !source.location" class="btn btn-primary">
            {{ loadingPreview ? 'Loading Preview...' : 'Load Document Preview' }}
          </button>
          <p v-if="!source.location" class="error-text">Please specify a source location in the previous step.</p>
        </div>

        <div v-if="previewData" class="preview-section">
          <div class="preview-summary">
            <h3>Discovery Summary</h3>
            <div class="summary-stats">
              <div class="stat-item">
                <span class="stat-label">Total Documents:</span>
                <span class="stat-value">{{ previewData.total_documents }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Total Size:</span>
                <span class="stat-value">{{ formatBytes(previewData.total_size) }}</span>
              </div>
              <div v-if="source.extract_inline_urls" class="stat-item">
                <span class="stat-label">Documents with URLs:</span>
                <span class="stat-value">{{ previewData.docs_with_urls }}</span>
              </div>
              <div v-if="source.date_pattern" class="stat-item">
                <span class="stat-label">Documents with Dates:</span>
                <span class="stat-value">{{ previewData.docs_with_dates }}</span>
              </div>
            </div>
          </div>

          <div class="preview-samples">
            <h3>Sample Documents</h3>
            <p class="help-text">Review these samples to verify your extraction settings are correct.</p>

            <div v-for="(doc, index) in previewData.samples" :key="index" class="sample-document">
              <div class="doc-header">
                <span class="doc-name">{{ doc.filename }}</span>
                <span class="doc-size">{{ formatBytes(doc.size) }}</span>
              </div>

              <div v-if="doc.extracted_metadata" class="doc-metadata">
                <div v-if="doc.extracted_metadata.url" class="metadata-item">
                  <span class="metadata-label">URL:</span>
                  <span class="metadata-value">{{ doc.extracted_metadata.url }}</span>
                </div>
                <div v-if="doc.extracted_metadata.date" class="metadata-item">
                  <span class="metadata-label">Date:</span>
                  <span class="metadata-value">{{ doc.extracted_metadata.date }}</span>
                </div>
              </div>

              <div class="doc-content">
                <pre>{{ doc.preview }}</pre>
              </div>
            </div>
          </div>

          <div v-if="previewData.filters && previewData.filters.length > 0" class="preview-filters">
            <h3>Discovered Filters</h3>
            <p class="help-text">These filters were discovered from your directory structure and will be available for corpus searches.</p>

            <div class="filter-grid">
              <div v-for="filter in previewData.filters" :key="filter.id"
                   :class="['filter-card', { 'filter-all': filter.type === 'all' }]">
                <div class="filter-header">
                  <input
                    type="checkbox"
                    :id="'filter-' + filter.id"
                    :checked="filter.type === 'all' || selectedFilters.includes(filter.id)"
                    @change="toggleFilter(filter.id)"
                    :disabled="filter.type === 'all'"
                  />
                  <label :for="'filter-' + filter.id" class="filter-label">
                    {{ filter.label }}
                  </label>
                </div>
                <div class="filter-details">
                  <span class="filter-type">{{ filter.type === 'all' ? 'Default' : 'Directory' }}</span>
                  <span class="filter-count">{{ filter.document_count }} docs</span>
                </div>
                <div v-if="filter.path" class="filter-path">
                  Path: {{ filter.path }}
                </div>
              </div>
            </div>
          </div>

          <div v-if="previewData.warnings && previewData.warnings.length > 0" class="preview-warnings">
            <h3>⚠️ Warnings</h3>
            <ul>
              <li v-for="warning in previewData.warnings" :key="warning">{{ warning }}</li>
            </ul>
          </div>

          <div class="preview-actions">
            <button @click="loadPreview" class="btn btn-secondary">Refresh Preview</button>
          </div>
        </div>
      </div>

      <!-- Step 5: Model Selection -->
      <div v-if="currentStep === 5" class="wizard-step">
        <h2>Select Embedding Model</h2>
        <p class="help-text">Choose an embedding model for creating vector representations of your documents.</p>

        <div class="model-selection">
          <div class="model-choice">
            <label class="radio-option">
              <input
                type="radio"
                v-model="modelChoice"
                value="default"
                @change="selectedModel = defaultModel"
              />
              <span class="radio-label">Default Model (Recommended)</span>
            </label>
            <div v-if="modelChoice === 'default'" class="model-details">
              <p><strong>{{ defaultModel }}</strong></p>
              <p class="model-description">
                A well-balanced, general-purpose embedding model.
                Fast processing with good accuracy for most use cases.
              </p>
              <ul class="model-specs">
                <li>Dimensions: 384</li>
                <li>Size: ~90MB</li>
                <li>Speed: Fast</li>
              </ul>
            </div>
          </div>

          <div class="model-choice">
            <label class="radio-option">
              <input
                type="radio"
                v-model="modelChoice"
                value="custom"
              />
              <span class="radio-label">Custom Hugging Face Model</span>
            </label>
            <div v-if="modelChoice === 'custom'" class="custom-model-input">
              <input
                v-model="customModel"
                type="text"
                placeholder="e.g., sentence-transformers/all-mpnet-base-v2"
                class="form-control"
                @input="selectedModel = customModel"
              />
              <p class="help-text">
                Enter a Hugging Face model ID. The model will be downloaded if not already available.
              </p>
            </div>
          </div>
        </div>

        <div class="chunk-settings">
          <h3>Document Chunking Settings</h3>
          <p class="help-text">Configure how documents are split into chunks for embedding.</p>

          <div class="form-row">
            <div class="form-group">
              <label>Chunk Size (characters)</label>
              <input
                v-model.number="chunkSize"
                type="number"
                min="100"
                max="5000"
                step="100"
                class="form-control"
              />
              <small>Default: 1000 characters</small>
            </div>

            <div class="form-group">
              <label>Chunk Overlap (characters)</label>
              <input
                v-model.number="chunkOverlap"
                type="number"
                min="0"
                max="500"
                step="50"
                class="form-control"
              />
              <small>Default: 200 characters</small>
            </div>
          </div>
        </div>
      </div>


      <!-- Step 6: Build Progress -->
      <div v-if="currentStep === 6" class="wizard-step">
        <h2>Building Vector Store</h2>

        <div v-if="!building && !buildProgress.status" class="build-start">
          <p>Ready to build your corpus vector store.</p>
          <button @click="startBuild" :disabled="building" class="btn btn-success">
            {{ building ? 'Starting...' : 'Start Build' }}
          </button>
        </div>

        <div v-if="building || buildProgress.status" class="build-in-progress">
          <div class="progress-bar-container">
            <div class="progress-bar" :style="{ width: (buildProgress.percentage || 0) + '%' }">
              {{ Math.round(buildProgress.percentage || 0) }}%
            </div>
          </div>

          <div class="build-stats">
            <div class="stat-row">
              <span>Documents Processed:</span>
              <span>{{ buildProgress.processed_documents || 0 }} / {{ buildProgress.total_documents || '?' }}</span>
            </div>
            <div class="stat-row">
              <span>Current Document:</span>
              <span>{{ buildProgress.current_document || 'Initializing...' }}</span>
            </div>
            <div class="stat-row">
              <span>Elapsed Time:</span>
              <span>{{ formatDuration(buildProgress.elapsed_seconds) }}</span>
            </div>
            <div v-if="buildProgress.estimated_remaining" class="stat-row">
              <span>Estimated Remaining:</span>
              <span>{{ formatDuration(buildProgress.estimated_remaining) }}</span>
            </div>
          </div>

          <div v-if="buildProgress.errors && buildProgress.errors.length > 0" class="build-errors">
            <h3>⚠️ Errors</h3>
            <ul>
              <li v-for="error in buildProgress.errors" :key="error.document">
                {{ error.document }}: {{ error.message }}
              </li>
            </ul>
          </div>

          <div v-if="buildLogs && buildLogs.length > 0" class="build-logs">
            <h3>Build Log</h3>
            <div class="log-container">
              <div v-for="(log, index) in buildLogs.slice(-10)" :key="index" class="log-entry">
                <span class="log-time">{{ formatTime(log.timestamp) }}</span>
                <span :class="'log-' + log.level">{{ log.message }}</span>
              </div>
            </div>
          </div>

          <div v-if="buildProgress.status === 'completed'" class="build-complete">
            <div class="success-message">
              ✅ Build completed successfully!
            </div>
            <button @click="() => currentStep++" class="btn btn-primary">
              Continue to Activation
            </button>
          </div>

          <div v-if="buildProgress.status === 'failed'" class="build-failed">
            <div class="error-message">
              ❌ Build failed: {{ buildProgress.error }}
            </div>
            <button @click="retryBuild" class="btn btn-secondary">
              Retry Build
            </button>
          </div>
        </div>
      </div>

      <!-- Step 7: Test & Activate -->
      <div v-if="currentStep === 7" class="wizard-step">
        <h2>Test & Activate Corpus</h2>

        <div class="activation-content">
          <!-- Pre-activation Check -->
          <div v-if="!validationComplete" class="validation-section">
            <h3>Pre-activation Validation</h3>
            <p>Validating your new corpus before activation...</p>

            <div v-if="!validationData" class="validation-loading">
              <button @click="runValidation" :disabled="validating" class="btn btn-primary">
                {{ validating ? 'Validating...' : 'Run Validation' }}
              </button>
            </div>

            <div v-if="validationData" class="validation-results">
              <div class="validation-item" :class="{ success: validationData.structure_valid }">
                <span>✓</span> Vector store structure
              </div>
              <div class="validation-item" :class="{ success: validationData.metadata_valid }">
                <span>✓</span> Metadata integrity
              </div>
              <div class="validation-item" :class="{ success: validationData.search_functional }">
                <span>✓</span> Search functionality
              </div>

              <div v-if="validationData.all_valid" class="validation-success">
                ✅ All validation checks passed!
              </div>
            </div>
          </div>

          <!-- Test Search -->
          <div v-if="validationData && validationData.all_valid" class="test-section">
            <h3>Test Your Corpus</h3>
            <p>Run a test search to verify the corpus is working correctly.</p>

            <div class="test-search-form">
              <input
                v-model="testQuery"
                type="text"
                placeholder="Enter a test query..."
                class="form-control"
                @keyup.enter="runTestSearch"
              />
              <button @click="runTestSearch" :disabled="testing" class="btn btn-primary">
                {{ testing ? 'Searching...' : 'Test Search' }}
              </button>
            </div>

            <div v-if="testResults" class="test-results">
              <h4>Search Results ({{ testResults.length }} documents found)</h4>
              <div v-for="(result, index) in testResults.slice(0, 3)" :key="index" class="test-result">
                <div class="result-header">
                  <span class="result-number">{{ index + 1 }}.</span>
                  <span class="result-score">Score: {{ result.score.toFixed(3) }}</span>
                </div>
                <div class="result-content">{{ result.excerpt }}</div>
                <div v-if="result.metadata" class="result-metadata">
                  <span v-if="result.metadata.source">Source: {{ result.metadata.source }}</span>
                  <span v-if="result.metadata.date">Date: {{ result.metadata.date }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Corpus Comparison -->
          <div v-if="validationData && validationData.all_valid" class="comparison-section">
            <h3>Corpus Comparison</h3>
            <table class="comparison-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Current Corpus</th>
                  <th>New Corpus</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Documents</td>
                  <td>{{ currentCorpusInfo?.document_count || 'N/A' }}</td>
                  <td>{{ buildProgress.processed_documents }}</td>
                </tr>
                <tr>
                  <td>Vector Store Size</td>
                  <td>{{ formatBytes(currentCorpusInfo?.size) || 'N/A' }}</td>
                  <td>{{ formatBytes(buildResults?.vector_store_size) }}</td>
                </tr>
                <tr>
                  <td>Model</td>
                  <td>{{ currentCorpusInfo?.model || 'N/A' }}</td>
                  <td>{{ selectedModel }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Activation -->
          <div v-if="validationData && validationData.all_valid" class="activation-section">
            <h3>Ready to Activate?</h3>
            <div class="activation-warning">
              <p>⚠️ <strong>Important:</strong></p>
              <ul>
                <li>Your current corpus will be backed up</li>
                <li>The new corpus will become active immediately</li>
                <li>To rollback: <code>make restore-corpus BACKUP_ID={{ backupId }}</code></li>
              </ul>
            </div>

            <div class="activation-buttons">
              <button @click="activateCorpus" :disabled="activating" class="btn btn-success">
                {{ activating ? 'Activating...' : 'Activate Corpus' }}
              </button>
              <button @click="saveConfiguration" class="btn btn-secondary">
                Save Configuration Only
              </button>
              <button @click="downloadConfig" class="btn btn-secondary">
                Download Configuration
              </button>
            </div>

            <div v-if="activationResult" class="activation-result">
              <div v-if="activationResult.success" class="success-message">
                ✅ Corpus activated successfully!
                <p>Backup saved as: {{ activationResult.backup_id }}</p>
              </div>
              <div v-else class="error-message">
                ❌ Activation failed: {{ activationResult.error }}
              </div>
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
        v-if="currentStep < steps.length && currentStep !== 6"
        @click="nextStep"
        :disabled="!canProceed"
        class="btn btn-primary"
      >
        Next
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import BuildProgress from '@/components/wizard/BuildProgress.vue'

export default {
  name: 'CorpusWizard',
  components: {
    BuildProgress
  },
  setup() {
    // Wizard state
    const currentStep = ref(1)
    const steps = [
      'Workflow',
      'Metadata',
      'Sources',
      'Preview',
      'Model',
      'Build',
      'Activate'
    ]

    // Workflow type
    const workflowType = ref('text')

    // Form data
    const metadata = ref({
      name: '',
      description: '',
      copyright_status: '',
      doi: ''
    })

    const source = ref({
      type: 'local',
      location: 'backend/corpus/sources',  // Default to the corpus sources directory
      branch: 'main',
      path: '',
      file_extensions: '.txt',
      include_subdirectories: true,
      extract_inline_urls: false,
      date_pattern: '',
      custom_date_pattern: ''
    })

    // Model selection
    const defaultModel = ref('sentence-transformers/all-MiniLM-L6-v2')
    const modelChoice = ref('default')
    const selectedModel = ref(defaultModel.value)
    const customModel = ref('')
    const chunkSize = ref(1000)
    const chunkOverlap = ref(200)

    // Preview
    const previewData = ref(null)
    const loadingPreview = ref(false)
    const selectedFilters = ref([])

    // Regex validation
    const regexValidation = ref({
      tested: false,
      valid: false,
      error: null,
      matches: []
    })

    // Build
    const building = ref(false)
    const buildProgress = ref({})
    const buildLogs = ref([])
    const buildId = ref(null)
    const buildResults = ref(null)

    // Validation & Activation
    const validationData = ref(null)
    const validationComplete = ref(false)
    const validating = ref(false)
    const testQuery = ref('')
    const testResults = ref(null)
    const testing = ref(false)
    const currentCorpusInfo = ref(null)
    const activating = ref(false)
    const activationResult = ref(null)
    const backupId = ref(null)

    // SSE connection for build progress
    let eventSource = null

    // Check if can proceed to next step
    const canProceed = computed(() => {
      switch (currentStep.value) {
        case 1: // Workflow
          return workflowType.value === 'text' // Only text workflow is available
        case 2: // Metadata
          return metadata.value.name &&
                 metadata.value.name.length > 0 &&
                 metadata.value.copyright_status
        case 3: // Sources
          return source.value.location &&
                 source.value.location.length > 0 &&
                 source.value.file_extensions
        case 4: // Preview
          return previewData.value && previewData.value.total_documents > 0
        case 5: // Model
          return selectedModel.value && selectedModel.value.length > 0
        case 6: // Build
          return buildProgress.value.status === 'completed'
        case 7: // Activate
          return validationData.value && validationData.value.all_valid
        default:
          return true
      }
    })

    // Navigation
    const nextStep = async () => {
      if (canProceed.value && currentStep.value < steps.length) {
        currentStep.value++

        // Perform step-specific actions AFTER incrementing step
        if (currentStep.value === 4) {
          // Entering Preview step - can load preview if not already loaded
          if (!previewData.value) {
            // User can manually click to load preview
          }
        } else if (currentStep.value === 7) {
          // Entering Activation step - get current corpus info
          await loadCurrentCorpusInfo()
        }
      }
    }

    const previousStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--
      }
    }

    // Regex validation methods
    const validateRegexPattern = async () => {
      if (!source.value.custom_date_pattern) {
        return
      }

      // Get a sample filename for testing
      const sampleFilename = "Friday, 02 August, 1901.txt"

      try {
        const response = await fetch('/api/corpus-wizard/validate-regex', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pattern: source.value.custom_date_pattern,
            test_string: sampleFilename
          })
        })

        const data = await response.json()

        regexValidation.value = {
          tested: true,
          valid: data.valid,
          error: data.error || null,
          matches: data.matches || []
        }
      } catch (error) {
        regexValidation.value = {
          tested: true,
          valid: false,
          error: error.message,
          matches: []
        }
      }
    }

    const clearRegexValidation = () => {
      regexValidation.value = {
        tested: false,
        valid: false,
        error: null,
        matches: []
      }
    }

    // Preview methods
    const loadPreview = async () => {
      console.log('loadPreview called')
      console.log('Current source value:', source.value)
      console.log('Current metadata value:', metadata.value)

      // Validate that we have a source location
      if (!source.value.location) {
        alert('Please specify a source location in the previous step')
        return
      }

      // Check if custom regex pattern needs validation
      if (source.value.date_pattern === 'custom' && source.value.custom_date_pattern && !regexValidation.value.tested) {
        alert('Please validate your custom regex pattern before proceeding')
        return
      }

      // Check if custom regex pattern is invalid
      if (source.value.date_pattern === 'custom' && regexValidation.value.tested && !regexValidation.value.valid) {
        alert('Please fix your invalid regex pattern before proceeding')
        return
      }

      loadingPreview.value = true
      try {
        // Ensure source has all required fields
        const sourceData = {
          ...source.value,
          file_extensions: source.value.file_extensions || '.txt',
          include_subdirectories: source.value.include_subdirectories !== undefined ? source.value.include_subdirectories : true
        }

        console.log('Sending preview request with source:', sourceData)

        const response = await fetch('/api/corpus-wizard/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source: sourceData,
            metadata: metadata.value
          })
        })

        console.log('Response status:', response.status)

        if (!response.ok) {
          const errorText = await response.text()
          console.error('Error response:', errorText)
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }

        const data = await response.json()
        console.log('Preview data received:', data)

        // Check if we have an error in the response
        if (data.error) {
          throw new Error(data.error)
        }

        previewData.value = data

        // Auto-select all non-'all' filters by default
        if (previewData.value.filters) {
          selectedFilters.value = previewData.value.filters
            .filter(f => f.type !== 'all')
            .map(f => f.id)
        }
      } catch (error) {
        console.error('Failed to load preview:', error)
        alert('Failed to load document preview: ' + error.message)
      } finally {
        loadingPreview.value = false
      }
    }

    const toggleFilter = (filterId) => {
      const index = selectedFilters.value.indexOf(filterId)
      if (index > -1) {
        selectedFilters.value.splice(index, 1)
      } else {
        selectedFilters.value.push(filterId)
      }
    }

    const formatBytes = (bytes) => {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    const formatTime = (timestamp) => {
      const date = new Date(timestamp)
      return date.toLocaleTimeString()
    }

    // Validation methods
    const runValidation = async () => {
      validating.value = true
      try {
        const response = await fetch(`/api/corpus-wizard/validate/${buildId.value}`, {
          method: 'POST'
        })
        validationData.value = await response.json()
        validationComplete.value = validationData.value.all_valid
      } catch (error) {
        console.error('Validation failed:', error)
        alert('Failed to validate corpus: ' + error.message)
      } finally {
        validating.value = false
      }
    }

    const loadCurrentCorpusInfo = async () => {
      try {
        const response = await fetch('/api/corpus-wizard/current-corpus')
        currentCorpusInfo.value = await response.json()
      } catch (error) {
        console.error('Failed to load current corpus info:', error)
      }
    }

    const downloadConfig = () => {
      const config = {
        metadata: metadata.value,
        source: source.value,
        model: {
          type: modelChoice.value,
          model: selectedModel.value,
          chunk_size: chunkSize.value,
          chunk_overlap: chunkOverlap.value
        }
      }

      const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `corpus-config-${metadata.value.name.toLowerCase().replace(/\s+/g, '-')}.json`
      a.click()
      URL.revokeObjectURL(url)
    }

    const retryBuild = () => {
      buildProgress.value = {}
      buildResults.value = null
      startBuild()
    }

    const startBuild = async () => {
      building.value = true

      try {
        // Prepare configuration
        const config = {
          metadata: {
            ...metadata.value,
            workflow_type: workflowType.value,
            created_by: 'corpus_wizard'
          },
          source: source.value,
          filters: previewData.value?.filters?.filter(f =>
            f.type === 'all' || selectedFilters.value.includes(f.id)
          ) || [],
          embeddings: {
            model: selectedModel.value,
            pooling: 'mean',
            chunk_size: chunkSize.value,
            chunk_overlap: chunkOverlap.value,
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
            mode: 'cpu' // Default to CPU mode
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

    const runTestSearch = async () => {
      testing.value = true
      try {
        const response = await fetch('/api/corpus-wizard/test-search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            build_id: buildId.value,
            query: testQuery.value,
            limit: 5
          })
        })
        const data = await response.json()
        testResults.value = data.results.map(r => ({
          excerpt: r.content.substring(0, 200) + '...',
          score: r.score,
          metadata: r.metadata
        }))
      } catch (error) {
        console.error('Test search failed:', error)
        alert('Failed to run test search: ' + error.message)
      } finally {
        testing.value = false
      }
    }

    const activateCorpus = async () => {
      activating.value = true
      try {
        const response = await fetch('/api/corpus-wizard/activate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            build_id: buildId.value,
            corpus_name: metadata.value.name
          })
        })
        const result = await response.json()
        activationResult.value = result
        if (result.success) {
          backupId.value = result.backup_id
        }
      } catch (error) {
        console.error('Failed to activate corpus:', error)
        activationResult.value = {
          success: false,
          error: error.message
        }
      } finally {
        activating.value = false
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
      // Wizard state
      currentStep,
      steps,
      workflowType,

      // Form data
      metadata,
      source,

      // Model selection
      defaultModel,
      modelChoice,
      selectedModel,
      customModel,
      chunkSize,
      chunkOverlap,

      // Preview
      previewData,
      loadingPreview,
      loadPreview,
      selectedFilters,
      toggleFilter,

      // Regex validation
      regexValidation,
      validateRegexPattern,
      clearRegexValidation,

      // Build
      building,
      buildProgress,
      buildLogs,
      buildResults,
      startBuild,
      retryBuild,

      // Validation & Activation
      validationData,
      validationComplete,
      validating,
      runValidation,
      testQuery,
      testResults,
      testing,
      runTestSearch,
      currentCorpusInfo,
      activating,
      activationResult,
      backupId,
      activateCorpus,

      // Navigation
      canProceed,
      nextStep,
      previousStep,

      // Utilities
      saveConfiguration,
      downloadConfig,
      formatDuration,
      formatBytes,
      formatTime
    }
  }
}
</script>

<style scoped>
.corpus-wizard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  font-family: "Times New Roman", Times, serif;
}

.wizard-header {
  text-align: center;
  margin-bottom: 3rem;
}

.wizard-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  color: #181818;
  font-weight: 800;
  letter-spacing: -0.5px;
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
  background: #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 0.5rem;
  color: #666;
  border: 1px solid #ddd;
}

.step.active .step-number {
  background: #000;
  color: #fff;
  border-color: #000;
}

.step.completed .step-number {
  background: #181818;
  color: #fff;
  border-color: #181818;
}

.step-label {
  font-size: 0.9rem;
  color: #181818;
}

/* Form Elements */
.wizard-content {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 2rem;
  min-height: 400px;
}

.wizard-step h2 {
  margin-bottom: 1.5rem;
  color: #181818;
  font-weight: 700;
  font-size: 1.8rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #181818;
  font-size: 0.97em;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  font-family: "Times New Roman", Times, serif;
  background: #fff;
  color: #181818;
}

.form-control:focus {
  outline: none;
  border-color: #181818;
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
  flex-wrap: wrap;
}

.checkbox {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #181818;
}

.checkbox input {
  margin-right: 0.5rem;
  cursor: pointer;
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
  border: 2px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
  background: #fff;
}

.source-option:hover {
  border-color: #181818;
}

.source-option.active {
  border-color: #181818;
  background: #f8f9fa;
}

.source-option .icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.source-option h3 {
  margin: 0.5rem 0;
  color: #181818;
  font-weight: 600;
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
  color: #181818;
  font-weight: 600;
}

.hardware-info {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
  color: #181818;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  font-weight: 600;
}

.info-item .warning {
  color: #666;
  font-style: italic;
}

.processing-modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.mode-option {
  padding: 1.5rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  background: #fff;
}

.mode-option:hover {
  border-color: #181818;
}

.mode-option.active {
  border-color: #181818;
  background: #f8f9fa;
}

.mode-option.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-option.recommended {
  border-color: #181818;
}

.mode-option h4 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
}

.mode-option p {
  color: #666;
  margin: 0.5rem 0;
}

.badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: #181818;
  color: #fff;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}

/* Warnings */
.warnings {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 1rem;
}

.warnings h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
}

.warning-item {
  padding: 0.5rem 0;
  color: #666;
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
  transition: all 0.2s;
  font-family: "Times New Roman", Times, serif;
  font-weight: 500;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #000;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #888;
}

.btn-secondary {
  background: #666;
  color: #fff;
}

.btn-secondary:hover {
  background: #888;
}

.btn-success {
  background: #000;
  color: #fff;
}

.btn-success:hover:not(:disabled) {
  background: #888;
}

/* Form Actions */
.form-actions {
  margin-top: 1.5rem;
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
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.analysis-result h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
}

.analysis-result h4 {
  color: #181818;
  font-weight: 600;
  margin-top: 1rem;
}

.analysis-result p {
  color: #181818;
}

.analysis-result ul {
  list-style: none;
  padding: 0;
}

.analysis-result li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
  color: #181818;
}

.analysis-result li:last-child {
  border-bottom: none;
}

/* Filter Configuration */
.filter-config {
  padding: 1rem;
}

.help-text {
  color: #666;
  margin-bottom: 1.5rem;
}

/* Regex Validation Styles */
.regex-input-group {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
}

.regex-input-group .form-control {
  flex: 1;
}

.regex-input-group .btn {
  flex-shrink: 0;
  white-space: nowrap;
}

.validation-feedback {
  margin-top: 0.5rem;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.validation-feedback .success-message {
  color: #155724;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  padding: 0.5rem;
  border-radius: 4px;
}

.validation-feedback .error-message {
  color: #721c24;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  padding: 0.5rem;
  border-radius: 4px;
}

.form-control.is-invalid {
  border-color: #dc3545;
  background-color: #fff5f5;
}

.warning-message {
  color: #856404;
  background-color: #fff3cd;
  border: 1px solid #ffeeba;
  padding: 0.5rem;
  border-radius: 4px;
  margin-top: 0.5rem;
}

.help-text code {
  background-color: #f4f4f4;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: monospace;
  color: #333;
}

.filter-list {
  margin-bottom: 1.5rem;
}

.filter-item {
  background: #fff;
  border: 1px solid #ddd;
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
  border: 1px solid #ddd;
  border-radius: 4px;
  font-weight: 600;
  font-family: "Times New Roman", Times, serif;
  color: #181818;
}

.btn-remove {
  background: #181818;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  font-size: 1.25rem;
  cursor: pointer;
  margin-left: 1rem;
  transition: background 0.2s;
}

.btn-remove:hover {
  background: #888;
}

.filter-details {
  display: flex;
  gap: 1rem;
  font-size: 0.9rem;
  color: #666;
}

/* Model Selection */
.model-selection {
  display: grid;
  gap: 1rem;
}

.model-option {
  padding: 1.5rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: #fff;
}

.model-option:hover {
  border-color: #181818;
}

.model-option.active {
  border-color: #181818;
  background: #f8f9fa;
}

.model-option.recommended {
  border-color: #181818;
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.model-header h4 {
  margin: 0;
  color: #181818;
  font-weight: 600;
}

.model-reason {
  margin-bottom: 0.5rem;
  color: #666;
}

.model-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.9rem;
  color: #666;
}

.custom-model-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #ddd;
}

.custom-model-section h4 {
  color: #181818;
  font-weight: 600;
  margin-bottom: 1rem;
}

/* Completion & Activation */
.completion-section {
  padding: 2rem;
}

.success-message {
  background: #f8f9fa;
  color: #181818;
  border: 1px solid #ddd;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  text-align: center;
  font-size: 1.25rem;
  font-weight: bold;
}

.build-summary {
  background: #f8f9fa;
  border: 1px solid #ddd;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.build-summary h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
}

.build-summary ul {
  list-style: none;
  padding: 0;
}

.build-summary li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
  color: #181818;
}

.build-summary li:last-child {
  border-bottom: none;
}

.test-section {
  background: #f8f9fa;
  border: 1px solid #ddd;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.test-section h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
}

.test-section .form-control {
  margin-bottom: 1rem;
}

.test-results {
  margin-top: 1rem;
  padding: 1rem;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.test-results h4 {
  color: #181818;
  font-weight: 600;
  margin-top: 0;
}

.test-result {
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
  color: #181818;
}

.test-result:last-child {
  border-bottom: none;
}

.activation-section {
  background: #f8f9fa;
  border: 1px solid #ddd;
  padding: 1.5rem;
  border-radius: 8px;
}

.activation-section h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
}

.activation-section p {
  color: #666;
  margin-bottom: 1rem;
}

.activation-section .btn {
  margin-right: 1rem;
}

/* Workflow Selection */
.workflow-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-top: 2rem;
}

.workflow-option {
  padding: 1.5rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
  background: #fff;
  position: relative;
}

.workflow-option:hover:not(.disabled) {
  border-color: #181818;
}

.workflow-option.active {
  border-color: #181818;
  background: #f8f9fa;
}

.workflow-option.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.workflow-option .icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  display: block;
}

.workflow-option h3 {
  margin: 0.5rem 0;
  color: #181818;
  font-weight: 600;
}

.workflow-option p {
  color: #666;
  margin: 0.5rem 0;
}

.workflow-option ul {
  text-align: left;
  margin: 1rem 0;
  padding-left: 1.5rem;
}

.workflow-option ul li {
  color: #666;
  margin: 0.5rem 0;
}

.coming-soon {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: #666;
  color: #fff;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

/* Processing Options */
.processing-options {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.processing-options h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
  margin-bottom: 1rem;
}

/* Model Selection */
.model-choice {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.radio-option {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-weight: 600;
  color: #181818;
}

.radio-option input[type="radio"] {
  margin-right: 0.75rem;
}

.radio-label {
  font-size: 1.1rem;
}

.model-details {
  margin-top: 1rem;
  padding-left: 1.75rem;
}

.model-description {
  color: #666;
  margin: 0.5rem 0;
}

.model-specs {
  list-style: none;
  padding: 0;
  margin-top: 1rem;
}

.model-specs li {
  padding: 0.25rem 0;
  color: #666;
}

.custom-model-input {
  margin-top: 1rem;
  padding-left: 1.75rem;
}

.chunk-settings {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.chunk-settings h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.chunk-settings small {
  color: #666;
  display: block;
  margin-top: 0.25rem;
}

/* Preview Section */
.preview-loading {
  text-align: center;
  padding: 3rem;
}

.preview-settings {
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  text-align: left;
}

.preview-settings h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
  margin-bottom: 1rem;
}

.preview-settings ul {
  list-style: none;
  padding: 0;
}

.preview-settings li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
  color: #666;
}

.preview-settings li:last-child {
  border-bottom: none;
}

.preview-settings strong {
  color: #181818;
  margin-right: 0.5rem;
}

.error-text {
  color: #dc3545;
  margin-top: 1rem;
  font-weight: 500;
}

.preview-section {
  display: grid;
  gap: 2rem;
}

.preview-summary {
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}

.stat-label {
  font-weight: 600;
  color: #666;
}

.stat-value {
  color: #181818;
  font-weight: 600;
}

.preview-samples {
  background: #fff;
}

.sample-document {
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.doc-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #ddd;
}

.doc-name {
  font-weight: 600;
  color: #181818;
}

.doc-size {
  color: #666;
}

.doc-metadata {
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #fff;
  border-radius: 4px;
}

.metadata-item {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.metadata-label {
  font-weight: 600;
  color: #666;
}

.metadata-value {
  color: #181818;
}

.doc-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: monospace;
  font-size: 0.9rem;
  color: #666;
  margin: 0;
  max-height: 200px;
  overflow-y: auto;
}

.preview-warnings {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 1rem;
}

.preview-warnings h3 {
  margin-top: 0;
  color: #856404;
}

.preview-warnings ul {
  margin: 0;
  padding-left: 1.5rem;
}

.preview-warnings li {
  color: #856404;
  margin: 0.5rem 0;
}

/* Filter Discovery */
.preview-filters {
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.preview-filters h3 {
  margin-top: 0;
  color: #181818;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.filter-card {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 1rem;
  transition: all 0.2s;
}

.filter-card:hover {
  border-color: #181818;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.filter-card.filter-all {
  background: #e8f4f8;
  border-color: #181818;
}

.filter-header {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
}

.filter-header input[type="checkbox"] {
  margin-right: 0.5rem;
}

.filter-label {
  font-weight: 600;
  color: #181818;
  cursor: pointer;
  flex: 1;
}

.filter-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.filter-type {
  color: #666;
  padding: 0.125rem 0.5rem;
  background: #f0f0f0;
  border-radius: 3px;
  font-size: 0.8rem;
}

.filter-count {
  color: #181818;
  font-weight: 500;
}

.filter-path {
  font-size: 0.85rem;
  color: #666;
  font-family: monospace;
  margin-top: 0.25rem;
  padding-top: 0.5rem;
  border-top: 1px solid #eee;
}

/* Build Progress */
.build-start {
  text-align: center;
  padding: 3rem;
}

.build-in-progress {
  padding: 1.5rem;
}

.progress-bar-container {
  background: #eee;
  border-radius: 8px;
  overflow: hidden;
  height: 40px;
  margin-bottom: 2rem;
  position: relative;
}

.progress-bar {
  background: #181818;
  height: 100%;
  transition: width 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
}

.build-stats {
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}

.stat-row:last-child {
  border-bottom: none;
}

.build-errors {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.build-errors h3 {
  margin-top: 0;
  color: #721c24;
}

.build-errors ul {
  margin: 0;
  padding-left: 1.5rem;
}

.build-errors li {
  color: #721c24;
  margin: 0.5rem 0;
}

.build-logs {
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.build-logs h3 {
  margin-top: 0;
  color: #181818;
}

.log-container {
  background: #fff;
  border-radius: 4px;
  padding: 0.75rem;
  max-height: 300px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 0.9rem;
}

.log-entry {
  margin-bottom: 0.25rem;
  display: flex;
  gap: 1rem;
}

.log-time {
  color: #666;
  flex-shrink: 0;
}

.log-info {
  color: #181818;
}

.log-warning {
  color: #856404;
}

.log-error {
  color: #721c24;
}

.build-complete,
.build-failed {
  text-align: center;
  padding: 2rem;
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-weight: 600;
}

/* Validation */
.validation-section {
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.validation-loading {
  text-align: center;
  padding: 2rem;
}

.validation-results {
  margin-top: 1.5rem;
}

.validation-item {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  color: #666;
}

.validation-item.success {
  border-color: #28a745;
  color: #155724;
  background: #d4edda;
}

.validation-success {
  margin-top: 1rem;
  padding: 1rem;
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
  border-radius: 8px;
  text-align: center;
  font-weight: 600;
}

/* Test Search */
.test-search-form {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.test-search-form .form-control {
  flex: 1;
}

.result-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.result-number {
  color: #181818;
}

.result-score {
  color: #666;
  font-size: 0.9rem;
}

.result-content {
  color: #666;
  margin-bottom: 0.5rem;
}

.result-metadata {
  font-size: 0.9rem;
  color: #666;
  display: flex;
  gap: 1rem;
}

/* Comparison Table */
.comparison-section {
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.comparison-table th,
.comparison-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.comparison-table th {
  background: #fff;
  font-weight: 600;
  color: #181818;
}

.comparison-table td {
  color: #666;
}

/* Activation */
.activation-warning {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.activation-warning p {
  margin-bottom: 0.5rem;
  color: #856404;
}

.activation-warning ul {
  margin: 0;
  padding-left: 1.5rem;
}

.activation-warning li {
  color: #856404;
  margin: 0.5rem 0;
}

.activation-warning code {
  background: #fff;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: monospace;
}

.activation-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.activation-result {
  margin-top: 1.5rem;
}

.activation-result .success-message {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
  padding: 1rem;
  border-radius: 8px;
}

.activation-result .error-message {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  padding: 1rem;
  border-radius: 8px;
}
</style>