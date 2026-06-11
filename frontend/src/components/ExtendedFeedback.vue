<template>
  <div class="extended-feedback">
    <div class="feedback-header">
      <h4>Extended Feedback</h4>
      <p class="subtitle"><em>Please provide an independent evaluation of this LLM response.</em></p>
      <p class="subtitle"><em>For each of the following points, rate the LLM response on a scale of 1 (very poor) to 5 (very good). For ratings that are 1, 2, or 5, please provide a one sentence rationale.</em></p>
    </div>

    <div class="feedback-content">
      <!-- Likert Scale Sections -->
      <div class="likert-sections">
        <!-- Corpus Fidelity -->
        <div class="feedback-section">
          <label class="section-label">
            Corpus Fidelity
            <span class="tooltip" title="i.e. are all claims about what the Hansard records contain supported by a Hansard citation?">ⓘ</span>
          </label>
          <div class="likert-scale">
            <span class="likert-endpoint">1 (very poor)</span>
            <div
              v-for="value in 5"
              :key="`corpus_fidelity-${value}`"
              class="likert-option"
              @click="setRating('corpus_fidelity', value)"
            >
              <input
                type="radio"
                :id="`corpus_fidelity-${value}`"
                :value="value"
                v-model="ratings.corpus_fidelity"
                :disabled="disabled"
              />
              <label :for="`corpus_fidelity-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.corpus_fidelity >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
            <span class="likert-endpoint">5 (very good)</span>
          </div>
          <div v-if="ratings.corpus_fidelity !== null" class="scale-comment">
            <textarea
              v-model="scaleComments.corpus_fidelity"
              class="textarea is-small"
              :placeholder="isCommentRequired('corpus_fidelity') ? 'Free text rationale (for extreme ratings only): Required' : 'Free text rationale (for extreme ratings only): Not required'"
              rows="2"
              maxlength="300"
              :disabled="disabled"
            ></textarea>
            <p v-if="isCommentRequired('corpus_fidelity') && !scaleComments.corpus_fidelity.trim()" class="help is-danger">
              Rationale required for this rating
            </p>
          </div>
        </div>

        <!-- Citation Quality -->
        <div class="feedback-section">
          <label class="section-label">
            Citation Quality
            <span class="tooltip" title="i.e. does each citation support the specific claim it is attached to?">ⓘ</span>
          </label>
          <div class="likert-scale">
            <span class="likert-endpoint">1 (very poor)</span>
            <div
              v-for="value in 5"
              :key="`citation_quality-${value}`"
              class="likert-option"
              @click="setRating('citation_quality', value)"
            >
              <input
                type="radio"
                :id="`citation_quality-${value}`"
                :value="value"
                v-model="ratings.citation_quality"
                :disabled="disabled"
              />
              <label :for="`citation_quality-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.citation_quality >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
            <span class="likert-endpoint">5 (very good)</span>
          </div>
          <div v-if="ratings.citation_quality !== null" class="scale-comment">
            <textarea
              v-model="scaleComments.citation_quality"
              class="textarea is-small"
              :placeholder="isCommentRequired('citation_quality') ? 'Free text rationale (for extreme ratings only): Required' : 'Free text rationale (for extreme ratings only): Not required'"
              rows="2"
              maxlength="300"
              :disabled="disabled"
            ></textarea>
            <p v-if="isCommentRequired('citation_quality') && !scaleComments.citation_quality.trim()" class="help is-danger">
              Rationale required for this rating
            </p>
          </div>
        </div>

        <!-- Relevance -->
        <div class="feedback-section">
          <label class="section-label">
            Relevance
            <span class="tooltip" title="i.e. does the LLM answer actually address the question asked, without padding or drift?">ⓘ</span>
          </label>
          <div class="likert-scale">
            <span class="likert-endpoint">1 (very poor)</span>
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
            <span class="likert-endpoint">5 (very good)</span>
          </div>
          <div v-if="ratings.relevance !== null" class="scale-comment">
            <textarea
              v-model="scaleComments.relevance"
              class="textarea is-small"
              :placeholder="isCommentRequired('relevance') ? 'Free text rationale (for extreme ratings only): Required' : 'Free text rationale (for extreme ratings only): Not required'"
              rows="2"
              maxlength="300"
              :disabled="disabled"
            ></textarea>
            <p v-if="isCommentRequired('relevance') && !scaleComments.relevance.trim()" class="help is-danger">
              Rationale required for this rating
            </p>
          </div>
        </div>

        <!-- Coherence -->
        <div class="feedback-section">
          <label class="section-label">
            Coherence
            <span class="tooltip" title="i.e. to what extent is the LLM answer well-reasoned and argued?">ⓘ</span>
          </label>
          <div class="likert-scale">
            <span class="likert-endpoint">1 (very poor)</span>
            <div
              v-for="value in 5"
              :key="`coherence-${value}`"
              class="likert-option"
              @click="setRating('coherence', value)"
            >
              <input
                type="radio"
                :id="`coherence-${value}`"
                :value="value"
                v-model="ratings.coherence"
                :disabled="disabled"
              />
              <label :for="`coherence-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.coherence >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
            <span class="likert-endpoint">5 (very good)</span>
          </div>
          <div v-if="ratings.coherence !== null" class="scale-comment">
            <textarea
              v-model="scaleComments.coherence"
              class="textarea is-small"
              :placeholder="isCommentRequired('coherence') ? 'Free text rationale (for extreme ratings only): Required' : 'Free text rationale (for extreme ratings only): Not required'"
              rows="2"
              maxlength="300"
              :disabled="disabled"
            ></textarea>
            <p v-if="isCommentRequired('coherence') && !scaleComments.coherence.trim()" class="help is-danger">
              Rationale required for this rating
            </p>
          </div>
        </div>

        <!-- Uncertainty -->
        <div class="feedback-section">
          <label class="section-label">
            Uncertainty
            <span class="tooltip" title="i.e. to what extent does the LLM answer flag contested interpretations, gaps, or ambiguity?">ⓘ</span>
          </label>
          <div class="likert-scale">
            <span class="likert-endpoint">1 (very poor)</span>
            <div
              v-for="value in 5"
              :key="`uncertainty-${value}`"
              class="likert-option"
              @click="setRating('uncertainty', value)"
            >
              <input
                type="radio"
                :id="`uncertainty-${value}`"
                :value="value"
                v-model="ratings.uncertainty"
                :disabled="disabled"
              />
              <label :for="`uncertainty-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.uncertainty >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
            <span class="likert-endpoint">5 (very good)</span>
          </div>
          <div v-if="ratings.uncertainty !== null" class="scale-comment">
            <textarea
              v-model="scaleComments.uncertainty"
              class="textarea is-small"
              :placeholder="isCommentRequired('uncertainty') ? 'Free text rationale (for extreme ratings only): Required' : 'Free text rationale (for extreme ratings only): Not required'"
              rows="2"
              maxlength="300"
              :disabled="disabled"
            ></textarea>
            <p v-if="isCommentRequired('uncertainty') && !scaleComments.uncertainty.trim()" class="help is-danger">
              Rationale required for this rating
            </p>
          </div>
        </div>

        <!-- Historical Contextualisation -->
        <div class="feedback-section">
          <label class="section-label">
            Historical Contextualisation
            <span class="tooltip" title="i.e. to what extent does the LLM answer contextualise the primary material with additional knowledge?">ⓘ</span>
          </label>
          <div class="likert-scale">
            <span class="likert-endpoint">1 (very poor)</span>
            <div
              v-for="value in 5"
              :key="`historical_contextualisation-${value}`"
              class="likert-option"
              @click="setRating('historical_contextualisation', value)"
            >
              <input
                type="radio"
                :id="`historical_contextualisation-${value}`"
                :value="value"
                v-model="ratings.historical_contextualisation"
                :disabled="disabled"
              />
              <label :for="`historical_contextualisation-${value}`" class="likert-label">
                <span class="likert-circle" :class="{ active: ratings.historical_contextualisation >= value }"></span>
                <span class="likert-text">{{ value }}</span>
              </label>
            </div>
            <span class="likert-endpoint">5 (very good)</span>
          </div>
          <div v-if="ratings.historical_contextualisation !== null" class="scale-comment">
            <textarea
              v-model="scaleComments.historical_contextualisation"
              class="textarea is-small"
              :placeholder="isCommentRequired('historical_contextualisation') ? 'Free text rationale (for extreme ratings only): Required' : 'Free text rationale (for extreme ratings only): Not required'"
              rows="2"
              maxlength="300"
              :disabled="disabled"
            ></textarea>
            <p v-if="isCommentRequired('historical_contextualisation') && !scaleComments.historical_contextualisation.trim()" class="help is-danger">
              Rationale required for this rating
            </p>
          </div>
        </div>
      </div>

      <!-- Faults Section -->
      <div class="faults-section">
        <p class="faults-instruction">Finally, please note that if you identified any of the following faults in the LLM answer. If a fault is identified please provide a one sentence explanation.</p>
        <div class="faults-grid">
          <div class="fault-option">
            <input
              type="checkbox"
              id="fault-hallucination"
              v-model="faults.hallucination"
              :disabled="disabled"
            />
            <label for="fault-hallucination">
              Hallucination
              <span class="tooltip" title="e.g. invented facts in the answer or false attributions of content to a source">ⓘ</span>
            </label>
          </div>
          <div class="fault-option">
            <input
              type="checkbox"
              id="fault-harmful-handling"
              v-model="faults.harmful_handling"
              :disabled="disabled"
            />
            <label for="fault-harmful-handling">
              Harmful handling
              <span class="tooltip" title="i.e. the LLM adopts or endorses prejudices contained in the Hansard records in its own analytical voice, or introduces stereotyping/derogatory framing not present in the cited material">ⓘ</span>
            </label>
          </div>
        </div>
        <div class="fault-rationale">
          <label class="fault-rationale-label">Free text rationale (only required if hallucination or harmful handling present):</label>
          <textarea
            v-model="faultRationale"
            class="textarea is-small"
            placeholder="Please provide a one sentence explanation."
            rows="2"
            maxlength="300"
            :disabled="disabled"
          ></textarea>
          <p v-if="isFaultRationaleRequired && !faultRationale.trim()" class="help is-danger">
            Rationale required when a fault is identified
          </p>
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
import { post } from '../utils/api'

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
        corpus_fidelity: null,
        citation_quality: null,
        relevance: null,
        coherence: null,
        uncertainty: null,
        historical_contextualisation: null
      },
      faults: {
        hallucination: false,
        harmful_handling: false
      },
      scaleComments: {
        corpus_fidelity: '',
        citation_quality: '',
        relevance: '',
        coherence: '',
        uncertainty: '',
        historical_contextualisation: ''
      },
      faultRationale: '',
      isSubmitting: false,
      configData: null
    }
  },
  computed: {
    isFaultRationaleRequired() {
      return this.faults.hallucination || this.faults.harmful_handling
    },
    hasExtendedFeedback() {
      const hasRatings = Object.values(this.ratings).some(rating => rating !== null)
      const hasFaults = Object.values(this.faults).some(fault => fault === true)
      if (!hasRatings && !hasFaults) return false
      // Block submit if any required scale comments are missing
      const requiredCommentsMissing = Object.keys(this.ratings).some(scale => {
        return this.isCommentRequired(scale) && !this.scaleComments[scale].trim()
      })
      if (requiredCommentsMissing) return false
      // Block submit if fault rationale required but missing
      if (this.isFaultRationaleRequired && !this.faultRationale.trim()) return false
      return true
    }
  },
  methods: {
    isCommentRequired(scale) {
      const rating = this.ratings[scale]
      return rating !== null && (rating === 1 || rating === 2 || rating === 5)
    },

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

    async submitExtendedFeedback() {
      if (!this.hasExtendedFeedback || this.isSubmitting) return

      this.isSubmitting = true

      try {
        const chatHistory = this.sessionStore.chatHistory
        const currentQuestion = chatHistory[chatHistory.length - 2]?.content || ''
        const currentAnswer = chatHistory[chatHistory.length - 1]?.content || ''
        const fullCitations = chatHistory[chatHistory.length - 1]?.citations || []

        const feedbackData = {
          qa_id: this.qaId,
          session_id: this.sessionId,
          feedback_type: 'extended',
          timestamp: new Date().toISOString(),
          question: currentQuestion,
          answer: currentAnswer,
          citations: fullCitations,
          trace_id: this.telemetryStore.traceId
        }

        // Include ratings if set
        for (const [key, value] of Object.entries(this.ratings)) {
          if (value !== null) {
            feedbackData[key] = value
          }
        }

        // Include faults if any are selected
        const activeFaults = Object.entries(this.faults).filter(([_, v]) => v === true)
        if (activeFaults.length > 0) {
          feedbackData.faults = this.faults
        }

        // Include fault rationale if provided
        if (this.faultRationale.trim()) {
          feedbackData.faults_rationale = this.faultRationale.trim()
        }

        // Include per-scale comments if provided
        for (const [scale, comment] of Object.entries(this.scaleComments)) {
          if (comment.trim()) {
            feedbackData[`${scale}_comments`] = comment.trim()
          }
        }

        if (this.configData && Object.keys(this.configData).length > 0) {
          feedbackData.test_target = { ...feedbackData.test_target, ...this.configData }
        }

        await post('/feedback', feedbackData, {
          headers: {
            ...this.telemetryStore.telemetryHeaders
          }
        })

        this.$emit('feedback-submitted', 'extended')
        this.resetForm()

      } catch (error) {
        console.error('Error submitting extended feedback:', error)
      } finally {
        this.isSubmitting = false
      }
    },

    resetForm() {
      this.ratings = {
        corpus_fidelity: null,
        citation_quality: null,
        relevance: null,
        coherence: null,
        uncertainty: null,
        historical_contextualisation: null
      }
      this.faults = {
        hallucination: false,
        harmful_handling: false
      }
      this.scaleComments = {
        corpus_fidelity: '',
        citation_quality: '',
        relevance: '',
        coherence: '',
        uncertainty: '',
        historical_contextualisation: ''
      }
      this.faultRationale = ''
    }
  },

  async mounted() {
    await this.fetchConfigData()

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
  margin: 0 0 0.25rem 0;
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
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  max-width: 420px;
  margin: 0 auto;
}

.likert-endpoint {
  font-size: 11px;
  color: #6c757d;
  white-space: nowrap;
  flex-shrink: 0;
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

.scale-comment {
  margin-top: 0.5rem;
  max-width: 420px;
  margin-left: auto;
  margin-right: auto;
}

.scale-comment .textarea {
  resize: vertical;
  min-height: 50px;
  font-size: 13px;
}

.scale-comment .help.is-danger {
  font-size: 12px;
  margin-top: 0.25rem;
}

.faults-section {
  border-top: 1px solid #e9ecef;
  padding-top: 1.5rem;
}

.faults-instruction {
  font-size: 14px;
  color: #495057;
  margin-bottom: 0.75rem;
}

.faults-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
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
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 14px;
  color: #495057;
  cursor: pointer;
}

.fault-rationale {
  margin-top: 0.75rem;
}

.fault-rationale-label {
  display: block;
  font-size: 13px;
  color: #495057;
  margin-bottom: 0.25rem;
}

.fault-rationale .textarea {
  resize: vertical;
  min-height: 50px;
  font-size: 13px;
}

.fault-rationale .help.is-danger {
  font-size: 12px;
  margin-top: 0.25rem;
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
    max-width: 320px;
  }

  .faults-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .feedback-actions {
    flex-direction: column;
  }
}
</style>
