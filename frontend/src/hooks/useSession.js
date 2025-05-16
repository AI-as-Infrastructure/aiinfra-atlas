import { v4 as uuidv4 } from "uuid";
import axios from "axios";
import { useState, useEffect } from "react";

export const useSession = () => {
  const [sessionLoading, setSessionLoading] = useState(true);
  
  const getSessionId = () => {
    let sessionId = localStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = uuidv4();
      localStorage.setItem("session_id", sessionId);
      console.log("🆕 Created new session ID:", sessionId);
    }
    return sessionId;
  };

  // Generate W3C-compliant trace context for distributed tracing
  const generateTraceContext = () => {
    // Format: 00-<trace-id>-<parent-id>-01
    // trace-id is 32 hex characters (16 bytes)
    // parent-id is 16 hex characters (8 bytes)
    const traceId = uuidv4().replace(/-/g, '') + Math.random().toString(16).substring(2, 10);
    const parentId = Math.random().toString(16).substring(2, 18);
    
    return {
      traceparent: `00-${traceId}-${parentId}-01`,
      tracestate: 'phoenix=1'
    };
  };

  // Store the current trace context in session storage
  const storeTraceContext = (traceContext) => {
    if (traceContext) {
      sessionStorage.setItem("trace_context", JSON.stringify(traceContext));
    }
  };

  // Get the current trace context from session storage or generate a new one
  const getTraceContext = () => {
    const storedContext = sessionStorage.getItem("trace_context");
    if (storedContext) {
      try {
        return JSON.parse(storedContext);
      } catch (e) {
        console.error("Error parsing stored trace context:", e);
      }
    }
    
    // Generate new trace context if none exists or parsing failed
    const newContext = generateTraceContext();
    storeTraceContext(newContext);
    return newContext;
  };

  const resetSession = (socket) => {
    const newSessionId = uuidv4();
    localStorage.setItem("session_id", newSessionId);
    
    // Generate new trace context for the new session
    const traceContext = generateTraceContext();
    storeTraceContext(traceContext);
    
    // Notify backend about session reset with trace context
    if (socket && socket.connected) {
      socket.emit("session_reset", { 
        session_id: newSessionId,
        timestamp: new Date().toISOString(),
        operation: "reset_session",
        trace_context: traceContext
      });
    }
    
    return newSessionId;
  };

  const loadSessionHistory = async (backendUrl) => {
    setSessionLoading(true);
    const sessionId = getSessionId();
    const traceContext = getTraceContext();
    
    try {
      // Add trace context to the request header
      const response = await axios.get(`${backendUrl}/api/session/${sessionId}`, {
        headers: {
          'X-Session-ID': sessionId,
          'traceparent': traceContext.traceparent,
          'tracestate': traceContext.tracestate,
          'X-Trace-Operation': 'load_session',
          'X-Trace-Timestamp': new Date().toISOString()
        }
      });
      console.log("📚 Loaded session history with trace context");
      setSessionLoading(false);
      return response.data.chat_history || [];
    } catch (error) {
      console.log("No existing session found or error loading session");
      setSessionLoading(false);
      return [];
    }
  };

  // Generate a unique QA ID for tracking question-answer pairs
  const generateQaId = () => {
    return `qa_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  };

  return { 
    getSessionId, 
    resetSession, 
    loadSessionHistory,
    generateQaId,
    generateTraceContext,
    getTraceContext,
    sessionLoading 
  };
};