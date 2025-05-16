import { defineStore } from 'pinia'
import { useSessionStore } from './session'

export const useSocketStore = defineStore('socket', {
  state: () => ({
    socket: null,
    connected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 2000,
    lastError: null,
    connectionUrl: null
  }),
  actions: {
    /**
     * Initialize the WebSocket connection to the backend
     */
    initializeSocket() {
      // Only create a new connection if there is no socket or the socket is closed
      if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
        console.log('WebSocket already connected or connecting');
        return
      }

      const sessionStore = useSessionStore()
      
      // Determine the correct WebSocket URL based on environment
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      
      // Get host and port from the environment or use defaults
      let host = location.hostname;
      let port = '8000'; // Default backend port
      
      // If we have an explicit API URL configured, use that
      const apiUrl = import.meta.env.VITE_API_URL;
      if (apiUrl) {
        try {
          const url = new URL(apiUrl);
          host = url.hostname;
          port = url.port || (url.protocol === 'https:' ? '443' : '80');
        } catch (e) {
          console.error('Invalid API URL format:', apiUrl);
        }
      }
      
      // Construct WebSocket URL with session ID
      const wsUrl = `${protocol}//${host}:${port}/ws/${sessionStore.sessionId}`;
      this.connectionUrl = wsUrl;
      
      console.log('Attempting WebSocket connection to:', wsUrl);
      
      try {
        this.socket = new WebSocket(wsUrl);

        // Set up WebSocket event handlers
        this.socket.onopen = this.handleSocketOpen.bind(this);
        this.socket.onclose = this.handleSocketClose.bind(this);
        this.socket.onerror = this.handleSocketError.bind(this);
        this.socket.onmessage = this.handleSocketMessage.bind(this);

        // Set up ping interval
        this.startPingInterval();
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        this.lastError = `Failed to create WebSocket: ${error.message}`;
        this.handleReconnect();
      }
    },

    /**
     * Handle WebSocket open event
     */
    handleSocketOpen() {
      console.log('✅ WebSocket connection established to', this.connectionUrl);
      this.connected = true;
      this.reconnectAttempts = 0;
      this.lastError = null;
    },

    /**
     * Handle WebSocket close event
     */
    handleSocketClose(event) {
      const reason = event.reason || 'No reason provided';
      const code = event.code;
      console.warn(`❌ WebSocket disconnected - Code: ${code}, Reason: ${reason}`);
      this.connected = false;
      this.lastError = `Connection closed (${code}: ${reason})`;
      this.handleReconnect();
    },

    /**
     * Handle WebSocket error event
     */
    handleSocketError(error) {
      console.error('❌ WebSocket error:', error);
      this.lastError = 'Connection failed - Check console for details';
      this.connected = false;
    },

    /**
     * Handle WebSocket message event
     */
    handleSocketMessage(event) {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error, event.data);
      }
    },

    /**
     * Handle reconnect after connection failure or close
     */
    handleReconnect() {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
        console.log(`Reconnecting (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);
        
        setTimeout(() => {
          this.initializeSocket();
        }, delay);
      } else {
        console.error(`Giving up after ${this.maxReconnectAttempts} reconnect attempts.`);
      }
    },

    /**
     * Start regular ping interval to keep connection alive
     */
    startPingInterval() {
      const pingInterval = setInterval(() => {
        if (this.connected && this.socket && this.socket.readyState === WebSocket.OPEN) {
          this.sendMessage({
            type: 'ping',
            session_id: useSessionStore().sessionId
          });
        } else if (!this.connected) {
          // Clear interval if disconnected
          clearInterval(pingInterval);
        }
      }, 10000);
    },

    /**
     * Process incoming WebSocket messages
     */
    handleMessage(data) {
      const sessionStore = useSessionStore();
      console.log('Received WebSocket message:', data.type);

      switch (data.type) {
        case 'pong':
          console.log('Received pong from server');
          break;

        case 'feedback_confirmed':
          console.log('Received feedback confirmation:', data);
          if (data.qa_id) {
            console.log('Marking feedback as submitted for qa_id:', data.qa_id);
            sessionStore.markFeedbackSubmitted(data.qa_id);
            
            // Show alert if there was an error
            if (!data.success && data.message) {
              console.warn('Feedback submission failed:', data.message);
              alert('Feedback submission issue: ' + data.message);
            }
          }
          break;

        case 'session_reset_confirmed':
          console.log('Session reset confirmed by server');
          break;

        case 'corpus_filter_updated':
          if (data.corpus_filter) {
            console.log('Server updated corpus filter to:', data.corpus_filter);
            sessionStore.setCorpusFilter(data.corpus_filter);
          }
          break;

        case 'error':
          console.error('Error from WebSocket server:', data.message || 'Unknown error');
          this.lastError = data.message || 'Server error';
          break;

        default:
          console.log('Unhandled WebSocket message type:', data.type);
      }
    },

    /**
     * Send a message through the WebSocket
     */
    sendMessage(message) {
      if (this.connected && this.socket && this.socket.readyState === WebSocket.OPEN) {
        try {
          const messageStr = JSON.stringify(message);
          console.log('Sending WebSocket message:', message.type);
          this.socket.send(messageStr);
          return true;
        } catch (error) {
          console.error('Error sending WebSocket message:', error);
          return false;
        }
      } else {
        console.warn('Cannot send message: WebSocket not connected');
        return false;
      }
    },

    /**
     * Send feedback via WebSocket
     */
    sendFeedback(qaId, feedback) {
      return this.sendMessage({
        type: 'feedback',
        data: {
          qa_id: qaId,
          feedback: feedback
        }
      });
    },

    /**
     * Disconnect the WebSocket
     */
    disconnect() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
        this.connected = false;
      }
    }
  }
}) 