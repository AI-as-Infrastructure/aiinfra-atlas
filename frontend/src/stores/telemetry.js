/**
 * Telemetry Store for ATLAS
 * 
 * This store manages telemetry state including trace IDs, timing data, and user feedback.
 * It provides the connection between frontend user interactions and backend telemetry spans.
 */

import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';
import { usePreferencesStore } from './preferences';

export const useTelemetryStore = defineStore('telemetry', {
  state: () => ({
    traceId: uuidv4(),        // For Phoenix correlation
    sessionId: null,          // ATLAS session ID
    currentQaId: null,        // Current QA pair ID
    qaIdCounter: 0,           // Counter for generating QA IDs
    feedback: null,           // Current user feedback
    interactionTimings: {
      questionStartTime: null,
      questionSubmitTime: null,
      responseStartTime: null,
      responseEndTime: null
    },
    responseMetadata: null    // Additional metadata about the response
  }),

  getters: {
    /**
     * Calculate latency in milliseconds from question submission to response end
     */
    latencyMs() {
      const { responseEndTime, questionSubmitTime } = this.interactionTimings;
      if (responseEndTime && questionSubmitTime) {
        return responseEndTime - questionSubmitTime;
      }
      return null;
    },

    /**
     * Check if telemetry is enabled by user preference
     */
    isTelemetryEnabled() {
      const preferencesStore = usePreferencesStore();
      return preferencesStore.isTelemetryEnabled;
    },

    /**
     * Generate fetch headers with telemetry IDs
     */
    telemetryHeaders() {
      // If telemetry is disabled, return empty headers
      if (!this.isTelemetryEnabled) {
        return {};
      }

      const headers = {
        'X-Trace-Id': this.traceId
      };

      if (this.sessionId) {
        headers['X-Session-Id'] = this.sessionId;
      }

      if (this.currentQaId) {
        headers['X-QA-Id'] = this.currentQaId;
      }

      return headers;
    }
  },

  actions: {
    /**
     * Initialize or update the session ID
     */
    setSessionId(sessionId) {
      this.sessionId = sessionId;
      // Keep existing traceId for the session
    },

    /**
     * Generate a new trace ID
     */
    regenerateTraceId() {
      this.traceId = uuidv4();
      return this.traceId;
    },

    /**
     * Record when user starts typing a question
     */
    startQuestion() {
      if (!this.isTelemetryEnabled) return;
      this.interactionTimings.questionStartTime = Date.now();
    },

    /**
     * Record when question is submitted to backend
     * Returns data needed for the API call
     */
    submitQuestion() {
      if (!this.isTelemetryEnabled) {
        return {
          sessionId: null,
          qaId: null,
          traceId: null
        };
      }
      
      this.interactionTimings.questionSubmitTime = Date.now();
      this.currentQaId = `qa_${this.qaIdCounter++}`;
      
      return {
        sessionId: this.sessionId,
        qaId: this.currentQaId,
        traceId: this.traceId
      };
    },

    /**
     * Record when response starts arriving
     */
    startResponse() {
      if (!this.isTelemetryEnabled) return;
      this.interactionTimings.responseStartTime = Date.now();
    },

    /**
     * Record when response is fully received
     */
    endResponse(metadata = {}) {
      if (!this.isTelemetryEnabled) return;
      this.interactionTimings.responseEndTime = Date.now();
      this.responseMetadata = {
        ...metadata,
        latencyMs: this.latencyMs
      };
    },

    /**
     * Store user feedback data
     */
    setFeedback(feedbackData) {
      if (!this.isTelemetryEnabled) return;
      this.feedback = {
        ...feedbackData,
        timestamp: new Date().toISOString()
      };
    },

    /**
     * Submit feedback to API
     */
    async submitFeedback() {
      if (!this.isTelemetryEnabled) {
        console.log('Feedback submission disabled by user preference');
        return { status: 'disabled', message: 'Telemetry disabled by user' };
      }

      if (!this.feedback || !this.sessionId || !this.currentQaId) {
        console.error('Cannot submit feedback: missing session data');
        return null;
      }

      try {
        const response = await fetch('/api/feedback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...this.telemetryHeaders
          },
          body: JSON.stringify({
            session_id: this.sessionId,
            qa_id: this.currentQaId,
            trace_id: this.traceId,  // Include trace_id in body as well
            ...this.feedback
          })
        });

        return await response.json();
      } catch (error) {
        console.error('Failed to submit feedback:', error);
        return { status: 'error', message: error.message };
      }
    },

    /**
     * Reset interaction data for a new question
     */
    resetInteraction() {
      // Keep the same session and trace ID
      this.currentQaId = null;
      this.feedback = null;
      this.responseMetadata = null;
      this.interactionTimings = {
        questionStartTime: null,
        questionSubmitTime: null,
        responseStartTime: null,
        responseEndTime: null
      };
    },

    /**
     * Reset everything for a new session
     */
    resetSession() {
      this.traceId = uuidv4();
      this.sessionId = null;
      this.currentQaId = null;
      this.qaIdCounter = 0;
      this.feedback = null;
      this.responseMetadata = null;
      this.interactionTimings = {
        questionStartTime: null,
        questionSubmitTime: null,
        responseStartTime: null,
        responseEndTime: null
      };
    }
  },

  // Enable persistence if needed
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'atlas-telemetry',
        storage: localStorage,
        paths: ['traceId', 'sessionId', 'qaIdCounter']
      }
    ]
  }
});
