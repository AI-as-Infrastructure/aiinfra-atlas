<template>
  <div class="extended-feedback">
    <div class="feedback-header">
      <h4>Extended Feedback</h4>
      <p class="subtitle">Help us improve our understanding of LLM RAG systems by providing detailed feedback</p>
    </div>

    <div class="feedback-content">
      <!-- Likert Scale Sections -->
      <div class="likert-sections">
        <!-- Factual Accuracy -->
        <div class="feedback-section">
          <label class="section-label">
            Factual Accuracy
            <span class="tooltip" title="Factual accuracy of LLM output">ⓘ</span>
          </label>
          <div class="likert-scale">
            <div
              v-for="value in 5"
              :key="`accuracy-${value}`"
              class="likert-option"
              @click="setRating('factual_accuracy', value)"
            >
              <input
                type="radio"
                :id="`accuracy-${value}`"
                :value="value"
                v-model="ratings.factual_accuracy"
                :disabled="disabled"
              />
              <label :for="`accuracy-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.factual_accuracy >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Analysis Quality -->
        <div class="feedback-section">
          <label class="section-label">
            Analysis Quality
            <span class="tooltip" title="Quality of historical analysis">ⓘ</span>
          </label>
          <div class="likert-scale">
            <div
              v-for="value in 5"
              :key="`analysis-${value}`"
              class="likert-option"
              @click="setRating('analysis_quality', value)"
            >
              <input
                type="radio"
                :id="`analysis-${value}`"
                :value="value"
                v-model="ratings.analysis_quality"
                :disabled="disabled"
              />
              <label :for="`analysis-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.analysis_quality >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Relevance -->
        <div class="feedback-section">
          <label class="section-label">
            Relevance
            <span class="tooltip" title="Relevance of retrieved sources to query">ⓘ</span>
          </label>
          <div class="likert-scale">
            <div
              v-for="value in 5"
              :key="`relevance-${value}`"
              class="likert-option"
              @click="setRating('relevance', value)"
            >
              <input
                type="radio"
                :id="`relevance-${value}`"
                :value="value"
                v-model="ratings.relevance"
                :disabled="disabled"
              />
              <label :for="`relevance-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.relevance >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Difficulty -->
        <div class="feedback-section">
          <label class="section-label">
            Difficulty
            <span class="tooltip" title="Difficulty of the query">ⓘ</span>
          </label>
          <div class="likert-scale">
            <div
              v-for="value in 5"
              :key="`difficulty-${value}`"
              class="likert-option"
              @click="setRating('difficulty', value)"
            >
              <input
                type="radio"
                :id="`difficulty-${value}`"
                :value="value"
                v-model="ratings.difficulty"
                :disabled="disabled"
              />
              <label :for="`difficulty-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.difficulty >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Clarity -->
        <div class="feedback-section">
          <label class="section-label">
            Clarity
            <span class="tooltip" title="Clarity of the response">ⓘ</span>
          </label>
          <div class="likert-scale">
            <div
              v-for="value in 5"
              :key="`clarity-${value}`"
              class="likert-option"
              @click="setRating('clarity', value)"
            >
              <input
                type="radio"
                :id="`clarity-${value}`"
                :value="value"
                v-model="ratings.clarity"
                :disabled="disabled"
              />
              <label :for="`clarity-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.clarity >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Faults Section -->
      <div class="faults-section">
        <label class="section-label">Faults</label>
        <div class="faults-grid">
          <div class="fault-option">
            <input
              type="checkbox"
              id="fault-hallucination"
              v-model="faults.hallucination"
              :disabled="disabled"
            />
            <label for="fault-hallucination">Hallucination</label>
          </div>
          <div class="fault-option">
            <input
              type="checkbox"
              id="fault-off-topic"
              v-model="faults.off_topic"
              :disabled="disabled"
            />
            <label for="fault-off-topic">Off-topic</label>
          </div>
          <div class="fault-option">
            <input
              type="checkbox"
              id="fault-inappropriate"
              v-model="faults.inappropriate"
              :disabled="disabled"
            />
            <label for="fault-inappropriate">Inappropriate</label>
          </div>
          <div class="fault-option">
            <input
              type="checkbox"
              id="fault-bias"
              v-model="faults.bias"
              :disabled="disabled"
            />
            <label for="fault-bias">Bias</label>
          </div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="feedback-actions">
      <button
        class="cancel-btn"
        @click="$emit('cancel')"
        :disabled="isSubmitting"
      >
        Cancel
      </button>
      <button
        class="submit-btn"
        @click="submitExtendedFeedback"
        :disabled="isSubmitting || !hasExtendedFeedback"
      >
        <span v-if="isSubmitting">Submitting...</span>
        <span v-else>Submit Extended Feedback</span>
      </button>
    </div>
  </div>
</template>

<script>
import { useSessionStore } from '@/stores/session'
import { useTelemetryStore } from '@/stores/telemetry'

export default {
  name: 'ExtendedFeedback',
  props: {
    qaId: {
      type: String,
      required: true
    },
    sessionId: {
      type: String,
      required: true
    },
    disabled: {
      type: Boolean,
      default: false
    },
    initialData: {
      type: Object,
      default: () => ({})
    },
    completeFeedbackPayload: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['cancel', 'feedback-submitted'],
  setup() {
    const sessionStore = useSessionStore()
    const telemetryStore = useTelemetryStore()
    return { sessionStore, telemetryStore }
  },
  data() {
    return {
      ratings: {
        factual_accuracy: null,
        analysis_quality: null,
        relevance: null,
        difficulty: null,
        clarity: null
      },
      faults: {
        hallucination: false,
        off_topic: false,
        inappropriate: false,
        bias: false
      },
      isSubmitting: false,
      configData: null
    }
  },
  computed: {
    hasExtendedFeedback() {
      const hasRatings = Object.values(this.ratings).some(rating => rating !== null)
      const hasFaults = Object.values(this.faults).some(fault => fault === true)
      return hasRatings || hasFaults
    }
  },
  methods: {
    setRating(category, value) {
      if (this.disabled) return
      this.ratings[category] = value
    },
    
    async fetchConfigData() {
      try {
        const response = await fetch('/api/config')
        if (response.ok) {
          this.configData = await response.json()
        }
      } catch (error) {
        console.error('Error fetching config data:', error)
        this.configData = {}
      }
    },
    
    convertFactualAccuracyRating(rating) {
      // Convert 1-5 Likert scale to string format for backend
      // But send the actual numeric score instead of string conversion
      // This preserves the user's intended rating
      return rating // Send numeric rating directly
    },
    
    async submitExtendedFeedback() {
      if (!this.hasExtendedFeedback || this.isSubmitting) return
      
      this.isSubmitting = true
      
      try {
        // Get current session data for the submission
        const chatHistory = this.sessionStore.chatHistory
        const currentQuestion = chatHistory[chatHistory.length - 2]?.content || ''
        const currentAnswer = chatHistory[chatHistory.length - 1]?.content || ''
        const fullCitations = chatHistory[chatHistory.length - 1]?.citations || []
        
        // Build the complete feedback payload for extended feedback
        const feedbackData = {
          qa_id: this.qaId,
          session_id: this.sessionId,
          feedback_type: 'extended',
          timestamp: new Date().toISOString(),
          question: currentQuestion,
          answer: currentAnswer,
          citations: fullCitations,
          
          // Add trace ID if available
          trace_id: this.telemetryStore.traceId
        }
        
        console.log('EXTENDED: feedbackData after spread:', feedbackData)
        console.log('EXTENDED: About to submit to API')
        console.log('EXTENDED: This should be the ONLY API call for extended feedback path')
        
        // Extended feedback ratings - only include if set
        // Send factual accuracy as numeric rating (1-5) to preserve user intent
        if (this.ratings.factual_accuracy !== null) {
          feedbackData.factual_accuracy = this.ratings.factual_accuracy
        }
        
        if (this.ratings.analysis_quality !== null) {
          feedbackData.analysis_quality = this.ratings.analysis_quality
        }
        
        if (this.ratings.relevance !== null) {
          feedbackData.relevance = this.ratings.relevance
        }
        
        if (this.ratings.difficulty !== null) {
          feedbackData.difficulty = this.ratings.difficulty
        }
        
        if (this.ratings.clarity !== null) {
          feedbackData.clarity = this.ratings.clarity
        }
        
        // Faults - only include if any are selected (use faults structure, not tags to avoid duplication)
        const activeFaults = Object.entries(this.faults)
          .filter(([_, value]) => value === true)
        
        if (activeFaults.length > 0) {
          // Only send faults structure, not both tags and faults to avoid duplication
          feedbackData.faults = this.faults
        }
        
        // The simple feedback data (sentiment, feedback_text, etc.) is already included from completeFeedbackPayload
        // Just need to add any additional config data if it exists
        if (this.configData && Object.keys(this.configData).length > 0) {
          feedbackData.test_target = { ...feedbackData.test_target, ...this.configData }
        }
        
        
        console.log('EXTENDED: Final payload being sent:', feedbackData)
        
        // Submit to API with telemetry headers
        const response = await fetch('/api/feedback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Trace-Id': this.telemetryStore.traceId,
            'X-Session-Id': this.sessionId
          },
          body: JSON.stringify(feedbackData)
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        console.log('EXTENDED: API call completed successfully')
        
        // Emit success
        this.$emit('feedback-submitted', 'extended')
        
        // Reset form
        this.resetForm()
        
      } catch (error) {
        console.error('Error submitting extended feedback:', error)
        // Could emit error event or show notification
      } finally {
        this.isSubmitting = false
      }
    },
    
    resetForm() {
      this.ratings = {
        factual_accuracy: null,
        analysis_quality: null,
        relevance: null,
        difficulty: null,
        clarity: null
      }
      this.faults = {
        hallucination: false,
        off_topic: false,
        inappropriate: false,
        bias: false
      }
    }
  },
  
  async mounted() {
    await this.fetchConfigData()
    
    // Load any initial data if provided
    if (this.initialData.ratings) {
      this.ratings = { ...this.ratings, ...this.initialData.ratings }
    }
    if (this.initialData.faults) {
      this.faults = { ...this.faults, ...this.initialData.faults }
    }
  }
}
</script>

<style scoped>
.extended-feedback {
  margin-top: 1rem;
  padding: 1.5rem;
  background-color: white;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.feedback-header {
  margin-bottom: 1.5rem;
  text-align: center;
}

.feedback-header h4 {
  margin: 0 0 0.5rem 0;
  color: #495057;
  font-size: 18px;
}

.subtitle {
  margin: 0;
  color: #6c757d;
  font-size: 14px;
}

.feedback-content {
  margin-bottom: 1.5rem;
}

.likert-sections {
  margin-bottom: 2rem;
}

.feedback-section {
  margin-bottom: 1.5rem;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.75rem;
  font-size: 14px;
}

.tooltip {
  color: #6c757d;
  cursor: help;
  font-size: 12px;
}

.likert-scale {
  display: flex;
  justify-content: space-between;
  max-width: 300px;
  margin: 0 auto;
}

.likert-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.likert-option input[type="radio"] {
  display: none;
}

.likert-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 0.25rem;
}

.likert-circle {
  width: 20px;
  height: 20px;
  border: 2px solid #dee2e6;
  border-radius: 50%;
  background-color: white;
  transition: all 0.2s ease;
  margin-bottom: 0.25rem;
}

.likert-circle.active {
  background-color: #363636;
  border-color: #363636;
}

.likert-text {
  font-size: 12px;
  color: #6c757d;
}

.faults-section {
  border-top: 1px solid #e9ecef;
  padding-top: 1.5rem;
}

.faults-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-top: 0.75rem;
}

.fault-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fault-option input[type="checkbox"] {
  margin: 0;
}

.fault-option label {
  font-size: 14px;
  color: #495057;
  cursor: pointer;
}

.feedback-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  border-top: 1px solid #e9ecef;
  padding-top: 1rem;
}

.cancel-btn {
  background-color: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.cancel-btn:hover:not(:disabled) {
  background-color: #545b62;
}

.submit-btn {
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.submit-btn:hover:not(:disabled) {
  background-color: #218838;
}

.submit-btn:disabled,
.cancel-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

@media (max-width: 768px) {
  .extended-feedback {
    padding: 1rem;
  }
  
  .likert-scale {
    max-width: 250px;
  }
  
  .faults-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .feedback-actions {
    flex-direction: column;
  }
}
</style>