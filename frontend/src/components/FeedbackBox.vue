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
              <div class="field-label-with-info">
                <label class="label">Factual Accuracy</label>
                <div class="tooltip-container">
                  <span class="info-icon">ⓘ</span>
                  <div class="tooltip-text">Rate the factual accuracy of the answer:
True - The answer is factually accurate
Mixed - The answer contains both accurate and inaccurate information
False - The answer contains factual errors</div>
                </div>
              </div>
              <div class="control checkbox-group">
                <label class="checkbox-label"><input type="checkbox" :checked="factualAccuracy === 'true'" @change="factualAccuracy = $event.target.checked ? 'true' : (factualAccuracy === 'mixed' ? 'mixed' : 'false')"> True</label> 
                <label class="checkbox-label"><input type="checkbox" :checked="factualAccuracy === 'mixed'" @change="factualAccuracy = $event.target.checked ? 'mixed' : (factualAccuracy === 'true' ? 'true' : 'false')"> Mixed</label> 
                <label class="checkbox-label"><input type="checkbox" :checked="factualAccuracy === 'false'" @change="factualAccuracy = $event.target.checked ? 'false' : (factualAccuracy === 'mixed' ? 'mixed' : 'true')"> False</label>
              </div>
            </div>
            <div class="field">
              <div class="field-label-with-info">
                <label class="label">Relevance</label>
                <div class="tooltip-container">
                  <span class="info-icon">ⓘ</span>
                  <div class="tooltip-text">Rate how relevant the answer is to the question (1-5):
1 - Not relevant
2 - Somewhat relevant
3 - Moderately relevant
4 - Very relevant
5 - Perfectly relevant</div>
                </div>
              </div>
              <div class="control">
                <select v-model="relevance" class="input">
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                  <option :value="3">3</option>
                  <option :value="4">4</option>
                  <option :value="5">5</option>
                </select>
              </div>
            </div>
            <div class="field">
              <div class="field-label-with-info">
                <label class="label">Source Quality</label>
                <div class="tooltip-container">
                  <span class="info-icon">ⓘ</span>
                  <div class="tooltip-text">Rate the quality of sources used (1-5):
1 - Poor sources
2 - Fair sources
3 - Good sources
4 - Very good sources
5 - Excellent sources</div>
                </div>
              </div>
              <div class="control">
                <select v-model="sourceQuality" class="input">
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                  <option :value="3">3</option>
                  <option :value="4">4</option>
                  <option :value="5">5</option>
                </select>
              </div>
            </div>
            <div class="field">
              <div class="field-label-with-info">
                <label class="label">Clarity</label>
                <div class="tooltip-container">
                  <span class="info-icon">ⓘ</span>
                  <div class="tooltip-text">Rate how clear the answer is (1-5):
1 - Very unclear
2 - Somewhat unclear
3 - Moderately clear
4 - Very clear
5 - Perfectly clear</div>
                </div>
              </div>
              <div class="control">
                <select v-model="clarity" class="input">
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                  <option :value="3">3</option>
                  <option :value="4">4</option>
                  <option :value="5">5</option>
                </select>
              </div>
            </div>
            <div class="field">
              <div class="field-label-with-info">
                <label class="label">Question Difficulty</label>
                <div class="tooltip-container">
                  <span class="info-icon">ⓘ</span>
                  <div class="tooltip-text">Rate how difficult the question is for the LLM (1-5):
1 - Very easy
2 - Easy
3 - Moderate
4 - Difficult
5 - Very difficult</div>
                </div>
              </div>
              <div class="control">
                <select v-model="questionRating" class="input">
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                  <option :value="3">3</option>
                  <option :value="4">4</option>
                  <option :value="5">5</option>
                </select>
              </div>
            </div>
            <div class="field">
              <label class="label">Tags:</label>
              <div class="control checkbox-group">
                <label class="checkbox-label"><input type="checkbox" value="hallucination" v-model="tags"> Hallucination</label> 
                <label class="checkbox-label"><input type="checkbox" value="anachronism" v-model="tags"> Anachronism</label> 
                <label class="checkbox-label"><input type="checkbox" value="biased" v-model="tags"> Biased</label> 
                <label class="checkbox-label"><input type="checkbox" value="off-topic" v-model="tags"> Off-topic</label> 
                <label class="checkbox-label"><input type="checkbox" value="well-sourced" v-model="tags"> Well-sourced</label>
              </div>
            </div>
            <div class="field">
              <div class="field-label-with-info">
                <label class="label">Comments</label>
                <div class="tooltip-container">
                  <span class="info-icon">ⓘ</span>
                  <div class="tooltip-text">Optionally, provide free text comments</div>
                </div>
              </div>
              <div class="control">
                <textarea class="textarea" v-model="feedbackText"></textarea>
              </div>
            </div>
            <div class="field">
              <div class="field-label-with-info">
                <label class="label">Model Answer</label>
                <div class="tooltip-container">
                  <span class="info-icon">ⓘ</span>
                  <div class="tooltip-text">Optionally, provide a model answer</div>
                </div>
              </div>
              <div class="control">
                <textarea class="textarea" v-model="modelAnswer"></textarea>
              </div>
            </div>
            <div class="action-buttons">
              <button 
                class="small-button submit-button" 
                type="submit" 
                :class="{ 'is-loading': isSubmitting }"
                :disabled="isSubmitting"
              >
                Submit
              </button>
              <button 
                class="small-button cancel-button" 
                @click="closeForm" 
                type="button"
              >
                Cancel
              </button>
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
import { useTelemetryStore } from '@/stores/telemetry'
import { onMounted } from 'vue'

// No props needed since visibility is controlled by parent component
const props = defineProps({})

const emit = defineEmits(['feedback-submitted'])

const sessionStore = useSessionStore()
const socketStore = useSocketStore()
const telemetryStore = useTelemetryStore()
const { chatHistory, sessionId, qaId } = storeToRefs(sessionStore)
const { traceId } = storeToRefs(telemetryStore)

// Store the session ID associated with the current QA ID to ensure feedback is associated with the correct session
const associatedSessionId = ref(sessionId.value)

// State - only Phoenix-compatible fields
const showForm = ref(false)
const isSubmitting = ref(false)
const relevance = ref(3)
const factualAccuracy = ref('true')
const sourceQuality = ref(3)
const clarity = ref(3)
const questionRating = ref(3)
const tags = ref([])
const feedbackText = ref('')
const modelAnswer = ref('')
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
  questionRating.value = 3;
  tags.value = [];
  feedbackText.value = '';
  modelAnswer.value = '';
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
      trace_id: traceId.value,  // Include trace_id for telemetry correlation
      relevance: Number(relevance.value),
      factual_accuracy: factualAccuracy.value,  // Now passing the string value directly: 'true', 'false', or 'mixed'
      source_quality: Number(sourceQuality.value),
      clarity: Number(clarity.value),
      question_rating: Number(questionRating.value),
      tags: tags.value,
      feedback_text: feedbackText.value,
      model_answer: modelAnswer.value,
      test_target: configData.value || {},
      question: currentQuestion,
      answer: currentAnswer,
      citations: fullCitations,
      timestamp: new Date().toISOString()
    };
    
    console.log('Phoenix feedback data with trace_id:', feedbackData);
    
    // Submit via HTTP POST with telemetry headers
    const response = await fetch('/api/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Trace-Id': traceId.value,  // Include trace_id in headers
        'X-Session-Id': associatedSessionId.value
      },
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
  margin-bottom: 1.25rem;
}

.checkbox-group {
  display: flex;
  flex-wrap: wrap;
}

.checkbox-label {
  margin-right: 1.5rem;
  display: inline-flex;
  align-items: center;
  margin-bottom: 0.5rem;
}

.field-label-with-info {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 0.25rem;
}

.tooltip-container {
  display: inline-block;
  margin-left: 4px;
  position: relative;
  vertical-align: middle;
}

.info-icon {
  cursor: pointer;
  color: #777;
  font-size: 0.9em;
}

.tooltip-text {
  display: none;
  position: absolute;
  left: 20px;
  top: -5px;
  background: #333;
  color: #fff;
  padding: 0.5em;
  border-radius: 4px;
  white-space: pre-line;
  z-index: 10;
  width: 250px;
  font-size: 0.9em;
  line-height: 1.4;
}

.tooltip-container:hover .tooltip-text {
  display: block;
}

.action-buttons {
  display: flex;
  flex-direction: row;
  gap: 10px;
  margin-top: 1rem;
}

.small-button {
  height: 1.8rem;
  padding: 0 0.75rem;
  font-size: 0.85rem;
  border-radius: 4px;
  cursor: pointer;
  border: none;
  font-weight: 500;
}

.submit-button {
  background-color: #23d160;
  color: white;
}

.submit-button:disabled {
  background-color: #23d160;
  opacity: 0.7;
  cursor: not-allowed;
}

.cancel-button {
  background-color: #f5f5f5;
  color: #363636;
}

.cancel-button:hover {
  background-color: #e8e8e8;
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

/* Improve checkbox styling */
.feedback-form input[type="checkbox"] {
  margin-right: 0.25rem;
  cursor: pointer;
}

.feedback-form label {
  cursor: pointer;
  user-select: none;
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