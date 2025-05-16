import { defineStore } from 'pinia'
import { v4 as uuidv4 } from 'uuid'

export const useSessionStore = defineStore('session', {
  state: () => ({
    sessionId: uuidv4(),
    qaId: null,
    traceparent: null,
    tracestate: null,
    chatHistory: [],
    corpusFilter: 'all', // Current corpus filter
    previousCorpusFilter: null, // Store previous corpus filter for context changes
    isResponseComplete: false,
    isNewQuestionAsked: false,
    feedbackSubmitted: {}, // Track feedback status by qaId
    contextChangeNotification: null // Added for context change notification
  }),
  actions: {
    /**
     * Create a new session with a fresh ID and reset state
     */
    newSession() {
      this.sessionId = uuidv4()
      this.qaId = null
      this.chatHistory = []
      this.feedbackSubmitted = {}
      this.isResponseComplete = false
      this.isNewQuestionAsked = false
      this.previousCorpusFilter = null
    },
    
    /**
     * Generate a new QA ID for a new question/answer pair
     */
    newQaId() {
      const newId = uuidv4()
      this.qaId = newId
      this.isResponseComplete = false
      this.isNewQuestionAsked = false
      return newId
    },
    
    /**
     * Set tracing context for telemetry
     */
    setTraceContext(traceparent, tracestate) {
      this.traceparent = traceparent
      this.tracestate = tracestate
    },
    
    /**
     * Add a message to the chat history
     */
    addMessage(message) {
      this.chatHistory.push(message)
    },
    
    /**
     * Set the corpus filter and record the previous value for context change detection
     */
    setCorpusFilter(filter) {
      if (this.corpusFilter !== filter) {
        this.previousCorpusFilter = this.corpusFilter
        this.corpusFilter = filter
      }
    },
    
    /**
     * Update the message at a specific index
     */
    updateMessage(index, updates) {
      if (index >= 0 && index < this.chatHistory.length) {
        this.chatHistory[index] = {
          ...this.chatHistory[index],
          ...updates
        }
      }
    },
    
    /**
     * Set whether the current response is complete
     */
    setResponseComplete(status) {
      this.isResponseComplete = status
    },
    
    /**
     * Set whether a new question has been asked (used for UI state)
     */
    setNewQuestionAsked(status) {
      this.isNewQuestionAsked = status
    },
    
    /**
     * Mark feedback as submitted for a specific QA ID
     */
    markFeedbackSubmitted(qaId) {
      this.feedbackSubmitted[qaId] = true
    },
    
    /**
     * Reset the feedback state (e.g., when starting a new interaction)
     */
    resetFeedbackState() {
      this.isResponseComplete = false
      this.isNewQuestionAsked = false
    },
    
    /**
     * Check if feedback has been submitted for a specific QA ID
     */
    hasFeedbackBeenSubmitted(qaId) {
      if (!qaId) return false
      return !!this.feedbackSubmitted[qaId]
    },
    
    /**
     * Clear all chat history
     */
    clearChatHistory() {
      this.chatHistory = []
      this.resetFeedbackState()
    },
    
    /**
     * Export the current conversation as JSON
     */
    exportConversation() {
      return {
        sessionId: this.sessionId,
        timestamp: new Date().toISOString(),
        messages: this.chatHistory.map(msg => ({
          role: msg.role,
          content: msg.content,
          citations: msg.citations || []
        })),
        corpusFilter: this.corpusFilter
      }
    }
  }
})