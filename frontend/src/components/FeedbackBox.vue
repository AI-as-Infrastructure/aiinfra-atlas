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
              <label class="label">Relevance (1–5):</label>
              <div class="control">
                <select v-model="relevance" class="input">
                  <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
                </select>
              </div>
            </div>
            <div class="field">
              <label class="label">Factual Accuracy:</label>
              <div class="control">
                <label><input type="radio" value="true" v-model="factualAccuracy"> True</label>
                <label><input type="radio" value="false" v-model="factualAccuracy"> False</label>
              </div>
            </div>
            <div class="field">
              <label class="label">Source Quality (1–5):</label>
              <div class="control">
                <select v-model="sourceQuality" class="input">
                  <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
                </select>
              </div>
            </div>
            <div class="field">
              <label class="label">Clarity (1–5):</label>
              <div class="control">
                <select v-model="clarity" class="input">
                  <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
                </select>
              </div>
            </div>
            <div class="field">
              <label class="label">Tags:</label>
              <div class="control">
                <label><input type="checkbox" value="hallucination" v-model="tags"> Hallucination</label>
                <label><input type="checkbox" value="anachronism" v-model="tags"> Anachronism</label>
                <label><input type="checkbox" value="biased" v-model="tags"> Biased</label>
                <label><input type="checkbox" value="off-topic" v-model="tags"> Off-topic</label>
                <label><input type="checkbox" value="well-sourced" v-model="tags"> Well-sourced</label>
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
                  Submit
                </button>
              </div>
              <div class="control">
                <button 
                  class="button" 
                  @click="closeForm" 
                  :disabled="false"
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
import { ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useSessionStore } from '@/stores/session'
import { useSocketStore } from '@/stores/socket'
import { onMounted } from 'vue'

// No props needed since visibility is controlled by parent component
const props = defineProps({})

const emit = defineEmits(['feedback-submitted'])

const sessionStore = useSessionStore()
const socketStore = useSocketStore()
const { chatHistory, sessionId, qaId } = storeToRefs(sessionStore)

// Store the session ID associated with the current QA ID to ensure feedback is associated with the correct session
const associatedSessionId = ref(sessionId.value)

// State - only Phoenix-compatible fields
const showForm = ref(false)
const isSubmitting = ref(false)
const relevance = ref(3)
const factualAccuracy = ref('true')
const sourceQuality = ref(3)
const clarity = ref(3)
const tags = ref([])
const feedbackText = ref('')
const configData = ref(null)

// Fetch config data on component mount
onMounted(async () => {
  try {
    const response = await fetch('/api/config');
    if (response.ok) {
      configData.value = await response.json();
    }
  } catch (error) {
    console.error('Error fetching config data:', error);
  }
  
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
  relevance.value = 3;
  factualAccuracy.value = 'true';
  sourceQuality.value = 3;
  clarity.value = 3;
  tags.value = [];
  feedbackText.value = '';
}

function closeForm() {
  showForm.value = false;
}

async function submitFeedback() {
  if (isSubmitting.value || !qaId.value) return
  
  isSubmitting.value = true
  console.log('Submitting Phoenix-compatible feedback for qa_id:', qaId.value)
  
  try {
    // Get the current question and answer from the chat history
    const currentQuestion = chatHistory.value[chatHistory.value.length - 2]?.content || '';
    const currentAnswer = chatHistory.value[chatHistory.value.length - 1]?.content || '';
    
    // Get the full citations - this is the same data used in the "view all citations" modal
    // The citations are stored directly on the chat message object
    const fullCitations = chatHistory.value[chatHistory.value.length - 1]?.citations || [];
    
    // Prepare Phoenix-compatible feedback data
    const feedbackData = {
      session_id: associatedSessionId.value,
      qa_id: qaId.value,
      relevance: Number(relevance.value),
      factual_accuracy: factualAccuracy.value === 'true',
      source_quality: Number(sourceQuality.value),
      clarity: Number(clarity.value),
      tags: tags.value,
      feedback_text: feedbackText.value,
      test_target: configData.value || {},
      question: currentQuestion,
      answer: currentAnswer,
      citations: fullCitations,
      timestamp: new Date().toISOString()
    };
    
    console.log('Phoenix feedback data:', feedbackData);
    
    // Submit via HTTP POST
    const response = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedbackData)
    });
    
    if (!response.ok) {
      throw new Error('Feedback submission failed');
    }
    
    const result = await response.json();
    console.log('Feedback submission result:', result);
    
    // Emit event to parent component
    emit('feedback-submitted')
    
    // Reset form
    resetForm();
    
  } catch (error) {
    console.error('Error submitting feedback:', error)
    alert('There was an issue submitting your feedback. Please try again.');
  } finally {
    isSubmitting.value = false
  }
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