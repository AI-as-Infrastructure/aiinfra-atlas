/**
 * Stream Parser for Server-Sent Events
 * 
 * This utility properly parses SSE streams from the /api/ask/stream endpoint,
 * handling different event types and correctly assembling the response.
 */

/**
 * Parse and process a streaming response from the API
 * @param {ReadableStream} stream - Stream returned from fetch API
 * @param {Function} onMessage - Callback fired when a message is received
 * @param {Function} onDone - Callback fired when the stream is complete
 * @param {Function} onError - Callback fired on error
 * @returns {Function} - Cancellation function
 */
export function parseSSEStream(stream, onMessage, onDone, onError) {
  // Create a reader from the stream
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  
  // Debug stats to help diagnose issues
  const stats = {
    chunksReceived: 0,
    messagesProcessed: 0,
    contentEvents: 0,
    referenceEvents: 0,
    citationEvents: 0,
    unknownEvents: 0,
    errors: 0
  };
  
  function processChunk(chunk) {
    // Track chunks received for debugging
    stats.chunksReceived++;
    
    // Add the new chunk to our buffer
    buffer += chunk;
    console.log(`[StreamParser] Received chunk ${stats.chunksReceived}, buffer length now: ${buffer.length}`);
    
    // Process any complete messages in the buffer
    // SSE messages are separated by double newlines
    while (buffer.includes('\n\n')) {
      const endOfMessage = buffer.indexOf('\n\n');
      const message = buffer.substring(0, endOfMessage);
      buffer = buffer.substring(endOfMessage + 2);
      
      // Track messages processed
      stats.messagesProcessed++;
      
      // Parse the SSE message
      if (message.startsWith('data:') || message.includes('\ndata:')) {
        try {
          // Get event type if specified
          let eventType = null;
          
          // Check for explicit event type
          const eventMatch = message.match(/^event:\s*(\w+)/m);
          if (eventMatch) {
            eventType = eventMatch[1].toLowerCase();
            console.log(`[StreamParser] Found explicit event type: ${eventType}`);
          }
          
          // Find all data lines (there could be multiple in one message)
          const dataMatches = message.match(/^data:(.*?)$/gm);
          
          if (!dataMatches || dataMatches.length === 0) {
            console.warn('[StreamParser] No data line found in SSE message');
            return;
          }
          
          // Join multiline data if needed (some SSE implementations split JSON across lines)
          const dataContent = dataMatches
            .map(line => line.substring(5).trim()) // Remove 'data:' prefix and trim
            .join('');
          
          // Try to parse as JSON
          let parsedData;
          try {
            parsedData = JSON.parse(dataContent);
          } catch (e) {
            console.warn('[StreamParser] Failed to parse JSON, treating as plain text');
            // If it's not valid JSON, treat as plain text
            parsedData = { text: dataContent };
          }
          
          // Log message structure for debugging
          console.log('[StreamParser] Message keys:', Object.keys(parsedData).join(', '));
          
          // Set event type based on explicit type or content
          if (eventType) {
            parsedData._eventType = eventType;
            
            // Track event types for debugging
            if (eventType === 'content') stats.contentEvents++;
            else if (eventType === 'references') stats.referenceEvents++;
            else if (eventType === 'citations') stats.citationEvents++;
            else stats.unknownEvents++;
          } 
          // Infer type from content if not explicitly specified
          else if (parsedData.references) {
            parsedData._eventType = 'references';
            stats.referenceEvents++;
            console.log(`[StreamParser] Inferred references event, found ${Object.keys(parsedData.references).length} references`);
          } else if (parsedData.citations) {
            parsedData._eventType = 'citations';
            stats.citationEvents++;

          } else if (parsedData.chunk && parsedData.chunk.type === 'text') {
            parsedData._eventType = 'content';
            stats.contentEvents++;
            console.log(`[StreamParser] Inferred content event from chunk, text length: ${parsedData.chunk.text.length}`);
          } else if (parsedData.responseComplete === true) {
            parsedData._eventType = 'complete';
            console.log('[StreamParser] Inferred completion event');
          } else if (parsedData.text && typeof parsedData.text === 'string') {
            parsedData._eventType = 'content';
            stats.contentEvents++;
            console.log(`[StreamParser] Inferred content event from text field, length: ${parsedData.text.length}`);
          } else {
            parsedData._eventType = 'unknown';
            stats.unknownEvents++;
            console.log('[StreamParser] Unknown event type, data structure:', Object.keys(parsedData));
          }
          
          // Call the message handler with the parsed data
          onMessage(parsedData);
          
          // If this is the final message, call the done handler
          if (parsedData.responseComplete === true || parsedData._eventType === 'complete') {
            // Log final stats
            console.log('[StreamParser] Stream complete, stats:', stats);
            onDone(parsedData);
          }
        } catch (error) {
          stats.errors++;
          console.error('[StreamParser] Error parsing SSE message:', error, message);
          onError(error);
        }
      }
    }
  }
  
  // Read the stream chunk by chunk
  function read() {
    reader.read().then(({ done, value }) => {
      if (done) {
        // Process any remaining data in the buffer
        if (buffer.length > 0) {
          try {
            const message = buffer.trim();
            if (message.startsWith('data:')) {
              const jsonData = message.substring(5).trim();
              let parsedData;
              try {
                parsedData = JSON.parse(jsonData);
              } catch (e) {
                // If it's not valid JSON, treat as plain text
                parsedData = { text: jsonData };
              }
              onMessage(parsedData);
              
              // If this is the final message, call the done handler
              if (parsedData.responseComplete === true) {
                onDone(parsedData);
              } else {
                // Force completion since stream is done
                onDone({ ...parsedData, responseComplete: true });
              }
            }
          } catch (e) {
            console.error('[StreamParser] Error processing final buffer:', e);
            onDone({ responseComplete: true });
          }
        } else {
          // If no data left in buffer, still signal completion
          onDone({ responseComplete: true });
        }
        
        // Log final stats
        console.log('[StreamParser] Stream processing complete, final stats:', stats);
        return;
      }
      
      // Process this chunk
      const chunk = decoder.decode(value, { stream: true });
      processChunk(chunk);
      
      // Continue reading
      read();
    }).catch(error => {
      stats.errors++;
      console.error('[StreamParser] Error reading stream:', error);
      onError(error);
    });
  }
  
  // Start reading the stream
  read();
  
  // Return a function to cancel the stream
  return function() {
    reader.cancel();
  };
}
