<template>
  <div class="feedback-form">
    <div v-if="error" class="notification is-danger">
      {{ error }}
    </div>
    <div v-if="feedbackMessage" class="notification is-success">
      {{ feedbackMessage }}
    </div>
    <form @submit.prevent="submitFeedback">
      <div class="field">
        <label class="label">Your Feedback</label>
        <div class="control">
          <textarea
            class="textarea"
            v-model="feedbackData.message"
            placeholder="Enter your feedback here..."
            required
          ></textarea>
        </div>
      </div>
      <div class="field">
        <div class="control">
          <button type="submit" class="button is-primary" :disabled="isSubmitting">
            {{ isSubmitting ? 'Sending...' : 'Submit Feedback' }}
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<script>
import { useTelemetryStore } from '@/stores/telemetry';

export default {
  name: 'FeedbackForm',
  data() {
    return {
      feedbackData: {
        message: '',
        timestamp: null
      },
      feedbackMessage: null,
      error: null,
      isSubmitting: false,
      telemetryStore: null
    };
  },
  
  created() {
    // Initialize telemetry store
    this.telemetryStore = useTelemetryStore();
  },
  methods: {
    async submitFeedback() {
      if (!this.feedbackData.message.trim()) {
        this.error = 'Please enter some feedback before submitting.';
        return;
      }
      
      this.isSubmitting = true;
      this.error = null;
      
      try {
        // Prepare feedback data with telemetry information
        const feedbackPayload = {
          message: this.feedbackData.message,
          timestamp: new Date().toISOString(),
          session_id: this.telemetryStore.sessionId || 'anonymous',
          trace_id: this.telemetryStore.traceId,
          feedback_text: this.feedbackData.message
        };
        
        // Headers with telemetry information
        const headers = {
          'Content-Type': 'application/json',
          'X-Trace-Id': this.telemetryStore.traceId
        };
        
        if (this.telemetryStore.sessionId) {
          headers['X-Session-Id'] = this.telemetryStore.sessionId;
        }
        
        // Submit feedback with telemetry headers
        const response = await fetch('/api/feedback', {
          method: 'POST',
          headers,
          body: JSON.stringify(feedbackPayload)
        });
        
        if (!response.ok) {
          throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        this.feedbackMessage = 'Thank you for your feedback!';
        this.feedbackData.message = ''; // Clear form
      } catch (error) {
        console.error('Feedback submission error:', error);
        this.error = 'Note: There was an issue submitting your feedback. Please try again.';
      } finally {
        this.isSubmitting = false;
      }
    },

  }
};
</script>

<style scoped>
.feedback-form {
  margin: 1rem 0;
  padding: 1rem;
  border-radius: 4px;
  background-color: #f5f5f5;
}
</style> 