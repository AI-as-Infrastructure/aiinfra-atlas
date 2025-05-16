<template>
  <Transition name="fade">
    <div class="feedback-container">
      <Transition name="slide">
        <div v-if="!showForm" class="feedback-button-container">
          <button class="button is-primary" @click="showForm = true">
            Rate Answer
          </button>
        </div>
        <div v-else class="feedback-form">
          <form @submit.prevent="submitFeedback">
            <div class="field">
              <label class="label">Answer Rating (1-5)</label>
              <div class="control">
                <div class="select is-fullwidth">
                  <select v-model.number="answerRating" required>
                    <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
                  </select>
                </div>
              </div>
            </div>
            <div class="field">
              <label class="label">Citations Rating (1-5)</label>
              <div class="control">
                <div class="select is-fullwidth">
                  <select v-model.number="citationsRating" required>
                    <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
                  </select>
                </div>
              </div>
            </div>
            <div class="field">
              <label class="label">Comments (Optional)</label>
              <div class="control">
                <textarea class="textarea" v-model="feedbackText"></textarea>
              </div>
            </div>
            <div class="field is-grouped">
              <div class="control">
                <button 
                  class="button is-success" 
                  type="submit" 
                  :class="{ 'is-loading': isSubmitting }"
                  :disabled="isSubmitting"
                >
                  Submit Feedback
                </button>
              </div>
              <div class="control">
                <button 
                  class="button" 
                  @click="closeForm" 
                  :disabled="isSubmitting"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { useSessionStore } from '@/stores/session'
import { useSocketStore } from '@/stores/socket'

// No props needed since visibility is controlled by parent component
const props = defineProps({})

const emit = defineEmits(['feedback-submitted'])

const sessionStore = useSessionStore()
const socketStore = useSocketStore()
const { chatHistory, sessionId, qaId } = storeToRefs(sessionStore)

// Store the session ID associated with the current QA ID to ensure feedback is associated with the correct session
const associatedSessionId = ref(sessionId.value)

// State
const showForm = ref(false)
const isSubmitting = ref(false)
const answerRating = ref(1)
const citationsRating = ref(1)
const feedbackText = ref('')
const feedbackSubmitted = ref(false)

// Add transition delay for smoother animations
const TRANSITION_DELAY = 300; // milliseconds

// Reset form on mount and whenever qaId changes
import { onMounted } from 'vue'

onMounted(() => {
  resetForm();
  // Store the current session ID on mount
  if (qaId.value) {
    associatedSessionId.value = sessionId.value;
  }
})

watch(() => qaId.value, (newVal, oldVal) => {
  if (newVal && newVal !== oldVal) {
    resetForm();
    // Store the current session ID when QA ID changes
    associatedSessionId.value = sessionId.value;
  }
})

// Methods
function resetForm() {
  showForm.value = false;
  isSubmitting.value = false;
  answerRating.value = 1;
  citationsRating.value = 1;
  feedbackText.value = '';
}

function closeForm() {
  if (!isSubmitting.value) {
    showForm.value = false;
    // Form is closed but feedback is not submitted
  }
}

async function submitFeedback() {
  if (isSubmitting.value || !qaId.value) return
  
  isSubmitting.value = true
  console.log('Submitting feedback for qa_id:', qaId.value)
  
  // Set a timeout to ensure we don't hang forever if there's an issue
  const submissionTimeout = setTimeout(() => {
    if (isSubmitting.value) {
      console.error('Feedback submission timed out')
      isSubmitting.value = false
      // Don't emit feedback-submitted event on timeout
    }
  }, 10000) // 10 second timeout
  
  try {
    // Check WebSocket connection status and try to reconnect if needed
    if (!socketStore.connected) {
      console.log('WebSocket not connected, attempting to reconnect...')
      socketStore.initializeSocket()
      
      // Wait for connection with timeout
      let attempts = 0;
      const maxAttempts = 3;
      const attemptDelay = 1000;
      
      while (!socketStore.connected && attempts < maxAttempts) {
        console.log(`Connection attempt ${attempts + 1}/${maxAttempts}...`);
        await new Promise(resolve => setTimeout(resolve, attemptDelay));
        attempts++;
      }
      
      if (!socketStore.connected) {
        throw new Error(`Could not establish WebSocket connection after ${maxAttempts} attempts. Last error: ${socketStore.lastError}`);
      }
    }
    
    const feedbackData = {
      type: 'feedback',
      data: {
        session_id: associatedSessionId.value, // Use the stored session ID associated with this QA interaction
        qa_id: qaId.value,
        feedback: {
          answer_rating: answerRating.value,
          citations_rating: citationsRating.value,
          feedback_text: feedbackText.value,
          question: chatHistory.value[chatHistory.value.length - 2]?.content,
          answer: chatHistory.value[chatHistory.value.length - 1]?.content,
          citations: chatHistory.value[chatHistory.value.length - 1]?.citations || [],
          timestamp: new Date().toISOString(),
          feedback_type: "user_rating",
          question_text: chatHistory.value[chatHistory.value.length - 2]?.content.substring(0, 500),
          answer_length: chatHistory.value[chatHistory.value.length - 1]?.content.length || 0,
          feedback_time_ms: Date.now(),
          feedback_tags: extractFeedbackTags()
        }
      }
    }
    
    console.log('Sending feedback data:', feedbackData)

    // Send feedback through WebSocket with retries
    let sent = false;
    let retries = 0;
    const maxRetries = 2;
    
    while (!sent && retries <= maxRetries) {
      sent = socketStore.sendMessage(feedbackData);
      if (!sent) {
        retries++;
        if (retries <= maxRetries) {
          console.log(`Retrying feedback submission (attempt ${retries}/${maxRetries})...`);
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
    }
    
    if (!sent) {
      throw new Error('Failed to send feedback message after retries');
    }
    
    // Clear the timeout since we got a response
    clearTimeout(submissionTimeout)
    
    // Emit event to parent component
    emit('feedback-submitted')
    
    // Reset the form after a short delay to allow transitions to complete
    setTimeout(() => {
      resetForm()
      feedbackSubmitted.value = true
    }, TRANSITION_DELAY);
    showForm.value = false;
    
    // Add a timeout to handle cases where the server doesn't respond
    const feedbackTimeout = setTimeout(() => {
      if (!sessionStore.hasFeedbackBeenSubmitted(qaId.value)) {
        console.warn('No feedback confirmation received from server after 5 seconds')
        isSubmitting.value = false
        showForm.value = true // Show the form again
        alert('The server did not confirm your feedback submission. Please try again.')
      }
    }, 5000)

    // Clean up timeout if component is unmounted
    onBeforeUnmount(() => {
      clearTimeout(feedbackTimeout);
    })
  } catch (error) {
    console.error('Error submitting feedback:', error)
    isSubmitting.value = false
    clearTimeout(submissionTimeout)
    
    // Provide visual feedback about the error (could be enhanced with a UI notification)
    feedbackText.value += '\n\nNote: There was an issue submitting your feedback. Please try again.'
  }
}

function extractFeedbackTags() {
  const tags = []
  
  const text = feedbackText.value.toLowerCase()
  
  const positiveTerms = ['good', 'great', 'excellent', 'helpful', 'accurate', 'clear']
  const negativeTerms = ['poor', 'bad', 'wrong', 'incorrect', 'confusing', 'unclear']
  
  let isPositive = positiveTerms.some(term => text.includes(term))
  let isNegative = negativeTerms.some(term => text.includes(term))
  
  if (isPositive && !isNegative) tags.push('positive')
  if (isNegative && !isPositive) tags.push('negative')
  if (isPositive && isNegative) tags.push('mixed')
  
  if (text.includes('citation') || text.includes('source') || text.includes('reference')) {
    tags.push('citations_feedback')
  }
  
  if (text.includes('clarity') || text.includes('understand') || text.includes('clear')) {
    tags.push('clarity_feedback')
  }
  
  if (text.includes('accuracy') || text.includes('correct') || text.includes('accurate')) {
    tags.push('accuracy_feedback')
  }
  
  if (answerRating.value >= 4) tags.push('high_answer_rating')
  if (answerRating.value <= 2) tags.push('low_answer_rating')
  if (citationsRating.value >= 4) tags.push('high_citations_rating')
  if (citationsRating.value <= 2) tags.push('low_citations_rating')
  
  return tags
}
</script>

<style scoped>
.feedback-container {
  padding: 0;
  border: none;
  background-color: transparent;
}

.feedback-button-container {
  padding: 0.5rem 0;
}
.feedback-button-container .button {
  width: 100%;
  background: #4CAF50 !important; /* Green */
  color: #fff !important;
  border: none !important;
  border-radius: 2px !important;
  box-shadow: none !important;
  font-size: 1rem;
  padding: 0.25rem 1.1rem;
  font-weight: 500;
  transition: background 0.2s;
  display: block;
}
.feedback-button-container .button:hover:not(:disabled) {
  background: #388E3C !important; /* Darker green on hover */
}
.feedback-button-container .button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-form .button,
.feedback-form .button.is-success {
  background: #000 !important;
  color: #fff !important;
  border: none !important;
  border-radius: 2px !important;
  box-shadow: none !important;
  font-size: 1rem;
  padding: 0.25rem 1.1rem;
  font-weight: 500;
  transition: background 0.2s;
  min-width: 120px;
  max-width: 100%;
  white-space: nowrap;
}

.feedback-form .field.is-grouped {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.feedback-form .control {
  flex: 1 1 auto;
  min-width: 120px;
  max-width: 100%;
}

@media (max-width: 600px) {
  .feedback-form .field.is-grouped {
    flex-direction: column;
    gap: 0.5rem;
  }
  .feedback-form .control {
    min-width: 0;
    width: 100%;
  }
  .feedback-form .button {
    width: 100%;
  }
}

.feedback-form .button:hover:not(:disabled),
.feedback-form .button.is-success:hover:not(:disabled) {
  background: #222 !important;
}
.feedback-form .button:disabled,
.feedback-form .button.is-success:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-form {
  max-width: 500px;
  margin: 0 auto 2rem auto;
  padding: 0.5rem 1rem 1rem 1rem;
  background-color: #fff;
  border-radius: 6px;
  border: 1px solid #ddd;
  box-shadow: none;
}

.feedback-form .field {
  margin-bottom: 1rem;
}

.feedback-form .label {
  color: #000 !important;
  font-weight: 600;
}

.feedback-form select,
.feedback-form textarea {
  background: #fff !important;
  color: #111 !important;
  border: 1px solid #e0e0e0 !important;
  border-radius: 3px;
  box-shadow: none !important;
}

/* Make dropdown arrow black */
.feedback-form .select::after {
  border-color: #000 !important;
}

.notification {
  font-family: monospace;
  font-size: 0.9em;
}

.notification pre {
  background-color: #f8f8f8;
  padding: 0.5rem;
  border-radius: 4px;
  margin-top: 0.5rem;
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Slide transition */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateY(20px);
  opacity: 0;
}
</style>