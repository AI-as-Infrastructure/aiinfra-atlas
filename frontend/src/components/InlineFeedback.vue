<template>
  <div class="inline-feedback" v-if="shouldShowFeedback">
    <!-- Simple Feedback (Initial Step) -->
    <SimpleFeedback
      v-if="currentStep === 'simple'"
      :qa-id="qaId"
      :session-id="sessionId"
      @feedback-changed="onSimpleFeedbackChanged"
      @feedback-data-ready="onSimpleFeedbackDataReady"
      @feedback-submitted="onSimpleFeedbackSubmitted"
      ref="simpleFeedback"
    />

    <!-- Extended Feedback Prompt (After Simple Feedback) -->
    <FeedbackPrompt
      v-if="currentStep === 'prompt'"
      @response="onPromptResponse"
    />

    <!-- Extended Feedback (If User Chose Yes) -->
    <ExtendedFeedback
      v-if="currentStep === 'extended'"
      :qa-id="qaId"
      :session-id="sessionId"
      :initial-data="simpleFeedbackData"
      :complete-feedback-payload="completeFeedbackPayload"
      @cancel="onExtendedCancel"
      @feedback-submitted="onExtendedFeedbackSubmitted"
    />

    <!-- Thank You Message (After Feedback Submission) -->
    <div v-if="currentStep === 'thankyou'" class="feedback-thank-you">
      <div class="thank-you-content">
        <span class="check-icon">✓</span>
        <span class="thank-you-text">Thank you for your feedback!</span>
      </div>
    </div>
  </div>
</template>

<script>
import SimpleFeedback from './SimpleFeedback.vue'
import ExtendedFeedback from './ExtendedFeedback.vue'
import FeedbackPrompt from './FeedbackPrompt.vue'
import { useSessionStore } from '../stores/session'
import { useTelemetryStore } from '../stores/telemetry'

export default {
  name: 'InlineFeedback',
  components: {
    SimpleFeedback,
    ExtendedFeedback,
    FeedbackPrompt
  },
  props: {
    qaId: {
      type: String,
      required: true
    },
    messageId: {
      type: String,
      required: true
    },
    sessionId: {
      type: String,
      required: true
    },
    messageComplete: {
      type: Boolean,
      default: false
    },
    citationsVisible: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const sessionStore = useSessionStore()
    const telemetryStore = useTelemetryStore()
    return { sessionStore, telemetryStore }
  },
  emits: ['feedback-workflow-complete'],
  data() {
    return {
      currentStep: 'simple', // 'simple', 'prompt', 'extended', 'thankyou', 'complete'
      simpleFeedbackData: {},
      completeFeedbackPayload: null // Store the complete feedback data
    }
  },
  computed: {
    shouldShowFeedback() {
      // Don't show feedback if it's already been submitted for this QA ID
      if (this.isAlreadySubmitted) {
        return false
      }
      
      // Don't show feedback if we're in the complete state
      if (this.currentStep === 'complete') {
        return false
      }
      
      // Show feedback after message is complete and citations are visible
      return this.messageComplete && this.citationsVisible && this.qaId
    },
    
    isAlreadySubmitted() {
      // Check if feedback was already submitted for this message ID
      return this.sessionStore.feedbackSubmitted[this.messageId] || false
    }
  },
  watch: {
    messageId: {
      immediate: true,
      handler(newMessageId, oldMessageId) {
        if (newMessageId) {
          // Only reset if this is actually a new message ID, not just a re-render
          if (newMessageId !== oldMessageId) {
            if (this.isAlreadySubmitted) {
              this.currentStep = 'complete'
            } else {
              this.resetFeedbackState()
            }
          }
        }
      }
    },
    
    isAlreadySubmitted: {
      immediate: true,
      handler(submitted) {
        if (submitted && this.currentStep !== 'complete') {
          this.currentStep = 'complete'
        }
      }
    }
  },
  
  mounted() {
    // Ensure proper initial state on mount
    if (this.isAlreadySubmitted) {
      this.currentStep = 'complete'
    }
  },
  methods: {
    onSimpleFeedbackChanged(feedbackData) {
      // Store simple feedback data for extended feedback
      this.simpleFeedbackData = {
        sentiment: feedbackData.sentiment,
        feedback_text: feedbackData.basicText,
        feedback_type: 'simple'
      }
    },
    
    onSimpleFeedbackDataReady(feedbackData) {
      // Store the complete feedback payload for later submission
      console.log('INLINE: storing feedback data:', feedbackData)
      this.completeFeedbackPayload = feedbackData // Already includes feedback_type and timestamp
    },
    
    onSimpleFeedbackSubmitted() {
      console.log('INLINE: onSimpleFeedbackSubmitted called - moving to prompt (NO API CALL)')
      // DON'T mark as submitted yet - wait for workflow completion
      // Just move to prompt step
      this.currentStep = 'prompt'
      
      // Reset simple feedback form
      if (this.$refs.simpleFeedback) {
        this.$refs.simpleFeedback.reset()
      }
    },
    
    async onPromptResponse(response) {
      console.log('INLINE: User response to prompt:', response)
      if (response === 'yes') {
        // User wants to provide extended feedback - DON'T submit simple feedback yet
        console.log('INLINE: User chose YES - moving to extended feedback (NO API call yet)')
        this.currentStep = 'extended'
      } else {
        // User doesn't want extended feedback - submit simple feedback and show thank you
        console.log('INLINE: User chose NO - submitting simple feedback only')
        await this.submitSimpleFeedbackOnly()
        this.currentStep = 'thankyou'
        
        // Show thank you for 1.5 seconds, then complete workflow
        setTimeout(() => {
          this.completeFeedbackWorkflow()
        }, 1500)
      }
    },
    
    onExtendedCancel() {
      // User cancelled extended feedback - workflow complete
      this.completeFeedbackWorkflow()
    },
    
    onExtendedFeedbackSubmitted() {
      // Extended feedback submitted - show thank you message
      this.currentStep = 'thankyou'
      
      // Show thank you for 2 seconds, then complete workflow
      setTimeout(() => {
        this.completeFeedbackWorkflow()
      }, 2000)
    },
    
    async submitSimpleFeedbackOnly() {
      if (this.completeFeedbackPayload) {
        console.log('INLINE: Submitting SIMPLE feedback only:', this.completeFeedbackPayload)
        
        try {
          // Submit the simple feedback directly from here since SimpleFeedback component is no longer rendered
          const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Trace-Id': this.telemetryStore.traceId,
              'X-Session-Id': this.sessionId
            },
            body: JSON.stringify(this.completeFeedbackPayload)
          })
          
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
          }
          
          console.log('INLINE: Simple feedback submission SUCCESS')
          return true
        } catch (error) {
          console.error('INLINE: Error submitting simple feedback:', error)
          return false
        }
      }
      return false
    },
    
    completeFeedbackWorkflow() {
      this.currentStep = 'complete'
      // NOW mark feedback as submitted in session store using message ID
      this.sessionStore.markFeedbackSubmitted(this.messageId)
      // Emit event to parent to indicate feedback workflow is complete
      this.$emit('feedback-workflow-complete', this.messageId)
    },
    
    resetFeedbackState() {
      this.currentStep = 'simple'
      this.simpleFeedbackData = {}
      this.completeFeedbackPayload = null
      
      // Reset simple feedback form if it exists
      if (this.$refs.simpleFeedback) {
        this.$refs.simpleFeedback.reset()
      }
    }
  }
}
</script>

<style scoped>
.inline-feedback {
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.feedback-thank-you {
  padding: 1rem;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 8px;
  margin-top: 1rem;
}

.thank-you-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #155724;
  font-weight: 500;
}

.check-icon {
  background-color: #28a745;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.thank-you-text {
  font-size: 14px;
}


/* Animation for extended feedback */
.extended-feedback-enter-active,
.extended-feedback-leave-active {
  transition: all 0.3s ease;
}

.extended-feedback-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.extended-feedback-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 768px) {
  .inline-feedback {
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
  }
}
</style>