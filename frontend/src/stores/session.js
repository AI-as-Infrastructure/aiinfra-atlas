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
    feedbackSubmitted: {}, // Track feedback status by message_id
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
     * Add a message to the chat history with size limits
     */
    addMessage(message) {
      const messageWithId = {
        ...message,
        message_id: uuidv4(),
        timestamp: new Date().toISOString(),
        qa_id: this.qaId
      }
      
      // Add the new message
      this.chatHistory.push(messageWithId)
      
      // Apply chat history limits (keep last 100 messages)
      const maxMessages = 100
      if (this.chatHistory.length > maxMessages) {
        // Remove oldest messages, but keep pairs (user question + assistant response)
        const messagesToRemove = this.chatHistory.length - maxMessages
        this.chatHistory.splice(0, messagesToRemove)
      }
      
      // Also check total content size (limit to ~1MB of text)
      const maxContentSize = 1024 * 1024 // 1MB
      let totalSize = 0
      
      // Calculate total content size
      for (const msg of this.chatHistory) {
        totalSize += (msg.content || '').length
        if (msg.citations) {
          totalSize += JSON.stringify(msg.citations).length
        }
      }
      
      // If too large, remove oldest messages
      while (totalSize > maxContentSize && this.chatHistory.length > 10) {
        const removedMessage = this.chatHistory.shift()
        totalSize -= (removedMessage.content || '').length
        if (removedMessage.citations) {
          totalSize -= JSON.stringify(removedMessage.citations).length
        }
      }
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
     * Mark feedback as submitted for a specific message ID
     */
    markFeedbackSubmitted(messageId) {
      this.feedbackSubmitted[messageId] = true
    },
    
    /**
     * Reset the feedback state (e.g., when starting a new interaction)
     */
    resetFeedbackState() {
      this.isResponseComplete = false
      this.isNewQuestionAsked = false
    },
    
    /**
     * Check if feedback has been submitted for a specific message ID
     */
    hasFeedbackBeenSubmitted(messageId) {
      if (!messageId) return false
      return !!this.feedbackSubmitted[messageId]
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
          message_id: msg.message_id,
          role: msg.role,
          content: msg.content,
          citations: msg.citations || [],
          timestamp: msg.timestamp,
          qa_id: msg.qa_id
        })),
        corpusFilter: this.corpusFilter
      }
    }
  }
})