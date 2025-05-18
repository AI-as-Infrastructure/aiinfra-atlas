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
    connectionUrl: null,
    connecting: false,
    connectionPromise: null
  }),
  actions: {
    /**
     * Initialize the WebSocket connection to the backend
     */
    async initializeSocket() {
      if (this.connecting && this.connectionPromise) {
        console.log('Connection attempt already in progress, reusing promise');
        return this.connectionPromise;
      }
      
      if (this.socket && (this.socket.readyState === WebSocket.OPEN)) {
        console.log('WebSocket already connected');
        return Promise.resolve(true);
      }
      
      if (this.socket && this.socket.readyState === WebSocket.CONNECTING) {
        console.log('WebSocket already connecting, waiting...');
        this.connecting = true;
        this.connectionPromise = new Promise((resolve) => {
          const checkConnection = () => {
            if (this.connected) {
              resolve(true);
            } else if (this.lastError) {
              resolve(false);
            } else {
              setTimeout(checkConnection, 100);
            }
          };
          checkConnection();
        });
        return this.connectionPromise;
      }

      const sessionStore = useSessionStore()
      
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      
      let host = location.hostname;
      let port = '8000';
      
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
      
      const wsUrl = `${protocol}//${host}:${port}/ws/${sessionStore.sessionId}`;
      this.connectionUrl = wsUrl;
      
      console.log('Attempting WebSocket connection to:', wsUrl);
      
      this.connecting = true;
      this.connectionPromise = new Promise((resolve) => {
        try {
          this.disconnect();
          
          this.lastError = null;
          
          this.socket = new WebSocket(wsUrl);
          console.log('WebSocket object created, waiting for connection...');

          const connectionTimeout = setTimeout(() => {
            if (this.socket && this.socket.readyState !== WebSocket.OPEN) {
              console.error('WebSocket connection timed out');
              this.lastError = 'Connection timed out';
              if (this.socket) {
                this.socket.close();
                this.handleSocketClose({code: 1000, reason: 'Connection timed out'});
              }
              resolve(false);
            }
          }, 10000);
          
          this.socket.onopen = (event) => {
            clearTimeout(connectionTimeout);
            this.handleSocketOpen(event);
            resolve(true);
          };
          
          this.socket.onclose = (event) => {
            clearTimeout(connectionTimeout);
            this.handleSocketClose(event);
            resolve(false);
          };
          
          this.socket.onerror = (error) => {
            clearTimeout(connectionTimeout);
            this.handleSocketError(error);
            resolve(false);
          };
          
          this.socket.onmessage = this.handleSocketMessage.bind(this);

          this.startPingInterval();
        } catch (error) {
          console.error('Failed to create WebSocket:', error);
          this.lastError = `Failed to create WebSocket: ${error.message}`;
          this.connected = false;
          resolve(false);
          this.handleReconnect();
        } finally {
          setTimeout(() => {
            this.connecting = false;
            this.connectionPromise = null;
          }, 1000);
        }
      });
      
      return this.connectionPromise;
    },

    /**
     * Handle WebSocket open event
     */
    handleSocketOpen(event) {
      console.log('✅ WebSocket connection established to', this.connectionUrl);
      this.connected = true;
      this.reconnectAttempts = 0;
      this.lastError = null;
      this.connecting = false;
      
      this.sendMessage({
        type: 'ping',
        data: {
          session_id: useSessionStore().sessionId
        }
      });
    },

    /**
     * Handle WebSocket close event
     */
    handleSocketClose(event) {
      const reason = event.reason || 'No reason provided';
      const code = event.code;
      console.warn(`❌ WebSocket disconnected - Code: ${code}, Reason: ${reason}`);
      this.connected = false;
      this.connecting = false;
      this.lastError = `Connection closed (${code}: ${reason})`;
      
      if (code !== 1000) {
        this.handleReconnect();
      }
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
            data: {
              session_id: useSessionStore().sessionId
            }
          });
        } else if (!this.connected) {
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
          if (message.data && !message.data.session_id) {
            const sessionStore = useSessionStore();
            message.data.session_id = sessionStore.sessionId;
          }
          
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
        try {
          if (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING) {
            console.log('Closing WebSocket connection gracefully');
            this.socket.close(1000, 'Client disconnected');
          }
        } catch (error) {
          console.warn('Error while closing WebSocket:', error);
        } finally {
          this.socket = null;
          this.connected = false;
        }
      }
    }
  }
}) 