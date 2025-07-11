<template>
  <div class="validate-session-container">
    <button 
      class="button is-info is-small"
      @click="validateSession"
      :disabled="isValidating || !canValidate"
      :title="buttonTooltip"
    >
      <span class="icon is-small">
        <i class="fas fa-check-circle" v-if="!isValidating"></i>
        <i class="fas fa-spinner fa-spin" v-else></i>
      </span>
      <span>{{ buttonText }}</span>
    </button>
    
    <!-- Validation Results Modal -->
    <div class="modal" :class="{ 'is-active': showValidationResults }">
      <div class="modal-background" @click="closeValidationResults"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">
            <span class="icon-text">
              <span class="icon">
                <i class="fas fa-check-circle"></i>
              </span>
              <span>Session Validation Results</span>
            </span>
          </p>
          <button class="delete" @click="closeValidationResults"></button>
        </header>
        
        <section class="modal-card-body">
          <div v-if="validationError" class="notification is-danger">
            <strong>Validation Error:</strong> {{ validationError }}
          </div>
          
          <div v-else-if="validationResults">
            <!-- Validation Info -->
            <div class="box">
              <h4 class="title is-5">Validation Configuration</h4>
              <div class="content">
                <div class="field is-horizontal">
                  <div class="field-label is-small">
                    <label class="label">Model:</label>
                  </div>
                  <div class="field-body">
                    <div class="field">
                      <div class="control">
                        <span class="tag is-info">
                          {{ validationResults.validation_provider }}/{{ validationResults.validation_model }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="field is-horizontal">
                  <div class="field-label is-small">
                    <label class="label">Mode:</label>
                  </div>
                  <div class="field-body">
                    <div class="field">
                      <div class="control">
                        <span class="tag" :class="validationResults.validation_mode === 'alternate' ? 'is-success' : 'is-primary'">
                          {{ validationResults.validation_mode }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="field is-horizontal">
                  <div class="field-label is-small">
                    <label class="label">Processing Time:</label>
                  </div>
                  <div class="field-body">
                    <div class="field">
                      <div class="control">
                        <span class="tag is-light">
                          {{ validationResults.processing_time.toFixed(2) }}s
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Structured Feedback -->
            <div class="box" v-if="validationResults.structured_feedback && validationResults.structured_feedback.overall_quality">
              <h4 class="title is-5">Structured Assessment</h4>
              <div class="content">
                <div class="field">
                  <label class="label">Overall Quality:</label>
                  <span class="tag is-large" :class="getQualityTagClass(validationResults.structured_feedback.overall_quality)">
                    {{ validationResults.structured_feedback.overall_quality }}
                  </span>
                </div>
                
                <!-- Quality Scores -->
                <div class="columns is-multiline" v-if="hasScores">
                  <div class="column is-half" v-for="(score, category) in getQualityScores(validationResults.structured_feedback)" :key="category">
                    <div class="field">
                      <label class="label is-small">{{ formatCategoryName(category) }}:</label>
                      <progress class="progress" :class="getScoreProgressClass(score.score)" :value="score.score" max="5">
                        {{ score.score }}/5
                      </progress>
                      <p class="help is-size-7" v-if="score.issues && score.issues.length > 0">
                        Issues: {{ score.issues.join(', ') }}
                      </p>
                    </div>
                  </div>
                </div>
                
                <!-- Recommendations -->
                <div class="field" v-if="validationResults.structured_feedback.recommendations && validationResults.structured_feedback.recommendations.length > 0">
                  <label class="label">Recommendations:</label>
                  <ul class="content">
                    <li v-for="rec in validationResults.structured_feedback.recommendations" :key="rec">
                      {{ rec }}
                    </li>
                  </ul>
                </div>
                
                <!-- Strengths -->
                <div class="field" v-if="validationResults.structured_feedback.strengths && validationResults.structured_feedback.strengths.length > 0">
                  <label class="label">Strengths:</label>
                  <ul class="content">
                    <li v-for="strength in validationResults.structured_feedback.strengths" :key="strength">
                      {{ strength }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            
            <!-- Raw Feedback -->
            <div class="box">
              <h4 class="title is-5">Detailed Feedback</h4>
              <div class="content">
                <pre class="validation-feedback">{{ validationResults.feedback }}</pre>
              </div>
            </div>
            
            <!-- Export Section -->
            <div class="box">
              <h4 class="title is-5">Export Options</h4>
              <div class="field is-grouped">
                <div class="control">
                  <button class="button is-primary" @click="downloadMarkdown">
                    <span class="icon">
                      <i class="fas fa-download"></i>
                    </span>
                    <span>Download Markdown</span>
                  </button>
                </div>
                <div class="control">
                  <button class="button is-info" @click="copyToClipboard">
                    <span class="icon">
                      <i class="fas fa-copy"></i>
                    </span>
                    <span>Copy Feedback</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
        
        <footer class="modal-card-foot">
          <button class="button is-primary" @click="closeValidationResults">Close</button>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
const { 
  chatHistory, 
  sessionId, 
  qaId,
  isResponseComplete 
} = storeToRefs(sessionStore)

const isValidating = ref(false)
const showValidationResults = ref(false)
const validationResults = ref(null)
const validationError = ref(null)
const markdownExport = ref(null)

const canValidate = computed(() => {
  return chatHistory.value.length > 0 && 
         isResponseComplete.value && 
         sessionId.value && 
         qaId.value
})

const buttonText = computed(() => {
  return isValidating.value ? 'Validating...' : 'Validate Session'
})

const buttonTooltip = computed(() => {
  if (!canValidate.value) {
    return 'Complete a question-answer session first'
  }
  return 'Validate this session using an alternate LLM'
})

const hasScores = computed(() => {
  return validationResults.value?.structured_feedback && 
         Object.keys(getQualityScores(validationResults.value.structured_feedback)).length > 0
})

async function validateSession() {
  if (!canValidate.value) return
  
  isValidating.value = true
  validationError.value = null
  
  try {
    // Get the current session data
    const currentSession = getCurrentSessionData()
    
    // Call the validation API
    const response = await fetch('/api/validate_session', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(currentSession)
    })
    
    const data = await response.json()
    
    if (data.success) {
      validationResults.value = data.validation_result
      markdownExport.value = data.markdown_export
      showValidationResults.value = true
    } else {
      validationError.value = data.message
      showValidationResults.value = true
    }
    
  } catch (error) {
    console.error('Validation error:', error)
    validationError.value = `Network error: ${error.message}`
    showValidationResults.value = true
  } finally {
    isValidating.value = false
  }
}

function getCurrentSessionData() {
  // Get the latest question and answer from chat history
  const latestEntry = chatHistory.value[chatHistory.value.length - 1]
  
  return {
    session_id: sessionId.value,
    qa_id: qaId.value,
    question: latestEntry?.question || '',
    answer: latestEntry?.answer || '',
    citations: latestEntry?.citations || [],
    metadata: {
      model: latestEntry?.model || 'unknown',
      retriever: 'hansard_retriever',
      target_config: latestEntry?.target_config || 'unknown',
      processing_time: latestEntry?.processing_time || 0,
      timestamp: new Date().toISOString()
    }
  }
}

function closeValidationResults() {
  showValidationResults.value = false
  validationResults.value = null
  validationError.value = null
}

function getQualityTagClass(quality) {
  const classes = {
    'excellent': 'is-success',
    'good': 'is-primary',
    'fair': 'is-warning',
    'poor': 'is-danger'
  }
  return classes[quality] || 'is-light'
}

function getQualityScores(feedback) {
  const scores = {}
  const scoreFields = ['factual_accuracy', 'completeness', 'relevance', 'citation_quality', 'clarity', 'historical_context']
  
  scoreFields.forEach(field => {
    if (feedback[field] && typeof feedback[field] === 'object' && feedback[field].score) {
      scores[field] = feedback[field]
    }
  })
  
  return scores
}

function formatCategoryName(category) {
  return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function getScoreProgressClass(score) {
  if (score >= 4) return 'is-success'
  if (score >= 3) return 'is-primary'
  if (score >= 2) return 'is-warning'
  return 'is-danger'
}

function downloadMarkdown() {
  if (!markdownExport.value) return
  
  const blob = new Blob([markdownExport.value], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `session-validation-${sessionId.value}-${qaId.value}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function copyToClipboard() {
  if (!validationResults.value?.feedback) return
  
  try {
    await navigator.clipboard.writeText(validationResults.value.feedback)
    // Could add a toast notification here
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
  }
}
</script>

<style scoped>
.validate-session-container {
  margin-bottom: 1rem;
}

.validation-feedback {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 4px;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 0.9rem;
  max-height: 400px;
  overflow-y: auto;
}

.modal-card {
  max-width: 90vw;
  max-height: 90vh;
}

.modal-card-body {
  max-height: 70vh;
  overflow-y: auto;
}

.progress {
  height: 0.75rem;
}

.field.is-horizontal .field-label {
  flex-basis: 8rem;
}

.icon-text {
  align-items: center;
  display: flex;
}

.icon-text .icon {
  margin-right: 0.5rem;
}
</style>