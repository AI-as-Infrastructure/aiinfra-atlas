<template>
  <div class="inline-feedback" v-if="shouldShowFeedback">
    <!-- Feedback Type Selection (Initial Step) -->
    <div v-if="currentStep === 'selection'" class="feedback-selection">
      <div class="feedback-options">
        <button 
          v-if="isSimpleEnabled"
          class="button" 
          @click="selectFeedbackType('simple')"
        >
          Simple Feedback
        </button>
        <button 
          v-if="isEnhancedEnabled"
          class="button" 
          @click="selectFeedbackType('extended')"
        >
          Enhanced Feedback
        </button>
        <button 
          v-if="isAIAssistedEnabled"
          class="button" 
          @click="selectFeedbackType('ai-enhanced')"
        >
          AI Assisted Feedback
        </button>
        <button 
          v-if="isSkipEnabled"
          class="button" 
          @click="selectFeedbackType('skip')"
        >
          Skip
        </button>
      </div>
    </div>

    <!-- Simple Feedback -->
    <SimpleFeedback
      v-if="currentStep === 'simple'"
      :qa-id="qaId"
      :session-id="sessionId"
      @feedback-changed="onSimpleFeedbackChanged"
      @feedback-data-ready="onSimpleFeedbackDataReady"
      @feedback-submitted="onSimpleFeedbackSubmitted"
      @cancel="onSimpleCancel"
      ref="simpleFeedback"
    />

    <!-- Extended Feedback Prompt (After Simple Feedback) -->
    <FeedbackPrompt
      v-if="currentStep === 'prompt'"
      @response="onPromptResponse"
    />

    <!-- Extended Feedback (If User Chose Extended) -->
    <ExtendedFeedback
      v-if="currentStep === 'extended'"
      :qa-id="qaId"
      :session-id="sessionId"
      :initial-data="simpleFeedbackData"
      :complete-feedback-payload="completeFeedbackPayload"
      @cancel="onExtendedCancel"
      @feedback-submitted="onExtendedFeedbackSubmitted"
    />

    <!-- AI-Enhanced Feedback (If User Chose AI-Enhanced) -->
    <AIEnhancedFeedback
      v-if="currentStep === 'ai-enhanced'"
      :qa-id="qaId"
      :session-id="sessionId"
      @back="onAIEnhancedBack"
      @submit="onAIEnhancedSubmit"
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
import AIEnhancedFeedback from './AIEnhancedFeedback.vue'
import FeedbackPrompt from './FeedbackPrompt.vue'
import { useSessionStore } from '../stores/session'
import { useTelemetryStore } from '../stores/telemetry'

export default {
  name: 'InlineFeedback',
  components: {
    SimpleFeedback,
    ExtendedFeedback,
    AIEnhancedFeedback,
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
      currentStep: 'selection', // 'selection', 'simple', 'prompt', 'extended', 'ai-enhanced', 'thankyou', 'complete'
      simpleFeedbackData: {},
      completeFeedbackPayload: null // Store the complete feedback data
    }
  },
  computed: {
    shouldShowFeedback() {
      // Don't show feedback if no feedback options are enabled
      if (!this.hasAnyFeedbackOptions) {
        return false
      }
      
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
    },
    
    // Environment variable toggles for feedback types
    isSimpleEnabled() {
      return import.meta.env.VITE_FEEDBACK_SIMPLE_ENABLED !== 'false'
    },
    
    isEnhancedEnabled() {
      return import.meta.env.VITE_FEEDBACK_ENHANCED_ENABLED !== 'false'
    },
    
    isAIAssistedEnabled() {
      return import.meta.env.VITE_FEEDBACK_AI_ASSISTED_ENABLED !== 'false'
    },
    
    isSkipEnabled() {
      return import.meta.env.VITE_FEEDBACK_SKIP_ENABLED !== 'false'
    },
    
    hasAnyFeedbackOptions() {
      return this.isSimpleEnabled || this.isEnhancedEnabled || this.isAIAssistedEnabled || this.isSkipEnabled
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
    
    async onSimpleFeedbackSubmitted() {
      console.log('INLINE: onSimpleFeedbackSubmitted called - submitting simple feedback')
      console.log('INLINE: completeFeedbackPayload available:', !!this.completeFeedbackPayload)
      
      // Submit simple feedback directly since user chose Simple Feedback from selection
      const success = await this.submitSimpleFeedbackOnly()
      if (success) {
        this.currentStep = 'thankyou'
        
        // Show thank you for 1.5 seconds, then complete workflow
        setTimeout(() => {
          this.completeFeedbackWorkflow()
        }, 1500)
      } else {
        console.error('INLINE: Failed to submit simple feedback')
      }
    },
    
    async onPromptResponse(response) {
      console.log('INLINE: User response to prompt:', response)
      if (response === 'extended') {
        // User wants to provide extended feedback - DON'T submit simple feedback yet
        console.log('INLINE: User chose EXTENDED - moving to extended feedback (NO API call yet)')
        this.currentStep = 'extended'
      } else if (response === 'ai-enhanced') {
        // User wants AI-Enhanced feedback - DON'T submit simple feedback yet
        console.log('INLINE: User chose AI-ENHANCED - moving to AI-enhanced feedback (NO API call yet)')
        this.currentStep = 'ai-enhanced'
      } else {
        // User doesn't want extended feedback - submit simple feedback and show thank you
        console.log('INLINE: User chose NO - submitting simple feedback only')
        console.log('INLINE: completeFeedbackPayload available:', !!this.completeFeedbackPayload)
        
        const success = await this.submitSimpleFeedbackOnly()
        if (success) {
          this.currentStep = 'thankyou'
          
          // Show thank you for 1.5 seconds, then complete workflow
          setTimeout(() => {
            this.completeFeedbackWorkflow()
          }, 1500)
        } else {
          console.error('INLINE: Failed to submit simple feedback')
          // Could show error message to user
        }
      }
    },
    
    onSimpleCancel() {
      // User cancelled simple feedback - return to selection
      this.currentStep = 'selection'
    },
    
    onExtendedCancel() {
      // User cancelled extended feedback - return to selection
      this.currentStep = 'selection'
    },
    
    onExtendedFeedbackSubmitted() {
      // Extended feedback submitted - show thank you message
      this.currentStep = 'thankyou'
      
      // Show thank you for 2 seconds, then complete workflow
      setTimeout(() => {
        this.completeFeedbackWorkflow()
      }, 2000)
    },
    
    onAIEnhancedBack() {
      // User went back from AI-Enhanced feedback - return to selection
      this.currentStep = 'selection'
    },
    
    async onAIEnhancedSubmit(feedbackData) {
      // AI-Enhanced feedback submitted - submit to API
      console.log('INLINE: AI-Enhanced feedback submitted:', feedbackData)
      
      try {
        // Get current session data for the submission
        const chatHistory = this.sessionStore.chatHistory
        const currentQuestion = chatHistory[chatHistory.length - 2]?.content || ''
        const currentAnswer = chatHistory[chatHistory.length - 1]?.content || ''
        const fullCitations = chatHistory[chatHistory.length - 1]?.citations || []
        
        // Build the complete feedback payload for AI-enhanced feedback
        const completeFeedbackPayload = {
          qa_id: this.qaId,
          session_id: this.sessionId,
          feedback_type: 'ai_enhanced',
          timestamp: new Date().toISOString(),
          question: currentQuestion,
          answer: currentAnswer,
          citations: fullCitations,
          
          // Add trace ID if available
          trace_id: this.telemetryStore.traceId
        }
        
        // Add AI-enhanced specific fields using direct assignment (same pattern as extended feedback)
        if (feedbackData.human_comments) {
          completeFeedbackPayload.feedback_text = feedbackData.human_comments
        }
        
        if (feedbackData.ai_agreement) {
          completeFeedbackPayload.ai_agreement = feedbackData.ai_agreement
        }
        
        // Add AI validation data (always try to unwrap Vue Proxy)
        try {
          const aiValidation = JSON.parse(JSON.stringify(feedbackData.ai_validation))
          console.log('INLINE: Unwrapped ai_validation:', aiValidation)
          console.log('INLINE: ai_validation keys count:', aiValidation ? Object.keys(aiValidation).length : 0)
          if (aiValidation && Object.keys(aiValidation).length > 0) {
            completeFeedbackPayload.ai_validation = aiValidation
            console.log('INLINE: Added ai_validation to payload')
          } else {
            console.log('INLINE: ai_validation is empty or null, not adding to payload')
          }
        } catch (error) {
          console.error('Error unwrapping ai_validation:', error)
        }
        
        // Add human ratings using direct assignment (same pattern as extended feedback)
        if (feedbackData.ratings) {
          const ratings = JSON.parse(JSON.stringify(feedbackData.ratings))
          
          // Add the ratings object itself for AI-enhanced feedback processing
          completeFeedbackPayload.ratings = ratings
          
          // Add each rating individually (same pattern as extended feedback)
          if (ratings.factual_accuracy !== null) {
            completeFeedbackPayload.factual_accuracy = ratings.factual_accuracy
          }
          if (ratings.completeness !== null) {
            completeFeedbackPayload.completeness = ratings.completeness
          }
          if (ratings.relevance !== null) {
            completeFeedbackPayload.relevance = ratings.relevance
          }
          if (ratings.citation_quality !== null) {
            completeFeedbackPayload.source_quality = ratings.citation_quality // Map to backend field name
          }
          if (ratings.clarity !== null) {
            completeFeedbackPayload.clarity = ratings.clarity
          }
        }
        
        console.log('INLINE: Submitting AI-Enhanced feedback:', completeFeedbackPayload)
        
        const response = await fetch('/api/feedback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Trace-Id': this.telemetryStore.traceId,
            'X-Session-Id': this.sessionId
          },
          body: JSON.stringify(completeFeedbackPayload)
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        console.log('INLINE: AI-Enhanced feedback submission SUCCESS')
        this.currentStep = 'thankyou'
        
        // Show thank you for 2 seconds, then complete workflow
        setTimeout(() => {
          this.completeFeedbackWorkflow()
        }, 2000)
        
      } catch (error) {
        console.error('INLINE: Error submitting AI-Enhanced feedback:', error)
        // Could show error message to user
      }
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
      this.currentStep = 'selection'
      this.simpleFeedbackData = {}
      this.completeFeedbackPayload = null
      
      // Reset simple feedback form if it exists
      if (this.$refs.simpleFeedback) {
        this.$refs.simpleFeedback.reset()
      }
    },
    
    selectFeedbackType(type) {
      console.log('INLINE: User selected feedback type:', type)
      
      if (type === 'skip') {
        // User chose to skip feedback - complete workflow immediately
        this.completeFeedbackWorkflow()
      } else {
        // Move to the selected feedback type
        this.currentStep = type
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

/* Feedback Selection Styles */
.feedback-selection {
  padding: 0.5rem 0;
  width: 100%;
}

.feedback-options {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-start;
  flex-wrap: wrap;
  width: 100%;
}

.feedback-options .button {
  font-size: 0.875rem;
  padding: 0.5rem 1rem;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .inline-feedback {
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
  }
  
  .feedback-options {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .feedback-options .button {
    width: 100%;
  }
}
</style>