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
      <!-- Prominent Question Display -->
      <div class="question-section">
        <div class="card">
          <div class="card-header has-background-primary">
            <h4 class="card-header-title has-text-white">
              <i class="fas fa-question-circle mr-2"></i>
              Question
            </h4>
          </div>
          <div class="card-content">
            <div class="content has-text-weight-medium" style="font-size: 1.1rem; line-height: 1.6;">
              {{ session.question }}
            </div>
          </div>
        </div>
      </div>

      <!-- Prominent Answer Display -->
      <div class="answer-section">
        <div class="card">
          <div class="card-header has-background-info">
            <h4 class="card-header-title has-text-white">
              <i class="fas fa-comment-dots mr-2"></i>
              Answer
            </h4>
          </div>
          <div class="card-content">
            <div class="content" style="font-size: 1rem; line-height: 1.6;">
              <div v-html="session.answer"></div>
              
              <div v-if="session.citations && session.citations.length > 0" class="citations-section">
                <hr class="my-4">
                <h6 class="title is-6 has-text-grey-dark">
                  <i class="fas fa-book mr-2"></i>
                  Sources Used:
                </h6>
                <div class="tags">
                  <span 
                    v-for="(citation, index) in session.citations" 
                    :key="index"
                    class="tag is-info is-light is-medium"
                  >
                    <i class="fas fa-external-link-alt mr-1"></i>
                    {{ citation.source }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Original Feedback Display -->
      <div class="original-feedback-section">
        <div class="card">
          <div class="card-header has-background-success">
            <h4 class="card-header-title has-text-white">
              <i class="fas fa-user-check mr-2"></i>
              Original User Feedback
            </h4>
            <span class="tag is-light">{{ session.original_feedback?.user_category || 'Unknown User' }}</span>
          </div>
          <div class="card-content">
            <div class="columns is-multiline">
              <div v-if="session.original_feedback?.relevance" class="column is-6">
                <div class="feedback-metric">
                  <span class="metric-label">Relevance:</span>
                  <span class="metric-value">{{ session.original_feedback.relevance }}/5</span>
                  <div class="metric-stars">
                    <span v-for="i in 5" :key="i" 
                          :class="['star', i <= session.original_feedback.relevance ? 'filled' : 'empty']">
                      ★
                    </span>
                  </div>
                </div>
              </div>
              <div v-if="session.original_feedback?.clarity" class="column is-6">
                <div class="feedback-metric">
                  <span class="metric-label">Clarity:</span>
                  <span class="metric-value">{{ session.original_feedback.clarity }}/5</span>
                  <div class="metric-stars">
                    <span v-for="i in 5" :key="i" 
                          :class="['star', i <= session.original_feedback.clarity ? 'filled' : 'empty']">
                      ★
                    </span>
                  </div>
                </div>
              </div>
              <div v-if="session.original_feedback?.factual_accuracy" class="column is-6">
                <div class="feedback-metric">
                  <span class="metric-label">Factual Accuracy:</span>
                  <span class="metric-value">{{ session.original_feedback.factual_accuracy }}/5</span>
                  <div class="metric-stars">
                    <span v-for="i in 5" :key="i" 
                          :class="['star', i <= session.original_feedback.factual_accuracy ? 'filled' : 'empty']">
                      ★
                    </span>
                  </div>
                </div>
              </div>
              <div v-if="session.original_feedback?.source_quality" class="column is-6">
                <div class="feedback-metric">
                  <span class="metric-label">Source Quality:</span>
                  <span class="metric-value">{{ session.original_feedback.source_quality }}/5</span>
                  <div class="metric-stars">
                    <span v-for="i in 5" :key="i" 
                          :class="['star', i <= session.original_feedback.source_quality ? 'filled' : 'empty']">
                      ★
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="session.original_feedback?.feedback_text" class="mt-4">
              <strong class="has-text-grey-dark">Comments:</strong>
              <p class="mt-2 has-background-light p-3" style="border-radius: 4px; font-style: italic;">
                "{{ session.original_feedback.feedback_text }}"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Inter-rater Feedback Form -->
    <div class="inter-rater-feedback-section">
      <div class="card">
        <div class="card-header has-background-warning">
          <h4 class="card-header-title">
            <i class="fas fa-star mr-2"></i>
            Your Inter-rater Assessment
          </h4>
        </div>
        <div class="card-content">
          <div class="notification is-info is-light mb-4">
            <p><strong>Instructions:</strong> Rate this question-answer interaction independently, without being influenced by the original feedback above.</p>
          </div>
          
          <!-- Streamlined Rating Grid -->
          <div class="columns is-multiline">
            <div class="column is-6">
              <div class="field">
                <label class="label has-text-weight-bold">Relevance</label>
                <div class="control">
                  <div class="rating-buttons">
                    <button 
                      v-for="n in 5" :key="n"
                      @click="feedback.relevance = n"
                      :class="['button', 'rating-btn', feedback.relevance == n ? 'is-primary' : 'is-light']"
                    >
                      {{ n }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="column is-6">
              <div class="field">
                <label class="label has-text-weight-bold">Clarity</label>
                <div class="control">
                  <div class="rating-buttons">
                    <button 
                      v-for="n in 5" :key="n"
                      @click="feedback.clarity = n"
                      :class="['button', 'rating-btn', feedback.clarity == n ? 'is-primary' : 'is-light']"
                    >
                      {{ n }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="column is-6">
              <div class="field">
                <label class="label has-text-weight-bold">Factual Accuracy</label>
                <div class="control">
                  <div class="rating-buttons">
                    <button 
                      v-for="n in 5" :key="n"
                      @click="feedback.factual_accuracy = n"
                      :class="['button', 'rating-btn', feedback.factual_accuracy == n ? 'is-primary' : 'is-light']"
                    >
                      {{ n }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="column is-6">
              <div class="field">
                <label class="label has-text-weight-bold">Source Quality</label>
                <div class="control">
                  <div class="rating-buttons">
                    <button 
                      v-for="n in 5" :key="n"
                      @click="feedback.source_quality = n"
                      :class="['button', 'rating-btn', feedback.source_quality == n ? 'is-primary' : 'is-light']"
                    >
                      {{ n }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Comments Section -->
          <div class="field mt-4">
            <label class="label has-text-weight-bold">Additional Comments (Optional)</label>
            <div class="control">
              <textarea 
                class="textarea" 
                v-model="feedback.feedback_text"
                placeholder="Any additional observations about this interaction..."
                rows="3"
              ></textarea>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="field is-grouped is-grouped-centered mt-5">
            <div class="control">
              <button 
                @click="submitFeedback" 
                class="button is-success is-large"
                :disabled="!isFormValid || isSubmitting"
              >
                <span class="icon">
                  <i class="fas fa-check"></i>
                </span>
                <span>{{ isSubmitting ? 'Submitting...' : 'Submit Rating' }}</span>
              </button>
            </div>
            <div class="control">
              <button @click="skipSession" class="button is-light is-large">
                <span class="icon">
                  <i class="fas fa-forward"></i>
                </span>
                <span>Skip Session</span>
              </button>
            </div>
          </div>
          
          <!-- Progress Indicator -->
          <div class="has-text-centered mt-4">
            <p class="has-text-grey">
              <i class="fas fa-info-circle mr-1"></i>
              Session {{ currentIndex + 1 }} of {{ totalSessions }}
            </p>
            <div v-if="!isFormValid" class="has-text-danger mt-2">
              <small>Please rate all four criteria to continue</small>
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
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 1rem;
}

.session-header {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #3273dc;
}

.conversation-container {
  margin-bottom: 2rem;
}

/* Question and Answer Sections */
.question-section,
.answer-section,
.original-feedback-section {
  margin-bottom: 1.5rem;
}

.question-section .card {
  border-left: 4px solid #3273dc;
}

.answer-section .card {
  border-left: 4px solid #209cee;
}

.original-feedback-section .card {
  border-left: 4px solid #48c774;
}

.citations-section {
  background-color: #fafafa;
  border-radius: 6px;
  padding: 1rem;
  margin-top: 1rem;
}

/* Original Feedback Metrics */
.feedback-metric {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.metric-label {
  font-weight: 600;
  min-width: 120px;
}

.metric-value {
  font-weight: bold;
  color: #3273dc;
}

.metric-stars {
  display: flex;
  gap: 2px;
}

.star {
  font-size: 1rem;
}

.star.filled {
  color: #ffdd57;
}

.star.empty {
  color: #ddd;
}

/* Inter-rater Feedback Form */
.inter-rater-feedback-section {
  margin-top: 3rem;
}

.inter-rater-feedback-section .card {
  border-left: 4px solid #ffdd57;
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

/* Rating Buttons */
.rating-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-start;
}

.rating-btn {
  min-width: 50px;
  font-weight: bold;
  transition: all 0.2s ease;
}

.rating-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.rating-btn.is-primary {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(50, 115, 220, 0.3);
}

/* Responsive Design */
@media (max-width: 768px) {
  .inter-rater-playback {
    padding: 0 0.5rem;
  }
  
  .session-header {
    padding: 1rem;
  }
  
  .rating-buttons {
    justify-content: center;
  }
  
  .field.is-grouped.is-grouped-centered {
    flex-direction: column;
  }
  
  .field.is-grouped.is-grouped-centered .control {
    margin-bottom: 0.5rem;
  }
}

/* Visual Improvements */
.card {
  transition: box-shadow 0.3s ease;
}

.card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.notification.is-info.is-light {
  border-left: 4px solid #209cee;
}
</style>
