import React, { useState, useEffect, useRef, useMemo } from "react";
import { Routes, Route } from "react-router-dom";
import axios from "axios";
import { io } from "socket.io-client";
import { v4 as uuidv4 } from "uuid";
import { useAuth } from "react-oidc-context";
import envConfig from "./utils/envConfig";

// Components 
import LoginPage from "./components/auth/LoginPage";
import Callback from "./components/auth/Callback";
import Header from "./components/layout/Header";
import ChatBox from "./components/chat/ChatBox";
import MessageInput from "./components/chat/MessageInput";
import ConfigBox from "./components/config/ConfigBox";
import FeedbackButtons from "./components/chat/FeedbackButtons";
import AboutPage from "./components/about/AboutPage";
import Message from "./components/chat/Message";

// Import custom hooks
import { useSession } from "./hooks/useSession";

// Import styles
import "./index.scss";

// App component sets the document title
function App() {
  useEffect(() => {
    document.title = envConfig.appTitle;
  }, []);
  
  // Return the AtlasUI component
  return <AtlasUI />;
}

// AtlasUI component (separate from App)
const AtlasUI = () => {
  // Retrieve authentication state
  const auth = useAuth();

  // If not authenticated, show the login page
  if (!auth.isAuthenticated) {
    return <LoginPage />;
  }

  // URLs
  const backendUrl = window.location.origin;
  const configUrl = `${backendUrl}/api/config`;

  console.log("🔹 Backend URL:", backendUrl);
  console.log("🔹 Config URL:", configUrl);

  // State Management
  const [chatHistory, setChatHistory] = useState([]);
  const [input, setInput] = useState("");
  const [config, setConfig] = useState({});
  const [isStreaming, setIsStreaming] = useState(false);
  const [showSessionMessage, setShowSessionMessage] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [currentMessage, setCurrentMessage] = useState(null);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState({});  // Track messages that have received feedback
  const [responseCompleteStatus, setResponseCompleteStatus] = useState(false); // Track if response is fully emitted
  const [isNewQuestionAsked, setIsNewQuestionAsked] = useState(false); // Track if a new question was asked
  const socketRef = useRef(null);
  const [socketConnected, setSocketConnected] = useState(false);
  
  // Session management
  const { getSessionId, resetSession, loadSessionHistory, getTraceContext } = useSession();

  // Handle manual session refresh
  const handleRefreshSession = () => {
    // Generate new session ID and notify backend
    const newSessionId = resetSession(socketRef.current);
    console.log("🔄 Manually refreshing session with new ID:", newSessionId);
    
    // Clear chat history
    setChatHistory([]);
    
    // Reset Rate Answer button related state
    setCurrentMessage(null);
    setResponseCompleteStatus(false);
    setIsNewQuestionAsked(false);
    setFeedbackSubmitted({});
    
    // Show success message
    setShowSessionMessage(true);
    setTimeout(() => setShowSessionMessage(false), 3000);
  };

  useEffect(() => {
    // Fetch API configuration from the backend
    const fetchConfig = async () => {
      try {
        const response = await axios.get(configUrl);
        setConfig(response.data);
      } catch (error) {
        console.error("❌ Error fetching config:", error);
      }
    };
    fetchConfig();

    // Load existing session history if available
    const fetchSessionHistory = async () => {
      setSessionLoading(true);
      try {
        const history = await loadSessionHistory(backendUrl);
        if (history && history.length > 0) {
          setChatHistory(history);
          console.log("📚 Loaded existing session history");
        }
      } catch (error) {
        console.error("❌ Error loading session history:", error);
      } finally {
        setSessionLoading(false);
      }
    };
    fetchSessionHistory();

    // Initialize Socket.IO connection
    const socket = io(backendUrl, {
      path: "/socket.io",
      transports: ["websocket"],
      pingInterval: 10000,
      pingTimeout: 30000,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 2000,
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("✅ Socket.IO connected:", socket.id);
      setSocketConnected(true);
    });

    socket.on("response", (data) => {
      console.log("💬 Received response:", data);
    
      // Skip the 'Processing your request...' signal
      if (data.message === "Processing your request...") {
        return;
      }
      
      // Mark that we've received a response, so we're now streaming content
      setIsStreaming(true);
      
      // Get trace context for distributed tracing - use the hook from component level
      const traceContext = getTraceContext();
    
      // Process sources if they're present
      if (data.sources) {
        setChatHistory((prev) => {
          const updated = [...prev];
          // Find the last AI message
          let lastAiIndex = -1;
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].sender === "ai") {
              lastAiIndex = i;
              break;
            }
          }
          
          if (lastAiIndex !== -1) {
            // Process and enhance sources for better citation display
            const enhancedSources = data.sources.map(source => ({
              ...source,
              // Ensure these fields exist for citation display
              title: source.title || source.document_title || "Unknown Source",
              text: source.text || source.quote || source.content || "",
              url: source.url || source.document_url || (source.metadata ? source.metadata.url : null)
            }));
            
            // Deduplicate sources
            const uniqueSources = [];
            const seenIds = new Set();
            
            enhancedSources.forEach(source => {
              const sourceId = source.id || source.source_id;
              if (!seenIds.has(sourceId)) {
                seenIds.add(sourceId);
                uniqueSources.push(source);
              }
            });
            
            // Create a unique QA identifier if it doesn't exist
            const qa_id = updated[lastAiIndex].qa_id || `qa_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
            
            // Update with sources and preserve any existing message content
            const updatedMessage = {
              ...updated[lastAiIndex],
              processing: false,  // Remove processing flag
              qa_id: qa_id,
              sources: uniqueSources,
              // Only append data.message if it exists and isn't empty
              message: updated[lastAiIndex].message + (data.message && data.message.trim() !== "" ? data.message : "")
            };
            
            updated[lastAiIndex] = updatedMessage;
            
            // Emit finalize_qa event with trace context
            socket.emit("finalize_qa", {
              session_id: getSessionId(),
              qa_id: qa_id,
              answer: updatedMessage.message,
              citations: uniqueSources,
              trace_context: traceContext // Include trace context
            });
            
            // Set current message for feedback
            setCurrentMessage(updatedMessage);
            
            // Mark response complete
            setResponseCompleteStatus(true);
            setIsNewQuestionAsked(false);
          }
          setIsStreaming(false);
          return updated;
        });
        // Don't return here, allow message chunk processing to continue
      }
      
      // Process message chunks
      if (typeof data.message === "string" && data.message.trim() !== "") {
        console.log("Processing chunk:", data.message);
        
        setChatHistory((prev) => {
          const updated = [...prev];
          
          // Find the last AI message (prioritize processing message)
          let lastAiMessageIndex = -1;
          let processingMessageIndex = -1;
          
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].sender === "ai") {
              // Store the last AI message index if we haven't found one yet
              if (lastAiMessageIndex === -1) {
                lastAiMessageIndex = i;
              }
              
              // If this message has a processing flag, prioritize it
              if (updated[i].processing === true) {
                processingMessageIndex = i;
                break;
              }
            }
          }
          
          if (processingMessageIndex !== -1) {
            // Update the processing message - first real chunk replaces placeholder
            updated[processingMessageIndex] = {
              ...updated[processingMessageIndex],
              processing: false,
              message: data.message,
              qa_id: updated[processingMessageIndex].qa_id || `qa_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
            };
          } else if (lastAiMessageIndex !== -1) {
            // Append to the existing AI message
            updated[lastAiMessageIndex] = {
              ...updated[lastAiMessageIndex],
              message: updated[lastAiMessageIndex].message + data.message
            };
          } else {
            // No existing AI message found, create a new one (fallback)
            updated.push({ 
              sender: "ai", 
              message: data.message, 
              sources: [],
              qa_id: `qa_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
            });
          }
          
          return updated;
        });
      }
    });

    socket.on("disconnect", (reason) => {
      console.warn("❌ Socket.IO disconnected:", reason);
      setSocketConnected(false);
    });

    socket.on("reconnect_attempt", (attempt) => {
      console.log(`🔄 Reconnect attempt #${attempt}`);
    });

    socket.on("pong", () => {
      console.log("🟢 Received Pong from server");
    });

    socket.on("session_reset_confirmed", (data) => {
      console.log("🔄 Session reset confirmed:", data.session_id);
    });
    
    socket.on("feedback_confirmed", (data) => {
      console.log("✅ Feedback confirmed for qa_id:", data.qa_id);
      if (data.qa_id) {
        // Mark this Q&A pair as having received feedback
        setFeedbackSubmitted(prev => ({
          ...prev,
          [data.qa_id]: true
        }));
      }
    });

    // Periodically ping the server
    const pingInterval = setInterval(() => {
      if (socket.connected) {
        console.log("🔵 Sending Ping...");
        socket.emit("ping", { session_id: getSessionId() });
      }
    }, 10000);

    return () => {
      clearInterval(pingInterval);
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [backendUrl, configUrl]);

  // Send user message
  const handleSend = async () => {
    if (!input.trim()) return;

    // Indicate that a new question is being asked
    setIsNewQuestionAsked(true);
    setResponseCompleteStatus(false);
    
    // Reset streaming state to ensure processing message shows up
    setIsStreaming(false);

    // Get trace context for distributed tracing
    const traceContext = getTraceContext();

    // Create messages
    const userMessage = { 
      sender: "user", 
      message: input,
      timestamp: new Date().toISOString()
    };
    
    // Create AI placeholder with processing flag and unique ID
    const qaId = `qa_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const aiPlaceholder = { 
      sender: "ai", 
      processing: true,
      message: "",
      sources: [],
      timestamp: new Date().toISOString(),
      qa_id: qaId
    };

    // Clean up chat history by removing any existing processing messages before adding new ones
    setChatHistory(prev => {
      // Remove any existing processing messages to prevent duplicates
      const cleanHistory = prev.filter(msg => !(msg.sender === "ai" && msg.processing === true));
      return [...cleanHistory, userMessage, aiPlaceholder];
    });
    
    // Reset current message state
    setCurrentMessage(null);

    // Prepare data to send to API
    const messageData = {
      question: input,
      session_id: getSessionId(),
      qa_id: qaId,
      chat_history: chatHistory
        .filter(msg => !msg.processing) // Don't include processing messages in the history sent to backend
        .concat(userMessage)
        .map(chat => ({
          role: chat.sender === "user" ? "human" : "ai",
          content: chat.message,
        })),
      cognito_id: auth.user.profile.sub,
      session_type: "single",
      trace_context: traceContext // Include trace context in the request body
    };
    
    // Clear input field
    setInput("");

    try {
      // Include trace context in request headers
      const headers = {
        'X-Session-ID': getSessionId(),
        'traceparent': traceContext.traceparent,
        'tracestate': traceContext.tracestate,
        'X-QA-ID': qaId
      };

      const response = await axios.post(`${backendUrl}/api/ask`, messageData, { headers });
      console.log("📤 Sent message with trace context:", messageData);
      console.log("✅ Received response:", response.data);
    } catch (error) {
      console.error("❌ Error sending message:", error);
      
      // Update the AI placeholder to show an error message
      setChatHistory(prev => {
        const updated = [...prev];
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].processing === true) {
            updated[i] = {
              ...updated[i],
              processing: false,
              message: "Sorry, there was an error processing your request."
            };
            break;
          }
        }
        return updated;
      });
      
      setIsStreaming(false);
    }
  };

  // Export chat session as JSON
  const handleExport = () => {
    const date = new Date();
    const dateString = date.toISOString().split("T")[0];
    const timeString = date.toTimeString().split(" ")[0].replace(/:/g, "-");
    const dateTimeString = `${dateString}_${timeString}`;
    const data = {
      date: date.toISOString(),
      config,
      chatHistory,
    };
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ATLAS_${dateTimeString}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Handle logout
  const handleLogout = () => {
    const baseUrl = envConfig.api.frontendUrl || window.location.origin;
    const logoutUrl = `${envConfig.auth.logoutUrl}?client_id=${envConfig.auth.clientId}&logout_uri=${encodeURIComponent(
      baseUrl + "logout.html"
    )}`;
    window.location.href = logoutUrl;
  };

  // Enhanced ChatBox component with improved citation display
  const EnhancedChatBox = ({ chatHistory, isStreaming, sessionId }) => {
    const chatBoxRef = useRef(null);
  
    useEffect(() => {
      if (chatBoxRef.current) {
        chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
      }
    }, [chatHistory]);

    // Track when a message is fully complete
    const handleMessageComplete = (message) => {
      if (message && message.qa_id) {
        setCurrentMessage(message);
        setResponseCompleteStatus(true);
      }
    };
  
    return (
      <div className="chatBox" ref={chatBoxRef}>
        {chatHistory.map((chat, index) => {
          // Special handling for AI messages with processing flag
          if (chat.sender === "ai" && chat.processing === true && !isStreaming) {
            return (
              <div key={`${chat.sender}-${index}-processing`} className="aiMessage">
                <div className="messageContent">
                  <div className="processing-doc-context">
                    <span className="spinner-inline"></span>
                    <span>Processing your request...</span>
                  </div>
                </div>
              </div>
            );
          }
          
          // Regular message rendering (skip rendering processing messages when streaming)
          if (!(chat.sender === "ai" && chat.processing === true)) {
            return (
              <Message 
                key={`${chat.sender}-${index}`}
                chat={chat}
                sessionId={sessionId}
                onComplete={handleMessageComplete}
              />
            );
          }
          
          return null; // Skip rendering processing messages when streaming
        })}
      </div>
    );
  };

  return (
    <Routes>
      <Route path="/callback" element={<Callback />} />
      <Route
        path="/about"
        element={
          <AboutPage 
            onLogout={handleLogout}
            onRefresh={handleRefreshSession}
            showSessionMessage={showSessionMessage}
          />
        }
      />
      <Route
        path="/*"
        element={
          <div className="container">
            <Header 
              title="ATLAS: Analysis and Testing of Language Models for Archival Systems"
              onLogout={handleLogout}
              onRefresh={handleRefreshSession}
              showSessionMessage={showSessionMessage}
            />
            <div className="main-content">
              <div className="chatContainer">
                {sessionLoading ? (
                  <div className="loading-session">Loading session...</div>
                ) : (
                  <EnhancedChatBox 
                    chatHistory={chatHistory} 
                    isStreaming={isStreaming}
                    sessionId={getSessionId()}
                  />
                )}
                <MessageInput 
                  input={input} 
                  setInput={setInput} 
                  onSend={handleSend}
                  disabled={!socketConnected || isStreaming}
                />
              </div>
              <div className="right-sidebar">
                {currentMessage && currentMessage.qa_id && (
                  <FeedbackButtons
                    message={currentMessage}
                    question={currentMessage.question || chatHistory.find(msg => msg.sender === "user")?.message || ""}
                    sessionId={getSessionId()}
                    isResponseComplete={responseCompleteStatus}
                    isNewQuestionAsked={isNewQuestionAsked}
                    onComplete={(updatedMessage) => {
                      // Mark this message as having received feedback
                      if (currentMessage.qa_id) {
                        setFeedbackSubmitted(prev => ({
                          ...prev,
                          [currentMessage.qa_id]: true
                        }));
                      }
                    }}
                  />
                )}
                <ConfigBox 
                  config={config} 
                  onExport={handleExport} 
                />
              </div>
            </div>
          </div>
        }
      />
    </Routes>
  );
};

export default AtlasUI;