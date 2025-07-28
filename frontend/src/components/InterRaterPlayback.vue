<template>
  <div class="inter-rater-playback">
    <div class="session-header">
      <div class="columns">
        <div class="column">
          <h3 class="title is-5">Session from {{ formatDate(session.timestamp) }}</h3>
          <p class="subtitle is-6">Original rating provided by {{ session.original_feedback?.user_category || 'Unknown User' }}</p>
        </div>
        <div class="column is-narrow">
          <div class="tags">
            <span class="tag is-info">Session {{ currentIndex + 1 }} of {{ totalSessions }}</span>
            <span class="tag is-light">{{ session.inter_rater_count }} previous ratings</span>
          </div>
        </div>
      </div>
    </div>

    <div class="conversation-container">
      <div class="message-group">
        <div class="message is-primary">
          <div class="message-header">
            <p>Question</p>
          </div>
          <div class="message-body">
            {{ session.question }}
          </div>
        </div>
      </div>

      <div class="message-group">
        <div class="message is-link">
          <div class="message-header">
            <p>Answer</p>
          </div>
          <div class="message-body">
            <div v-html="session.answer"></div>
            
            <div v-if="session.citations && session.citations.length > 0" class="citations mt-4">
              <h6 class="subtitle is-6">Sources:</h6>
              <div class="tags">
                <span 
                  v-for="(citation, index) in session.citations" 
                  :key="index"
                  class="tag is-light"
                >
                  {{ citation.source }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="original-feedback">
        <div class="message is-info">
          <div class="message-header">
            <p>Original User Feedback</p>
          </div>
          <div class="message-body">
            <div class="columns is-multiline">
              <div v-if="session.original_feedback?.relevance" class="column is-half">
                <strong>Relevance:</strong> {{ session.original_feedback.relevance }}/5
              </div>
              <div v-if="session.original_feedback?.clarity" class="column is-half">
                <strong>Clarity:</strong> {{ session.original_feedback.clarity }}/5
              </div>
              <div v-if="session.original_feedback?.factual_accuracy" class="column is-half">
                <strong>Factual Accuracy:</strong> {{ session.original_feedback.factual_accuracy }}/5
              </div>
              <div v-if="session.original_feedback?.source_quality" class="column is-half">
                <strong>Source Quality:</strong> {{ session.original_feedback.source_quality }}/5
              </div>
            </div>
            <div v-if="session.original_feedback?.feedback_text" class="mt-3">
              <strong>Comments:</strong> {{ session.original_feedback.feedback_text }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="inter-rater-feedback-section">
      <div class="message is-warning">
        <div class="message-header">
          <p>Your Inter-rater Feedback</p>
        </div>
        <div class="message-body">
          <p class="mb-4">Please provide your independent assessment of this interaction:</p>
          
          <div class="field">
            <label class="label">Relevance (1-5)</label>
            <div class="control">
              <div class="select is-fullwidth">
                <select v-model="feedback.relevance">
                  <option value="">Select rating...</option>
                  <option value="1">1 - Not relevant</option>
                  <option value="2">2 - Somewhat relevant</option>
                  <option value="3">3 - Moderately relevant</option>
                  <option value="4">4 - Very relevant</option>
                  <option value="5">5 - Perfectly relevant</option>
                </select>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="label">Clarity (1-5)</label>
            <div class="control">
              <div class="select is-fullwidth">
                <select v-model="feedback.clarity">
                  <option value="">Select rating...</option>
                  <option value="1">1 - Very unclear</option>
                  <option value="2">2 - Somewhat unclear</option>
                  <option value="3">3 - Moderately clear</option>
                  <option value="4">4 - Very clear</option>
                  <option value="5">5 - Perfectly clear</option>
                </select>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="label">Factual Accuracy (1-5)</label>
            <div class="control">
              <div class="select is-fullwidth">
                <select v-model="feedback.factual_accuracy">
                  <option value="">Select rating...</option>
                  <option value="1">1 - Inaccurate</option>
                  <option value="2">2 - Mostly inaccurate</option>
                  <option value="3">3 - Partly accurate</option>
                  <option value="4">4 - Mostly accurate</option>
                  <option value="5">5 - Completely accurate</option>
                </select>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="label">Source Quality (1-5)</label>
            <div class="control">
              <div class="select is-fullwidth">
                <select v-model="feedback.source_quality">
                  <option value="">Select rating...</option>
                  <option value="1">1 - Poor sources</option>
                  <option value="2">2 - Fair sources</option>
                  <option value="3">3 - Good sources</option>
                  <option value="4">4 - Very good sources</option>
                  <option value="5">5 - Excellent sources</option>
                </select>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="label">Additional Comments</label>
            <div class="control">
              <textarea 
                class="textarea" 
                v-model="feedback.feedback_text"
                placeholder="Any additional observations about this interaction..."
                rows="3"
              ></textarea>
            </div>
          </div>

          <div class="field is-grouped">
            <div class="control">
              <button 
                @click="submitFeedback" 
                class="button is-primary"
                :disabled="!isFormValid || isSubmitting"
              >
                {{ isSubmitting ? 'Submitting...' : 'Submit Inter-rating' }}
              </button>
            </div>
            <div class="control">
              <button @click="skipSession" class="button is-light">
                Skip This Session
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'InterRaterPlayback',
  props: {
    session: {
      type: Object,
      required: true
    },
    currentIndex: {
      type: Number,
      required: true
    },
    totalSessions: {
      type: Number,
      required: true
    }
  },
  emits: ['submit-feedback', 'skip-session'],
  setup(props, { emit }) {
    const feedback = ref({
      relevance: '',
      clarity: '',
      factual_accuracy: '',
      source_quality: '',
      feedback_text: ''
    })
    
    const isSubmitting = ref(false)

    const isFormValid = computed(() => {
      return feedback.value.relevance && 
             feedback.value.clarity && 
             feedback.value.factual_accuracy && 
             feedback.value.source_quality
    })

    const formatDate = (dateString) => {
      try {
        const date = new Date(dateString)
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
      } catch (error) {
        return dateString
      }
    }

    const submitFeedback = async () => {
      if (!isFormValid.value || isSubmitting.value) return

      isSubmitting.value = true
      
      try {
        const feedbackData = {
          session_id: props.session.session_id,
          qa_id: props.session.qa_id,
          relevance: parseInt(feedback.value.relevance),
          clarity: parseInt(feedback.value.clarity),
          factual_accuracy: parseInt(feedback.value.factual_accuracy),
          source_quality: parseInt(feedback.value.source_quality),
          feedback_text: feedback.value.feedback_text,
          is_inter_rater: true,
          original_span_id: props.session.span_id,
          timestamp: new Date().toISOString()
        }

        emit('submit-feedback', feedbackData)
      } catch (error) {
        console.error('Error submitting inter-rater feedback:', error)
      } finally {
        isSubmitting.value = false
      }
    }

    const skipSession = () => {
      emit('skip-session')
    }

    return {
      feedback,
      isSubmitting,
      isFormValid,
      formatDate,
      submitFeedback,
      skipSession
    }
  }
}
</script>

<style scoped>
.inter-rater-playback {
  max-width: 900px;
  margin: 0 auto;
}

.session-header {
  margin-bottom: 2rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.conversation-container {
  margin-bottom: 2rem;
}

.message-group {
  margin-bottom: 1.5rem;
}

.citations {
  border-top: 1px solid #e0e0e0;
  padding-top: 1rem;
}

.original-feedback {
  margin-bottom: 2rem;
}

.inter-rater-feedback-section {
  position: sticky;
  bottom: 0;
  background: white;
  padding: 1rem 0;
  border-top: 2px solid #f0f0f0;
}
</style>
