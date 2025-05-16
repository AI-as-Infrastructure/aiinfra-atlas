import { useSessionStore } from '@/stores/session'
import { generateTraceparent } from '@/utils/trace'
import { parseSSEStream } from './useStreamParser'

/**
 * Helper function to build API URLs correctly
 * @param {string} path - API path (should start with /)
 * @returns {string} - Complete API URL
 */
function getApiUrl(path) {
  // Get the base API URL from environment
  const apiUrl = import.meta.env.VITE_API_URL || '';
  
  // Make sure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  
  // For absolute URLs, just append the path
  if (apiUrl.startsWith('http://') || apiUrl.startsWith('https://')) {
    // Remove trailing slash from apiUrl if present
    const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
    return `${baseUrl}${normalizedPath}`;
  }
  
  // For relative URLs, use as is
  return normalizedPath;
}

/**
 * Send a question to the LLM and process the streaming response
 * @param {string} question - The question to ask
 * @param {Array} chatHistory - Previous chat messages
 * @param {string} corpusFilter - Corpus filter to apply
 * @param {string} previousCorpusFilter - Previous corpus filter
 * @param {Function} onUpdate - Callback for streaming updates (receives accumulated text)
 * @param {Function} onDone - Callback for completion (receives final text and citations)
 * @param {Function} onError - Callback for error handling
 * @param {string} provider - Optional LLM provider to use
 */
export async function sendQuestion(
  question, 
  chatHistory = [], 
  corpusFilter = 'all', 
  previousCorpusFilter = null,
  onUpdate = () => {},
  onDone = () => {},
  onError = () => {},
  provider = null
) {
  const session = useSessionStore()
  // Generate new QA ID only if not already set by caller
  if (!session.qaId) {
    session.newQaId()
  }
  
  // Use existing traceparent or generate a new one for the session
  let traceparent = session.traceparent
  if (!traceparent) {
    traceparent = generateTraceparent()
    session.setTraceContext(traceparent, null)
  }

  // Variables to track accumulated text and citations
  let accumulatedText = '';
  let citations = [];
  let receivedReferences = false;
  
  console.log('[AskAPI] Sending question:', { 
    question: question.substring(0, 50) + '...',
    sessionId: session.sessionId,
    qaId: session.qaId,
    corpusFilter
  });
  
  // Helper functions within scope of sendQuestion
  
  /**
   * Check if data contains text content in any format
   */
  function hasTextContent(data) {
    return (
      (data.chunk && data.chunk.type === 'text' && data.chunk.text) ||
      (data.text && typeof data.text === 'string')
    );
  }

  /**
   * Check if data contains citations or references
   */
  function hasCitationsOrReferences(data) {
    return (
      (data.citations && Array.isArray(data.citations)) ||
      (data.references && typeof data.references === 'object')
    );
  }

  /**
   * Find the index where the new text starts to overlap with existing text
   */
  function findOverlapIndex(existingText, newText) {
    // Handle empty cases
    if (!existingText || !newText) return 0;
    
    // If existing text ends with the start of new text, find where they overlap
    for (let i = Math.min(existingText.length, newText.length); i >= 10; i--) {
      const endOfExisting = existingText.substring(existingText.length - i);
      const startOfNew = newText.substring(0, i);
      
      if (endOfExisting === startOfNew) {
        return i;
      }
    }
    
    return 0;
  }

  /**
   * Process text content from any supported format
   */
  function processTextContent(data) {
    let newText = '';
    
    // Extract text from various formats
    if (data.chunk && data.chunk.type === 'text' && data.chunk.text) {
      newText = data.chunk.text;
    } else if (data.text && typeof data.text === 'string') {
      newText = data.text;
    }
    
    // Skip empty text
    if (!newText || newText.length === 0) {
      console.log('[AskAPI] Received empty text content, skipping');
      return;
    }
    
    console.log('[AskAPI] Processing text content, length:', newText.length);
    
    // Check for citation markers in text
    if (newText.includes('[[CITATIONS]]')) {

      const parts = newText.split('[[CITATIONS]]');
      
      // Update text content (before the marker)
      newText = parts[0].trim();
      
      // Try to parse citations (after the marker)
      if (parts.length > 1 && parts[1].trim()) {
        try {
          const citationsJson = parts[1].trim();
          const parsedCitations = JSON.parse(citationsJson);
          
          if (Array.isArray(parsedCitations) && parsedCitations.length > 0) {

            citations = parsedCitations;
            setTimeout(() => onUpdate({ type: 'citations', citations }), 0);
          }
        } catch (e) {
          console.error('[AskAPI] Error parsing citations from marker:', e);
        }
      }
    }
    
    // Check for duplicates - but with smarter comparison to handle streaming
    if (accumulatedText === newText) {
      console.log('[AskAPI] Text unchanged, skipping update');
      return;
    }
    
    // Special case: if backend sends entire text each time (not incremental)
    // Detect if new content is not an extension of previous content
    if (accumulatedText && newText.length > accumulatedText.length && 
        !newText.startsWith(accumulatedText) &&
        !accumulatedText.endsWith(newText.substring(0, 20)) &&
        newText.length > 100) {
      
      console.log('[AskAPI] Detected non-incremental update, replacing text');
      
      // If the text is significantly different, check if it's an entirely new response
      // or just a non-incremental update
      
      // If the new text is much longer, it's likely a complete replacement
      if (newText.length > accumulatedText.length * 1.5) {
        console.log('[AskAPI] Detected complete replacement, length difference is significant');
        accumulatedText = newText;
      }
      // If the beginnings are completely different, it's likely a replacement
      else if (!newText.substring(0, 50).includes(accumulatedText.substring(0, 20))) {
        console.log('[AskAPI] Detected complete replacement, beginning is different');
        accumulatedText = newText;
      }
      // If the new text is very long, check for internal duplication
      else if (newText.length > 1000) {
        // Check if the text might contain duplication within itself
        const firstQuarter = newText.substring(0, Math.floor(newText.length / 4));
        const secondQuarter = newText.substring(Math.floor(newText.length / 4), Math.floor(newText.length / 2));
        
        if (newText.indexOf(firstQuarter, Math.floor(newText.length / 2)) !== -1) {
          console.log('[AskAPI] Detected internal duplication in single-chunk response');
          // Only use the first half since the second half is likely a duplicate
          accumulatedText = newText.substring(0, Math.floor(newText.length / 2));
        } else if (newText.indexOf(secondQuarter, Math.floor(newText.length / 2)) !== -1) {
          // More subtle duplication
          console.log('[AskAPI] Detected partial internal duplication');
          accumulatedText = newText.substring(0, Math.floor(newText.length * 0.6));
        } else {
          // No obvious duplication, use the full new text
          accumulatedText = newText;
        }
      } else {
        // Default case - just use the new text
        accumulatedText = newText;
      }
    } 
    else {
      // Normal streaming case: check overlap and append new content
      const overlapIndex = findOverlapIndex(accumulatedText, newText);
      
      if (overlapIndex > 0 && overlapIndex < newText.length) {
        // Append only the new part
        accumulatedText += newText.substring(overlapIndex);
      } else if (!accumulatedText.includes(newText)) {
        // No overlap found and not a duplicate, just append
        accumulatedText += newText;
      } else {
        console.log('[AskAPI] Text chunk already included, skipping');
        return;
      }
    }
    
    // Send updated text to UI
    console.log('[AskAPI] Updating with new text content, total length:', accumulatedText.length);
    setTimeout(() => onUpdate({ type: 'text', text: accumulatedText }), 0);
  }

  /**
   * Process citations or references data
   */
  function processCitationsOrReferences(data) {
    let eventCitations = [];
    
    // Process references object (key-value format)
    if (data.references && typeof data.references === 'object') {
      eventCitations = Object.entries(data.references).map(([id, ref]) => ({
        id,
        text: ref.text || ref.content || '',
        metadata: ref.metadata || {},
        source: ref.metadata?.source || '',
        date: ref.metadata?.date || '',
        page: ref.metadata?.page || '',
        corpus: ref.metadata?.corpus || ''
      }));

    }
    
    // Process citations array
    if (data.citations && Array.isArray(data.citations)) {
      eventCitations = data.citations;

    }
    
    // Store citations for later use and send update
    if (eventCitations.length > 0) {
      citations = eventCitations;

      setTimeout(() => onUpdate({ type: 'citations', citations: eventCitations }), 0);
    }
  }

  try {
    // Format chat history for the backend
    // The backend expects a specific format with role and content properties
    const formattedChatHistory = chatHistory.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    // Prepare the request payload to match the refactored backend's expectations
    const payload = {
      question,
      session_id: session.sessionId,
      qa_id: session.qaId,
      chat_history: formattedChatHistory,
      corpus_filter: corpusFilter,
      previous_corpus_filter: previousCorpusFilter
    };

    // Add trace context if available
    if (traceparent) {
      payload.trace_context = {
        traceparent,
        tracestate: session.tracestate
      };
    }

    // Add provider if specified
    if (provider) {
      payload.provider = provider;
    }

    // Make the API request
    const response = await fetch(getApiUrl('/api/ask/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'traceparent': traceparent,
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      // Get error details from response if possible
      try {
        const errorData = await response.json();
        throw new Error(`API error: ${errorData.error || response.statusText} (${response.status})`);
      } catch (e) {
        throw new Error(`API responded with status: ${response.status} - ${response.statusText}`);
      }
    }

    console.log('[AskAPI] Request sent, processing stream');
    
    // Parse the SSE stream using our specialized parser
    parseSSEStream(
      response.body,
      // On message (data chunk received)
      (data) => {
        // Check event type first to handle different types of messages
        const eventType = data._eventType || 'unknown';
        console.log('[AskAPI] Received event type:', eventType, 'Data keys:', Object.keys(data).join(', '));
        
        // First check for error
        if (data.error) {
          onError(new Error(data.error));
          return;
        }
        
        // Handle different event types with specific handlers
        switch (eventType) {
          // Handle event type 'content' or events containing text content
          case 'content':
            processTextContent(data);
            break;
            
          // Handle citation/reference events
          case 'references':
          case 'citations':
            processCitationsOrReferences(data);
            break;
            
          // Handle completion events
          case 'complete':
            // Nothing special needed here, completion is handled in onDone
            break;
            
          // Default: check content type based on data structure
          default:
            // Check for text content first
            if (hasTextContent(data)) {
              processTextContent(data);
            }
            
            // Then check for citations/references (could be in same message)
            if (hasCitationsOrReferences(data)) {
              processCitationsOrReferences(data);
            }
            break;
        }
      },
      // On done (stream complete)
      (finalData) => {
        console.log('[AskAPI] Stream complete');
        
        // Get final text - either from the data or our accumulated text
        let finalText = finalData.responseText || accumulatedText;
        if (!finalText && finalData.text) finalText = finalData.text;
        
        // Check for [[CITATIONS]] marker in the text - this is another way citations can be provided
        if (finalText && finalText.includes('[[CITATIONS]]')) {

          
          const parts = finalText.split('[[CITATIONS]]');
          // The actual text content is before the marker
          finalText = parts[0].trim();
          
          // Try to parse citations from the part after the marker
          if (parts.length > 1 && parts[1].trim()) {
            try {
              const citationsJson = parts[1].trim();
              const parsedCitations = JSON.parse(citationsJson);
              
              if (Array.isArray(parsedCitations) && parsedCitations.length > 0) {

                citations = parsedCitations;
                // Send an immediate update with the citations
                setTimeout(() => onUpdate({ type: 'citations', citations }), 0);
              }
            } catch (e) {
              console.error('[AskAPI] Error parsing citations from marker:', e);
            }
          }
        }
        
        // Check for duplicated content in final text - this happens sometimes with streaming
        if (finalText && finalText.length > 600) {
          // Look for large repeated chunks (possible duplication)
          console.log('[AskAPI] Checking for duplicated content in finalText (length:', finalText.length, ')');
          
          // Split the text into paragraphs
          const paragraphs = finalText.split('\n\n').filter(p => p.trim().length > 0);
          if (paragraphs.length > 1) {
            // Check for identical paragraphs
            const uniqueParagraphs = [];
            const seenParagraphs = new Set();
            
            for (const paragraph of paragraphs) {
              if (!seenParagraphs.has(paragraph) && paragraph.length > 20) {
                uniqueParagraphs.push(paragraph);
                seenParagraphs.add(paragraph);
              }
            }
            
            // If we removed duplicates, rebuild the text
            if (uniqueParagraphs.length < paragraphs.length) {
              console.log('[AskAPI] Found and removed duplicated paragraphs:', 
                paragraphs.length - uniqueParagraphs.length);
              finalText = uniqueParagraphs.join('\n\n');
            }
          }
        }
        
        // Final check for citations in the response data
        if (citations.length === 0) {
          if (finalData.citations && Array.isArray(finalData.citations)) {

            citations = finalData.citations;
          } else if (finalData.references && typeof finalData.references === 'object') {

            citations = Object.entries(finalData.references).map(([id, ref]) => ({
              id,
              text: ref.text || ref.content || '',
              metadata: ref.metadata || {},
              source: ref.metadata?.source || '',
              date: ref.metadata?.date || '',
              page: ref.metadata?.page || '',
              corpus: ref.metadata?.corpus || ''
            }));
          }
        }
        
        // Log the final state
        console.log('[AskAPI] Final text length:', finalText.length, 
                    'Citations:', citations.length);
        
        // Mark response as complete and call the callback with final text and citations
        session.setResponseComplete(true);
        onDone(finalText, citations);
      },
      // On error
      (error) => {
        console.error('[AskAPI] Stream parsing error:', error);
        onError(error);
      }
    )
    
    return true;
  } catch (error) {
    console.error('[AskAPI] Error sending question:', error);
    onError(error);
    return false;
  }
}