<template>
  <div class="validation-preview">
    <h2>Validation Results</h2>
    <p class="form-description">Review the validation results from your corpus sample</p>

    <div class="validation-summary">
      <div class="summary-card" :class="validationStatus">
        <div class="status-icon">
          <span v-if="validationResults?.valid">✅</span>
          <span v-else>⚠️</span>
        </div>
        <div class="status-content">
          <h3>{{ validationResults?.valid ? 'Validation Passed' : 'Issues Detected' }}</h3>
          <p>{{ validationSummaryText }}</p>
        </div>
      </div>
    </div>

    <div class="validation-sections">
      <!-- Sample Information -->
      <div class="section-card">
        <h3>Sample Information</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">Total Files:</span>
            <span class="value">{{ sampleData?.total_files || 0 }}</span>
          </div>
          <div class="info-item">
            <span class="label">Sample Size:</span>
            <span class="value">{{ sampleData?.sample_size || 0 }}</span>
          </div>
          <div class="info-item">
            <span class="label">Sampling Method:</span>
            <span class="value">{{ sampleData?.sampling_method || 'Unknown' }}</span>
          </div>
          <div class="info-item">
            <span class="label">Coverage:</span>
            <span class="value">{{ sampleCoverage }}%</span>
          </div>
        </div>
      </div>

      <!-- Filter Coverage -->
      <div class="section-card">
        <h3>Filter Coverage Analysis</h3>
        <div v-if="filterCoverage">
          <div class="coverage-stats">
            <div class="stat">
              <span class="label">Total Filters:</span>
              <span class="value">{{ filterCoverage.total_filters }}</span>
            </div>
            <div class="stat">
              <span class="label">Filters with Matches:</span>
              <span class="value">{{ filterCoverage.filters_with_matches }}</span>
            </div>
            <div class="stat">
              <span class="label">Coverage Rate:</span>
              <span class="value">{{ (filterCoverage.coverage_rate * 100).toFixed(0) }}%</span>
            </div>
          </div>

          <div v-if="filterCoverage.filter_distribution" class="filter-distribution">
            <h4>Documents per Filter:</h4>
            <div class="distribution-list">
              <div
                v-for="(count, filter) in filterCoverage.filter_distribution"
                :key="filter"
                class="distribution-item"
              >
                <span class="filter-name">{{ filter }}</span>
                <span class="doc-count">{{ count }} docs</span>
              </div>
            </div>
          </div>

          <div v-if="filterCoverage.uncovered_files?.length > 0" class="uncovered-warning">
            <p>⚠️ {{ filterCoverage.uncovered_files.length }} files not covered by any filter</p>
            <details>
              <summary>View uncovered files</summary>
              <ul>
                <li v-for="file in filterCoverage.uncovered_files.slice(0, 10)" :key="file">
                  {{ file }}
                </li>
                <li v-if="filterCoverage.uncovered_files.length > 10">
                  ... and {{ filterCoverage.uncovered_files.length - 10 }} more
                </li>
              </ul>
            </details>
          </div>
        </div>
      </div>

      <!-- Metadata Extraction -->
      <div class="section-card">
        <h3>Metadata Extraction Preview</h3>
        <div v-if="metadataExtraction">
          <div class="extraction-stats">
            <div class="success-rate">
              <span class="label">Success Rate:</span>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: (metadataExtraction.success_rate * 100) + '%' }"
                ></div>
                <span class="percentage">{{ (metadataExtraction.success_rate * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>

          <div v-if="metadataExtraction.coverage" class="field-coverage">
            <h4>Field Coverage:</h4>
            <div class="coverage-grid">
              <div
                v-for="(coverage, field) in metadataExtraction.coverage"
                :key="field"
                class="coverage-item"
              >
                <span class="field-name">{{ field }}</span>
                <div class="mini-progress">
                  <div class="mini-fill" :style="{ width: (coverage * 100) + '%' }"></div>
                </div>
                <span class="coverage-value">{{ (coverage * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>

          <div v-if="citationPreviews?.length > 0" class="citation-preview">
            <h4>Sample Citations:</h4>
            <div class="citation-list">
              <div v-for="(preview, index) in citationPreviews.slice(0, 3)" :key="index" class="citation-item">
                <div class="citation-text">{{ preview.citation }}</div>
                <div v-if="preview.url" class="citation-url">
                  <a :href="preview.url" target="_blank">{{ preview.url }}</a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Issues and Recommendations -->
      <div v-if="detectedIssues?.length > 0" class="section-card issues-section">
        <h3>Detected Issues</h3>
        <div class="issues-list">
          <div
            v-for="(issue, index) in detectedIssues"
            :key="index"
            class="issue-item"
            :class="issue.severity"
          >
            <div class="issue-header">
              <span class="issue-icon">
                {{ issue.severity === 'error' ? '❌' : '⚠️' }}
              </span>
              <span class="issue-type">{{ formatIssueType(issue.type) }}</span>
              <button
                v-if="issue.auto_fixable"
                @click="fixIssue(issue)"
                class="fix-btn"
              >
                Auto Fix
              </button>
            </div>
            <p class="issue-message">{{ issue.message }}</p>
            <p v-if="issue.file" class="issue-file">File: {{ issue.file }}</p>
          </div>
        </div>
      </div>

      <!-- Recommendations -->
      <div v-if="recommendations?.length > 0" class="section-card">
        <h3>Recommendations</h3>
        <ul class="recommendations-list">
          <li v-for="(rec, index) in recommendations" :key="index">
            {{ rec }}
          </li>
        </ul>
      </div>

      <!-- Processing Time Estimate -->
      <div class="section-card">
        <h3>Processing Time Estimate</h3>
        <div v-if="timeEstimation" class="time-estimate">
          <div class="estimate-grid">
            <div class="estimate-item">
              <span class="label">Estimated Time:</span>
              <span class="value">{{ formatTime(timeEstimation.estimated_seconds) }}</span>
            </div>
            <div class="estimate-item">
              <span class="label">Processing Rate:</span>
              <span class="value">{{ timeEstimation.files_per_minute }} files/min</span>
            </div>
            <div class="estimate-item">
              <span class="label">Mode:</span>
              <span class="value">{{ timeEstimation.mode.toUpperCase() }}</span>
            </div>
            <div class="estimate-item">
              <span class="label">Confidence:</span>
              <span class="value">{{ (timeEstimation.confidence * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="validation-actions">
      <button @click="adjustPatterns" class="action-btn">Adjust Patterns</button>
      <button @click="revalidate" class="action-btn">Re-validate</button>
      <button
        v-if="hasAutoFixableIssues"
        @click="fixAllIssues"
        class="action-btn fix-all"
      >
        Fix All Issues
      </button>
    </div>

    <div class="form-actions">
      <button @click="$emit('back')" class="btn btn-secondary">Back</button>
      <button
        @click="$emit('next')"
        class="btn btn-primary"
        :disabled="!canProceed"
      >
        {{ validationResults?.valid ? 'Continue to Build' : 'Continue with Issues' }}
      </button>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';

export default {
  name: 'ValidationPreview',

  props: {
    validationResults: {
      type: Object,
      default: () => ({})
    },
    sampleData: {
      type: Object,
      default: () => ({})
    }
  },

  emits: ['next', 'back', 'fix-issues', 'revalidate'],

  setup(props, { emit }) {
    const validationStatus = computed(() => {
      return props.validationResults?.valid ? 'success' : 'warning';
    });

    const validationSummaryText = computed(() => {
      if (props.validationResults?.valid) {
        return 'Your corpus is ready for processing. All validation checks passed.';
      } else {
        const issueCount = props.validationResults?.issues?.length || 0;
        return `Found ${issueCount} issue${issueCount !== 1 ? 's' : ''} that may affect processing quality.`;
      }
    });

    const sampleCoverage = computed(() => {
      if (!props.sampleData) return 0;
      const coverage = (props.sampleData.sample_size / props.sampleData.total_files) * 100;
      return Math.min(100, coverage).toFixed(1);
    });

    const filterCoverage = computed(() => {
      return props.validationResults?.filter_coverage;
    });

    const metadataExtraction = computed(() => {
      return props.validationResults?.metadata_extraction;
    });

    const detectedIssues = computed(() => {
      return props.validationResults?.detected_issues || [];
    });

    const recommendations = computed(() => {
      return props.validationResults?.recommendations || [];
    });

    const timeEstimation = computed(() => {
      return props.validationResults?.time_estimation;
    });

    const citationPreviews = computed(() => {
      // Extract sample citations from metadata extraction
      const extracted = props.validationResults?.metadata_extraction?.extracted_fields;
      if (!extracted) return [];

      // Mock citation previews
      return [
        {
          citation: 'Smith, J. Document Title. 2024-01-15. Corpus.',
          url: 'https://example.com/doc1'
        },
        {
          citation: 'Johnson, M. Another Document. 2024-01-16. Corpus.',
          url: 'https://example.com/doc2'
        }
      ];
    });

    const hasAutoFixableIssues = computed(() => {
      return detectedIssues.value.some(issue => issue.auto_fixable);
    });

    const canProceed = computed(() => {
      // Allow proceeding even with warnings, but not with errors
      const hasErrors = detectedIssues.value.some(issue => issue.severity === 'error');
      return !hasErrors;
    });

    const formatIssueType = (type) => {
      return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    };

    const formatTime = (seconds) => {
      if (seconds < 60) {
        return `${seconds} seconds`;
      } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
      } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours} hour${hours !== 1 ? 's' : ''} ${minutes} min`;
      }
    };

    const fixIssue = (issue) => {
      emit('fix-issues', [issue]);
    };

    const fixAllIssues = () => {
      const fixableIssues = detectedIssues.value.filter(i => i.auto_fixable);
      emit('fix-issues', fixableIssues);
    };

    const adjustPatterns = () => {
      // Navigate back to filter configuration
      emit('back');
      emit('back');
    };

    const revalidate = () => {
      emit('revalidate');
    };

    return {
      validationStatus,
      validationSummaryText,
      sampleCoverage,
      filterCoverage,
      metadataExtraction,
      detectedIssues,
      recommendations,
      timeEstimation,
      citationPreviews,
      hasAutoFixableIssues,
      canProceed,
      formatIssueType,
      formatTime,
      fixIssue,
      fixAllIssues,
      adjustPatterns,
      revalidate
    };
  }
};
</script>

<style scoped>
.validation-preview {
  max-width: 1000px;
  margin: 0 auto;
}

.validation-preview h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.form-description {
  color: #666;
  margin-bottom: 2rem;
}

.validation-summary {
  margin-bottom: 2rem;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.5rem;
  border-radius: 8px;
  background: white;
  border: 2px solid #e0e0e0;
}

.summary-card.success {
  border-color: #4caf50;
  background: #e8f5e9;
}

.summary-card.warning {
  border-color: #ff9800;
  background: #fff3e0;
}

.status-icon {
  font-size: 3rem;
}

.status-content h3 {
  margin: 0 0 0.5rem;
  color: #333;
}

.status-content p {
  margin: 0;
  color: #666;
}

.validation-sections {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.section-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
}

.section-card h3 {
  margin-top: 0;
  color: #333;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

.coverage-stats {
  display: flex;
  gap: 2rem;
  margin-bottom: 1rem;
}

.stat {
  display: flex;
  flex-direction: column;
}

.filter-distribution {
  margin-top: 1rem;
}

.distribution-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.distribution-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
}

.uncovered-warning {
  margin-top: 1rem;
  padding: 1rem;
  background: #fff3e0;
  border-left: 4px solid #ff9800;
  border-radius: 4px;
}

.extraction-stats {
  margin-bottom: 1rem;
}

.success-rate {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-bar {
  flex: 1;
  height: 24px;
  background: #e0e0e0;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #66bb6a);
  border-radius: 12px;
  transition: width 0.3s ease;
}

.percentage {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
}

.field-coverage {
  margin-top: 1rem;
}

.coverage-grid {
  display: grid;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.coverage-item {
  display: grid;
  grid-template-columns: 100px 1fr 50px;
  align-items: center;
  gap: 0.5rem;
}

.mini-progress {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.mini-fill {
  height: 100%;
  background: #3498db;
  border-radius: 4px;
}

.citation-preview {
  margin-top: 1rem;
}

.citation-list {
  margin-top: 0.5rem;
}

.citation-item {
  padding: 0.75rem;
  background: #f5f5f5;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.citation-text {
  font-family: serif;
  font-size: 0.95rem;
  color: #333;
}

.citation-url {
  margin-top: 0.25rem;
  font-size: 0.875rem;
}

.citation-url a {
  color: #3498db;
  text-decoration: none;
}

.issues-section {
  border-color: #ff9800;
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.issue-item {
  padding: 1rem;
  border-radius: 4px;
  border-left: 4px solid;
}

.issue-item.error {
  background: #ffebee;
  border-color: #f44336;
}

.issue-item.warning {
  background: #fff3e0;
  border-color: #ff9800;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.issue-icon {
  font-size: 1.2rem;
}

.issue-type {
  font-weight: 500;
  color: #333;
  flex: 1;
}

.fix-btn {
  padding: 0.25rem 0.75rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.issue-message {
  margin: 0 0 0.5rem;
  color: #666;
}

.issue-file {
  margin: 0;
  font-size: 0.875rem;
  color: #999;
  font-family: monospace;
}

.recommendations-list {
  margin: 0.5rem 0 0 1.5rem;
  padding: 0;
}

.recommendations-list li {
  margin-bottom: 0.5rem;
  color: #666;
}

.time-estimate {
  margin-top: 0.5rem;
}

.estimate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.estimate-item {
  display: flex;
  flex-direction: column;
}

.validation-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  justify-content: center;
}

.action-btn {
  padding: 0.5rem 1rem;
  background: white;
  color: #3498db;
  border: 2px solid #3498db;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-btn:hover {
  background: #3498db;
  color: white;
}

.action-btn.fix-all {
  border-color: #4caf50;
  color: #4caf50;
}

.action-btn.fix-all:hover {
  background: #4caf50;
  color: white;
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
</style>