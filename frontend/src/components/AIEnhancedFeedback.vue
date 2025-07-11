<template>
  <div class="ai-enhanced-feedback">
    <div class="feedback-header">
      <h4>
        <span class="icon-text">
          <span class="icon has-text-info">
            <i class="fas fa-robot"></i>
          </span>
          <span>AI-Enhanced Feedback</span>
        </span>
      </h4>
      <p class="subtitle">
        Get AI validation assistance and provide comprehensive human feedback
      </p>
      <div class="notification is-info is-light info-box">
        <p><strong>How AI Validation Works:</strong></p>
        <p>AI validation analyzes the complete response including the full answer text, all citations, and metadata. This comprehensive analysis takes 10-12 seconds as the AI processes the entire payload to provide detailed quality assessments.</p>
        <p><strong>Important:</strong> LLMs can make mistakes. Use the AI validation as a helpful starting point, but exercise your own judgment when providing final feedback.</p>
      </div>
    </div>

    <div class="feedback-content">
      <!-- AI Validation Section -->
      <div class="ai-validation-section">
        <div class="section-header">
          <h5 class="title is-5">
            <span class="icon-text">
              <span class="icon has-text-primary">
                <i class="fas fa-check-circle"></i>
              </span>
              <span>AI Validation</span>
            </span>
          </h5>
          <button 
            class="button is-small is-primary" 
            @click="runAIValidation"
            :disabled="isValidating || hasAIValidation"
            :class="{ 'is-loading': isValidating }"
          >
            <span class="icon is-small">
              <i class="fas fa-magic"></i>
            </span>
            <span>{{ hasAIValidation ? 'AI Validation Complete' : 'Run AI Validation' }}</span>
          </button>
        </div>

        <!-- AI Validation Progress -->
        <div v-if="isValidating" class="validation-progress mb-4">
          <div class="progress-header">
            <span class="progress-message">{{ validationProgress.message }}</span>
            <span class="progress-percentage">{{ validationProgress.percentage }}%</span>
          </div>
          <progress class="progress is-primary" :value="validationProgress.percentage" max="100">
            {{ validationProgress.percentage }}%
          </progress>
          <div class="progress-details">
            <span class="tag is-light">
              <i class="fas fa-clock"></i>
              Estimated time: {{ getEstimatedTime() }}
            </span>
          </div>
        </div>

        <!-- AI Validation Results -->
        <div v-if="aiValidationError" class="notification is-danger is-small">
          <strong>AI Validation Error:</strong> {{ aiValidationError }}
        </div>

        <div v-else-if="aiValidation" class="ai-validation-results">
          <!-- AI Configuration Info -->
          <div class="field is-grouped is-grouped-multiline">
            <div class="control">
              <div class="tags has-addons">
                <span class="tag is-info">AI Model</span>
                <span class="tag is-light">{{ aiValidation.validation_provider }}/{{ aiValidation.validation_model }}</span>
              </div>
            </div>
            <div class="control">
              <div class="tags has-addons">
                <span class="tag is-info">Mode</span>
                <span class="tag" :class="aiValidation.validation_mode === 'alternate' ? 'is-success' : 'is-primary'">
                  {{ aiValidation.validation_mode }}
                </span>
              </div>
            </div>
            <div class="control">
              <div class="tags has-addons">
                <span class="tag is-info">Processing</span>
                <span class="tag is-light">{{ aiValidation.processing_time?.toFixed(2) }}s</span>
              </div>
            </div>
          </div>

          <!-- AI Quality Assessment -->
          <div v-if="aiValidation.structured_feedback" class="ai-quality-assessment">
            <div class="field">
              <label class="label is-small">AI Overall Quality Assessment:</label>
              <span class="tag is-medium" :class="getQualityTagClass(aiValidation.structured_feedback.overall_quality)">
                {{ aiValidation.structured_feedback.overall_quality || 'Not assessed' }}
              </span>
            </div>

            <!-- AI Quality Scores -->
            <div class="ai-scores" v-if="hasAIScores">
              <div class="columns is-multiline">
                <div class="column is-half" v-for="(score, category) in getAIQualityScores()" :key="category">
                  <div class="field">
                    <label class="label is-small">{{ formatCategoryName(category) }}:</label>
                    <progress class="progress is-small" :class="getScoreProgressClass(score.score)" :value="score.score" max="5">
                      {{ score.score }}/5
                    </progress>
                    <p class="help is-size-7" v-if="score.issues && score.issues.length > 0">
                      <strong>AI noted:</strong> {{ score.issues.join(', ') }}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <!-- AI Recommendations -->
            <div v-if="aiValidation.structured_feedback.recommendations && aiValidation.structured_feedback.recommendations.length > 0" class="ai-recommendations">
              <label class="label is-small">AI Recommendations:</label>
              <ul class="content is-small">
                <li v-for="rec in aiValidation.structured_feedback.recommendations" :key="rec">
                  {{ rec }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div v-else class="notification is-info is-light is-small">
          <p>
            <strong>AI Validation:</strong> Run AI validation to get structured feedback about this response. 
            The AI will analyze factual accuracy, completeness, and citation quality to help guide your human assessment.
          </p>
        </div>
      </div>

      <!-- Human Feedback Section -->
      <div class="human-feedback-section">
        <div class="section-header">
          <h5 class="title is-5">
            <span class="icon-text">
              <span class="icon has-text-success">
                <i class="fas fa-user"></i>
              </span>
              <span>Your Expert Assessment</span>
            </span>
          </h5>
          <p class="subtitle is-6">
            {{ hasAIValidation ? 'Compare your assessment with the AI analysis above' : 'Provide your expert evaluation' }}
          </p>
        </div>

        <!-- Human Likert Scale Sections -->
        <div class="likert-sections">
          <!-- Factual Accuracy -->
          <div class="feedback-section">
            <label class="section-label">
              Factual Accuracy
              <span class="tooltip" title="How accurate are the facts presented?">ⓘ</span>
              <span v-if="hasAIScores && aiValidation.structured_feedback.factual_accuracy" class="ai-comparison">
                (AI: {{ aiValidation.structured_feedback.factual_accuracy.score }}/5)
              </span>
            </label>
            <div class="likert-scale">
              <div
                v-for="value in 5"
                :key="`accuracy-${value}`"
                class="likert-option"
                @click="setRating('factual_accuracy', value)"
              >
                <div class="likert-label">
                  <span class="likert-circle" :class="{ active: ratings.factual_accuracy >= value }"></span>
                  <span class="likert-text">{{ value }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Completeness -->
          <div class="feedback-section">
            <label class="section-label">
              Completeness
              <span class="tooltip" title="How completely does the response address the question?">ⓘ</span>
              <span v-if="hasAIScores && aiValidation.structured_feedback.completeness" class="ai-comparison">
                (AI: {{ aiValidation.structured_feedback.completeness.score }}/5)
              </span>
            </label>
            <div class="likert-scale">
              <div
                v-for="value in 5"
                :key="`completeness-${value}`"
                class="likert-option"
                @click="setRating('completeness', value)"
              >
                <div class="likert-label">
                  <span class="likert-circle" :class="{ active: ratings.completeness >= value }"></span>
                  <span class="likert-text">{{ value }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Relevance -->
          <div class="feedback-section">
            <label class="section-label">
              Relevance
              <span class="tooltip" title="How relevant is the information to the question?">ⓘ</span>
              <span v-if="hasAIScores && aiValidation.structured_feedback.relevance" class="ai-comparison">
                (AI: {{ aiValidation.structured_feedback.relevance.score }}/5)
              </span>
            </label>
            <div class="likert-scale">
              <div
                v-for="value in 5"
                :key="`relevance-${value}`"
                class="likert-option"
                @click="setRating('relevance', value)"
              >
                <div class="likert-label">
                  <span class="likert-circle" :class="{ active: ratings.relevance >= value }"></span>
                  <span class="likert-text">{{ value }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Citation Quality -->
          <div class="feedback-section">
            <label class="section-label">
              Citation Quality
              <span class="tooltip" title="How appropriate and accurate are the citations?">ⓘ</span>
              <span v-if="hasAIScores && aiValidation.structured_feedback.citation_quality" class="ai-comparison">
                (AI: {{ aiValidation.structured_feedback.citation_quality.score }}/5)
              </span>
            </label>
            <div class="likert-scale">
              <div
                v-for="value in 5"
                :key="`citation-${value}`"
                class="likert-option"
                @click="setRating('citation_quality', value)"
              >
                <div class="likert-label">
                  <span class="likert-circle" :class="{ active: ratings.citation_quality >= value }"></span>
                  <span class="likert-text">{{ value }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Clarity -->
          <div class="feedback-section">
            <label class="section-label">
              Clarity
              <span class="tooltip" title="How clear and well-structured is the response?">ⓘ</span>
              <span v-if="hasAIScores && aiValidation.structured_feedback.clarity" class="ai-comparison">
                (AI: {{ aiValidation.structured_feedback.clarity.score }}/5)
              </span>
            </label>
            <div class="likert-scale">
              <div
                v-for="value in 5"
                :key="`clarity-${value}`"
                class="likert-option"
                @click="setRating('clarity', value)"
              >
                <div class="likert-label">
                  <span class="likert-circle" :class="{ active: ratings.clarity >= value }"></span>
                  <span class="likert-text">{{ value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Agreement with AI Assessment -->
        <div v-if="hasAIValidation" class="ai-agreement-section">
          <div class="field">
            <label class="label">Agreement with AI Assessment</label>
            <div class="control">
              <label class="radio">
                <input type="radio" v-model="aiAgreement" value="strongly_agree" />
                Strongly Agree
              </label>
              <label class="radio">
                <input type="radio" v-model="aiAgreement" value="agree" />
                Agree
              </label>
              <label class="radio">
                <input type="radio" v-model="aiAgreement" value="neutral" />
                Neutral
              </label>
              <label class="radio">
                <input type="radio" v-model="aiAgreement" value="disagree" />
                Disagree
              </label>
              <label class="radio">
                <input type="radio" v-model="aiAgreement" value="strongly_disagree" />
                Strongly Disagree
              </label>
            </div>
          </div>
        </div>

        <!-- Human Comments -->
        <div class="feedback-section">
          <label class="section-label">
            Your Comments
            <span class="tooltip" title="Provide specific feedback or observations">ⓘ</span>
          </label>
          <textarea
            v-model="humanComments"
            class="textarea"
            placeholder="Provide specific feedback about this response. If you disagree with the AI assessment, please explain why..."
            rows="4"
            maxlength="1000"
          ></textarea>
          <p class="help">{{ humanComments.length }}/1000 characters</p>
        </div>
      </div>

    </div>

    <!-- Action Buttons -->
    <div class="feedback-actions">
      <button class="button is-light" @click="$emit('back')" :disabled="isSubmitting">
        <span class="icon is-small">
          <i class="fas fa-arrow-left"></i>
        </span>
        <span>Back</span>
      </button>
      <button class="button is-primary" @click="submitFeedback" :disabled="!canSubmit" :class="{ 'is-loading': isSubmitting }">
        <span class="icon is-small">
          <i class="fas fa-paper-plane"></i>
        </span>
        <span>Submit Enhanced Feedback</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useSessionStore } from '@/stores/session'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  },
  qaId: {
    type: String,
    required: true
  },
  sessionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['back', 'submit'])

const sessionStore = useSessionStore()
const { chatHistory } = storeToRefs(sessionStore)

// AI Validation state
const isValidating = ref(false)
const aiValidation = ref(null)
const aiValidationError = ref(null)
const markdownExport = ref(null)
const validationProgress = ref({
  step: '',
  message: '',
  percentage: 0
})

// Human feedback state
const ratings = ref({
  factual_accuracy: null,
  completeness: null,
  relevance: null,
  citation_quality: null,
  clarity: null
})

const aiAgreement = ref('')
const humanComments = ref('')
const isSubmitting = ref(false)

// Computed properties
const hasAIValidation = computed(() => !!aiValidation.value)
const hasAIScores = computed(() => {
  return hasAIValidation.value && 
         aiValidation.value.structured_feedback && 
         Object.keys(getAIQualityScores()).length > 0
})

const canSubmit = computed(() => {
  const hasRatings = Object.values(ratings.value).some(rating => rating !== null)
  return hasRatings && !isSubmitting.value
})

// Methods
async function runAIValidation() {
  if (isValidating.value || hasAIValidation.value) return
  
  isValidating.value = true
  aiValidationError.value = null
  
  try {
    // Step 1: Preparing data
    updateProgress('prepare', 'Preparing session data for validation...', 10)
    await new Promise(resolve => setTimeout(resolve, 100)) // Small delay to show progress
    
    const currentSession = getCurrentSessionData()
    
    // Step 2: Sending to LLM
    updateProgress('sending', 'Sending data to AI validation service...', 20)
    
    const response = await fetch('/api/validate_session', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(currentSession)
    })
    
    // Step 3: Processing
    updateProgress('processing', 'AI is analyzing the complete response, citations, and metadata...', 40)
    
    const data = await response.json()
    
    // Step 4: Finalizing
    updateProgress('finalizing', 'Processing validation results...', 90)
    
    if (data.success) {
      aiValidation.value = data.validation_result
      markdownExport.value = data.markdown_export
      updateProgress('complete', 'AI validation completed successfully!', 100)
    } else {
      aiValidationError.value = data.message
    }
    
  } catch (error) {
    console.error('AI validation error:', error)
    aiValidationError.value = `Network error: ${error.message}`
  } finally {
    // Clean up progress after a short delay
    setTimeout(() => {
      isValidating.value = false
      if (!aiValidationError.value) {
        validationProgress.value = { step: '', message: '', percentage: 0 }
      }
    }, 1000)
  }
}

function updateProgress(step, message, percentage) {
  validationProgress.value = {
    step,
    message,
    percentage: Math.min(percentage, 100)
  }
}

function getEstimatedTime() {
  const percentage = validationProgress.value.percentage
  if (percentage < 20) return '10-12 seconds'
  if (percentage < 40) return '8-10 seconds'
  if (percentage < 90) return '4-6 seconds'
  return '1-2 seconds'
}

function getCurrentSessionData() {
  // Get question from second-to-last message (user) and answer from last message (assistant)
  const currentQuestion = chatHistory.value[chatHistory.value.length - 2]?.content || ''
  const currentAnswer = chatHistory.value[chatHistory.value.length - 1]?.content || ''
  const latestEntry = chatHistory.value[chatHistory.value.length - 1]
  
  return {
    session_id: props.sessionId,
    qa_id: props.qaId,
    question: currentQuestion,
    answer: currentAnswer,
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

function setRating(category, value) {
  ratings.value[category] = value
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

function getAIQualityScores() {
  if (!aiValidation.value?.structured_feedback) return {}
  
  const scores = {}
  const scoreFields = ['factual_accuracy', 'completeness', 'relevance', 'citation_quality', 'clarity', 'historical_context']
  
  scoreFields.forEach(field => {
    if (aiValidation.value.structured_feedback[field] && 
        typeof aiValidation.value.structured_feedback[field] === 'object' && 
        aiValidation.value.structured_feedback[field].score) {
      scores[field] = aiValidation.value.structured_feedback[field]
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


async function submitFeedback() {
  if (!canSubmit.value) return
  
  isSubmitting.value = true
  
  try {
    const feedbackData = {
      ratings: ratings.value,
      ai_agreement: aiAgreement.value,
      human_comments: humanComments.value,
      ai_validation: aiValidation.value,
      feedback_type: 'ai_enhanced'
    }
    
    emit('submit', feedbackData)
    
  } catch (error) {
    console.error('Error submitting feedback:', error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.ai-enhanced-feedback {
  max-width: 800px;
  margin: 0 auto;
}

.validation-progress {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 1rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.progress-message {
  font-weight: 500;
  color: #495057;
}

.progress-percentage {
  font-weight: 600;
  color: #0066cc;
}

.progress-details {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}

.progress-details .tag {
  font-size: 0.75rem;
}

.progress-details .fas {
  margin-right: 0.25rem;
}

.info-box {
  text-align: left;
}

.feedback-header {
  text-align: center;
  margin-bottom: 2rem;
}

.feedback-header h4 {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.feedback-header .subtitle {
  color: #666;
  font-size: 0.9rem;
}

.ai-validation-section,
.human-feedback-section,
.export-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.ai-validation-results {
  margin-top: 1rem;
}

.ai-scores {
  margin-top: 1rem;
}

.ai-recommendations {
  margin-top: 1rem;
}

.likert-sections {
  margin-top: 1.5rem;
}

.feedback-section {
  margin-bottom: 1.5rem;
}

.section-label {
  font-weight: 600;
  margin-bottom: 0.5rem;
  display: block;
}

.ai-comparison {
  font-size: 0.85rem;
  color: #3273dc;
  font-weight: normal;
}

.likert-scale {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.likert-option {
  cursor: pointer;
}

.likert-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
}

.likert-circle {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #ddd;
  transition: all 0.2s;
}

.likert-circle.active {
  background: #3273dc;
  border-color: #3273dc;
}

.likert-text {
  font-size: 0.8rem;
  color: #666;
}

.ai-agreement-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #eee;
}

.ai-agreement-section .radio {
  margin-right: 1rem;
}

.feedback-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #eee;
}

.progress.is-small {
  height: 0.75rem;
}

.icon-text {
  align-items: center;
  display: flex;
}

.icon-text .icon {
  margin-right: 0.5rem;
}

.tooltip {
  cursor: help;
  color: #3273dc;
}

.notification.is-small {
  padding: 0.75rem;
}

.textarea {
  min-height: 100px;
}

.help {
  font-size: 0.75rem;
  color: #999;
  text-align: right;
}
</style>