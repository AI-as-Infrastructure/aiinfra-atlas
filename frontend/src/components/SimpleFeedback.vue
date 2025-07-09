<template>
  <div class="simple-feedback">
    <div class="feedback-line">
      <!-- Thumbs Up/Down Buttons -->
      <div class="sentiment-buttons">
        <button
          class="sentiment-btn thumbs-up"
          :class="{ active: sentiment === 'positive' }"
          @click="setSentiment('positive')"
          title="This response was helpful"
        >
          <svg class="thumbs-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M7.493 18.75c-.425 0-.82-.236-.975-.632A7.48 7.48 0 016 15.375c0-1.75.599-3.358 1.602-4.634.151-.192.373-.309.6-.397.473-.183.89-.514 1.212-.924a9.042 9.042 0 012.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3a.75.75 0 01.75-.75 2.25 2.25 0 012.25 2.25c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 01-2.649 7.521c-.388.482-.987.729-1.605.729H14.23c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 00-1.423-.23h-.777zM2.331 10.977a11.969 11.969 0 00-.831 4.398 12 12 0 00.52 3.507c.26.85 1.084 1.368 1.973 1.368H4.9c.445 0 .72-.498.523-.898a8.963 8.963 0 01-.924-3.977c0-1.708.476-3.305 1.302-4.666.245-.403-.028-.959-.5-.959H4.25c-.832 0-1.612.453-1.918 1.227z"/>
          </svg>
        </button>
        <button
          class="sentiment-btn thumbs-down"
          :class="{ active: sentiment === 'negative' }"
          @click="setSentiment('negative')"
          title="This response was not helpful"
        >
          <svg class="thumbs-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M15.73 5.25h1.035A7.465 7.465 0 0118 9.375a7.465 7.465 0 01-1.235 4.125h-.148c-.806 0-1.534.446-2.031 1.08a9.04 9.04 0 01-2.861 2.4c-.723.384-1.35.956-1.653 1.715a4.498 4.498 0 00-.322 1.672V21a.75.75 0 01-.75.75 2.25 2.25 0 01-2.25-2.25c0-1.152.26-2.243.723-3.218C7.74 15.724 7.366 15 6.748 15H3.622c-1.026 0-1.945-.694-2.054-1.715A12.134 12.134 0 011.5 12c0-2.848.992-5.464 2.649-7.521C4.537 3.997 5.136 3.75 5.754 3.75H9.77a4.5 4.5 0 011.423.23l3.114 1.04a4.5 4.5 0 001.423.23zM21.669 13.023c.536-1.362.831-2.845.831-4.398 0-1.22-.182-2.398-.52-3.507-.26-.85-1.084-1.368-1.973-1.368H19.1c-.445 0-.72.498-.523.898.591 1.2.924 2.55.924 3.977a8.959 8.959 0 01-1.302 4.666c-.245.403.028.959.5.959h1.053c.832 0 1.612-.453 1.918-1.227z"/>
          </svg>
        </button>
      </div>

      <!-- Basic Feedback Text Field -->
      <div class="feedback-text">
        <input
          v-model="basicText"
          type="text"
          placeholder="Free text feedback (optional)..."
          class="feedback-input"
          maxlength="200"
          @input="onTextChange"
        />
      </div>

      <!-- Submit and Cancel Buttons -->
      <div class="submit-section">
        <button
          class="cancel-btn"
          @click="cancelFeedback"
          :disabled="isSubmitting"
        >
          Cancel
        </button>
        <button
          class="submit-btn"
          @click="submitBasicFeedback"
          :disabled="isSubmitting || !hasBasicFeedback"
        >
          <span v-if="isSubmitting">Submitting...</span>
          <span v-else>Submit</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { useSessionStore } from '@/stores/session'
import { useTelemetryStore } from '@/stores/telemetry'

export default {
  name: 'SimpleFeedback',
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
    }
  },
  emits: ['feedback-submitted', 'feedback-changed', 'feedback-data-ready', 'cancel'],
  setup() {
    const sessionStore = useSessionStore()
    const telemetryStore = useTelemetryStore()
    return { sessionStore, telemetryStore }
  },
  data() {
    return {
      sentiment: null, // 'positive', 'negative', or null
      basicText: '',
      isSubmitting: false,
      configData: null
    }
  },
  computed: {
    hasBasicFeedback() {
      return this.sentiment !== null || this.basicText.trim().length > 0
    }
  },
  methods: {
    setSentiment(value) {
      if (this.disabled) return
      
      // Toggle off if clicking the same sentiment
      this.sentiment = this.sentiment === value ? null : value
      this.emitFeedbackChange()
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
    
    onTextChange() {
      this.emitFeedbackChange()
    },
    
    emitFeedbackChange() {
      // Emit current feedback state to parent
      this.$emit('feedback-changed', {
        sentiment: this.sentiment,
        basicText: this.basicText.trim(),
        hasBasicFeedback: this.hasBasicFeedback
      })
    },
    
    async submitBasicFeedback() {
      if (!this.hasBasicFeedback || this.isSubmitting) return
      
      this.isSubmitting = true
      
      try {
        // Get current question and answer from chat history
        const chatHistory = this.sessionStore.chatHistory
        const currentQuestion = chatHistory[chatHistory.length - 2]?.content || ''
        const currentAnswer = chatHistory[chatHistory.length - 1]?.content || ''
        const fullCitations = chatHistory[chatHistory.length - 1]?.citations || []
        
        // Build feedback data with only non-empty fields
        const feedbackData = {
          session_id: this.sessionId,
          qa_id: this.qaId,
          feedback_type: 'simple',
          timestamp: new Date().toISOString()
        }
        
        // Add optional fields only if they have values
        if (this.telemetryStore.traceId) {
          feedbackData.trace_id = this.telemetryStore.traceId
        }
        
        if (this.sentiment) {
          feedbackData.sentiment = this.sentiment
        }
        
        if (this.basicText.trim()) {
          feedbackData.feedback_text = this.basicText.trim()
        }
        
        if (this.configData && Object.keys(this.configData).length > 0) {
          feedbackData.test_target = this.configData
        }
        
        if (currentQuestion) {
          feedbackData.question = currentQuestion
        }
        
        if (currentAnswer) {
          feedbackData.answer = currentAnswer
        }
        
        if (fullCitations && fullCitations.length > 0) {
          feedbackData.citations = fullCitations
        }
        
        console.log('SIMPLE: Preparing feedback data (NOT submitting to API yet):', feedbackData)
        
        // Emit the feedback data to parent for handling
        this.$emit('feedback-data-ready', feedbackData)
        
        // Emit success (but don't actually submit to API yet)
        this.$emit('feedback-submitted', 'simple')
        
        // Reset form
        this.sentiment = null
        this.basicText = ''
        
      } catch (error) {
        console.error('Error preparing feedback:', error)
      } finally {
        this.isSubmitting = false
      }
    },

    async submitFeedbackToAPI(feedbackData) {
      // This method can be called by parent to actually submit the data
      try {
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
        
        return true
      } catch (error) {
        console.error('Error submitting feedback:', error)
        return false
      }
    },
    
    cancelFeedback() {
      // Reset form state
      this.sentiment = null
      this.basicText = ''
      this.isSubmitting = false
      
      // Emit cancel event to parent
      this.$emit('cancel')
    },
    
    reset() {
      this.sentiment = null
      this.basicText = ''
      this.isSubmitting = false
    }
  },
  
  async mounted() {
    await this.fetchConfigData()
    // Emit initial feedback state
    this.emitFeedbackChange()
  }
}
</script>

<style scoped>
.simple-feedback {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.feedback-line {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
}

.sentiment-buttons {
  display: flex;
  gap: 0.5rem;
}

.sentiment-btn {
  background: white;
  border: 2px solid #dee2e6;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #6c757d;
}

.thumbs-icon {
  width: 18px;
  height: 18px;
  transition: color 0.2s ease;
}

.sentiment-btn:hover:not(.active) {
  border-color: #6c757d;
  background-color: #f8f9fa;
}

.sentiment-btn.active.thumbs-up {
  background-color: #d4edda !important;
  border-color: #28a745 !important;
  color: #28a745 !important;
}

.sentiment-btn.active.thumbs-down {
  background-color: #f8d7da !important;
  border-color: #dc3545 !important;
  color: #dc3545 !important;
}

/* Ensure active state persists on hover */
.sentiment-btn.active.thumbs-up:hover {
  background-color: #c3e6cb !important;
  border-color: #28a745 !important;
  color: #1e7e34 !important;
}

.sentiment-btn.active.thumbs-down:hover {
  background-color: #f5c6cb !important;
  border-color: #dc3545 !important;
  color: #bd2130 !important;
}

.feedback-text {
  flex: 1;
  min-width: 200px;
}

.feedback-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
}

.feedback-input:focus {
  outline: none;
  border-color: #80bdff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}


.submit-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.submit-btn {
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.submit-btn:hover:not(:disabled) {
  background-color: #0056b3;
}

.submit-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
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
  background-color: #5a6268;
}

.cancel-btn:disabled {
  background-color: #adb5bd;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .feedback-line {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
  
  .sentiment-buttons {
    justify-content: center;
  }
  
  .submit-section {
    justify-content: center;
  }
}
</style>