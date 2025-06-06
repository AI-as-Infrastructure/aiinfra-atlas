<template>
	<div class="user-input">
	  <div v-if="errorMessage" class="error-message mb-2">
		{{ errorMessage }}
	  </div>
	  <form v-if="!isGenerating" @submit.prevent="onSend">
		<div class="field has-addons">
		  <!-- Only show corpus selector if there are valid corpus options -->
		  <div v-if="hasCorpusOptions" class="control is-corpus-selector">
			<div class="select">
			  <select v-model="selectedCorpus">
				<option v-for="option in corpusOptions" :key="option.value" :value="option.value">
				  {{ option.label }}
				</option>
			  </select>
			</div>
		  </div>
		  <div class="control is-expanded">
			<input 
			  class="input" 
			  v-model="input" 
			  type="text" 
			  placeholder="Type your question..." 
			  :disabled="isGenerating"
			/>
		  </div>
		  <div class="control">
			<button 
			  class="button send-button" 
			  :disabled="!input.trim() || isGenerating"
			  :class="{ 'is-loading': isGenerating }"
			  title="Send"
			>
			  ➤
			</button>
		  </div>
		</div>
	  </form>
	  <div v-else class="has-text-centered my-4">
		<span class="tag is-warning is-medium" style="background: #fffbe6; color: #b8860b; border: 1px solid #f7e07d; font-weight: 500; letter-spacing: 0.01em;">
		  Processing document chunks (fetch-k)...
		</span>
	  </div>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted, watch, computed, onBeforeUnmount } from 'vue'
  import { useSessionStore } from '@/stores/session'
  import { deduplicateText } from '@/utils/textUtils'

  // Define emits with compiler macro
  const emit = defineEmits(['input-active-change'])
  
  const input = ref('')
  const isGenerating = ref(false)
  const session = useSessionStore()
  const corpusOptions = ref([])
  const selectedCorpus = ref('all')
  const inputActive = ref(false)
  const errorMessage = ref('')
  const selectedProvider = ref(null)
  const eventSource = ref(null)
  
  // Computed property to determine if corpus options are available
  const hasCorpusOptions = computed(() => {
    return corpusOptions.value && 
         corpusOptions.value.length > 0 && 
         corpusOptions.value.length > 1  // Only show if we have more than just the 'all' option
  })
  
  // Helper function to build API URLs correctly
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
  
  // Fetch corpus options and config from API
  async function fetchCorpusOptions() {
    try {
      // Construct the correct API URL
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const configUrl = apiUrl ? 
        (apiUrl.endsWith('/') ? `${apiUrl}api/config` : `${apiUrl}/api/config`) : 
        '/api/config';
      
      console.log('Fetching configuration from:', configUrl);
      const response = await fetch(configUrl);
      
      if (response.ok) {
        const data = await response.json()
        if (data.CORPUS_OPTIONS && Array.isArray(data.CORPUS_OPTIONS)) {
          corpusOptions.value = data.CORPUS_OPTIONS
        }
        
        // Check if there's a provider in the config
        if (data.llm_provider) {
          selectedProvider.value = data.llm_provider
        }
      }
    } catch (error) {
      console.error('Error fetching corpus options:', error)
      // Set to empty array on error
      corpusOptions.value = []
      errorMessage.value = 'Failed to load configuration. Please refresh the page or try again later.'
    }
  }
  
  onMounted(() => {
    fetchCorpusOptions()
    // Restore selected corpus from session store if available
    if (session.corpusFilter) {
      selectedCorpus.value = session.corpusFilter
    }
  })
  
  // Clean up EventSource on component unmount
  onBeforeUnmount(() => {
    if (eventSource.value) {
      console.log('[UserInput] Closing EventSource connection');
      eventSource.value.close();
      eventSource.value = null;
    }
  })
  
  // Keep session store in sync with dropdown
  watch(selectedCorpus, (newVal) => {
    // Simply update the corpus filter without affecting chat history
    session.setCorpusFilter(newVal)
  })
  
  // Watch for changes in the input field to emit input-active-change event
  watch(input, (newVal) => {
    // Only emit if the value changes from empty to non-empty or vice versa
    const newActive = newVal.trim().length > 0
    if (newActive !== inputActive.value) {
        inputActive.value = newActive
        emit('input-active-change', newActive)
    }
  })
  
  // Close EventSource connection
  function closeEventSource() {
    if (eventSource.value) {
      console.log('[UserInput] Closing EventSource connection');
      eventSource.value.close();
      eventSource.value = null;
    }
  }
  
  // Set up SSE connection and process stream
  async function setupSSE(payload) {
    // Close any existing connection
    if (eventSource.value) {
      console.log('[UserInput] Closing previous EventSource');
      eventSource.value.close();
      eventSource.value = null;
    }
    
    // Set up the streaming URL
    const askUrl = getApiUrl('/api/ask/stream');
    
    // Variables to track the streaming state
    let answer = '';
    let currentCitations = [];
    let assistantMessageAdded = false;
    
    // Set up headers for the fetch request
    const headers = {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    };
    
    // Add traceparent if available
    if (session.traceparent) {
      headers['traceparent'] = session.traceparent;
    }
    
    try {
      console.log('[UserInput] Sending streaming request with payload:', 
        { question: payload.question.substring(0, 50) + '...', sessionId: payload.session_id });
      
      // Create the streaming request
      const response = await fetch(askUrl, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      
      // Get a reader for the stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      // Process the stream chunks
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          console.log('[UserInput] Stream complete');
          // Process any remaining buffer
          if (buffer) {
            processSSEMessage(buffer);
          }
          break;
        }
        
        // Decode the chunk and add to buffer
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        // Process any complete SSE messages in the buffer
        let processedBuffer = processSSEMessages(buffer);
        // Update buffer with what's left after processing
        buffer = processedBuffer;
      }
      
      // Finalize the response
      console.log('[UserInput] Stream completed');
      session.setResponseComplete(true);
      session.setNewQuestionAsked(false);
      return true;
    } catch (error) {
      console.error('[UserInput] Error in SSE processing:', error);
      errorMessage.value = error.message || 'Error processing response';
      
      // Add error message to chat if needed
      if (!assistantMessageAdded) {
        session.addMessage({ 
          role: 'assistant', 
          content: `Sorry, there was an error: ${errorMessage.value}`,
          error: true
        });
      }
      
      // Reset session state
      session.setResponseComplete(false);
      session.setNewQuestionAsked(false);
      return false;
    }
    
    // Process SSE messages from the buffer
    function processSSEMessages(currentBuffer) {
      while (currentBuffer.includes('\n\n')) {
        const endOfMessage = currentBuffer.indexOf('\n\n');
        const message = currentBuffer.substring(0, endOfMessage);
        
        // Process the message
        processSSEMessage(message);
        
        // Remove the processed message from the buffer
        currentBuffer = currentBuffer.substring(endOfMessage + 2);
      }
      
      // Return what's left in the buffer for next round
      return currentBuffer;
    }
    
    // Process a single SSE message
    function processSSEMessage(message) {
      try {
        // Get event type
        const eventMatch = message.match(/^event:\s*(\w+)/m);
        const eventType = eventMatch ? eventMatch[1] : 'message';
        
        // Get data content
        const dataMatch = message.match(/^data:(.*?)$/m);
        if (!dataMatch) return;
        
        // Parse the data
        const dataContent = dataMatch[1].trim();
        const data = JSON.parse(dataContent);
        
        console.log(`[UserInput] Processing ${eventType} event:`, 
          Object.keys(data).join(', '));
        
        // Handle different event types
        switch (eventType) {
          case 'error':
            handleErrorEvent(data);
            break;
          
          case 'content':
            handleContentEvent(data);
            break;
          
          case 'references':
          case 'citations':
            handleCitationsEvent(data);
            break;
          
          case 'complete':
            handleCompleteEvent(data);
            break;
          
          default:
            // For unnamed events, check content type
            if (data.error) {
              handleErrorEvent(data);
            } else if (data.chunk && data.chunk.type === 'text') {
              handleContentEvent(data);
            } else if (data.references || data.citations) {
              handleCitationsEvent(data);
            } else if (data.responseComplete) {
              handleCompleteEvent(data);
            }
            break;
        }
      } catch (error) {
        console.error('[UserInput] Error processing SSE message:', error);
      }
    }
    
    // Handle error events
    function handleErrorEvent(data) {
      const errorDetail = data.error?.detail || 
                         data.error?.message || 
                         'Unknown error';
      
      console.error('[UserInput] Error in stream:', errorDetail);
      errorMessage.value = errorDetail;
      
      // Add error message to chat if needed
      if (!assistantMessageAdded) {
        session.addMessage({ 
          role: 'assistant', 
          content: `Sorry, there was an error: ${errorDetail}`,
          error: true
        });
        assistantMessageAdded = true;
      }
    }
    
    // Handle content (text) events
    function handleContentEvent(data) {
      // Extract text from chunk or text property
      const newText = data.chunk?.text || data.text || '';
      if (!newText) return;
      
      console.log(`[UserInput] Received content, length: ${newText.length}`);
      
      // Update answer text
      if (answer) {
        // Append to existing text
        answer += newText;
        
        // Check for duplications in longer text
        if (answer.length > 600) {
          answer = deduplicateText(answer);
        }
      } else {
        answer = newText;
      }
      
      // Update or add message
      if (!assistantMessageAdded) {
        console.log('[UserInput] Adding new assistant message');
        session.addMessage({ 
          role: 'assistant', 
          content: answer,
          citations: currentCitations.length > 0 ? currentCitations : undefined,
          citations_loading: currentCitations.length === 0 // Show loading indicator if no citations yet
        });
        assistantMessageAdded = true;
      } else {
        // Update existing message - PRESERVE existing message properties
        const lastMessageIndex = session.chatHistory.length - 1;
        const lastMessage = session.chatHistory[lastMessageIndex];
        
        // Use session.updateMessage to properly trigger reactivity
        session.updateMessage(lastMessageIndex, {
          ...lastMessage,  // Preserve all existing properties including citations
          content: answer   // Update only the content
        });
      }
    }
    
    // Handle citation events
    function handleCitationsEvent(data) {
      // Get citations from data (could be in different formats)
      const citations = data.citations || [];
      const references = data.references || {};
      
      // Process citations array
      if (citations.length > 0) {

        currentCitations = citations;
      }
      // Process references object
      else if (Object.keys(references).length > 0) {
        console.log(`[UserInput] Received ${Object.keys(references).length} references`);
        currentCitations = Object.entries(references).map(([id, ref]) => ({
          id,
          text: ref.text || ref.content || '',
          metadata: ref.metadata || {},
          source: ref.metadata?.source || '',
          date: ref.metadata?.date || '',
          page: ref.metadata?.page || '',
          corpus: ref.metadata?.corpus || ''
        }));
      }
      
      // Update citations in existing message or create a new one if needed
      if (assistantMessageAdded) {
        // Get the last message index
        const lastMessageIndex = session.chatHistory.length - 1;
        const lastMessage = session.chatHistory[lastMessageIndex];
        
        // Update the message with citations but preserve existing content
        session.updateMessage(lastMessageIndex, {
          ...lastMessage,
          citations: currentCitations,
          citations_loading: false // Remove loading indicator
        });
      } else if (currentCitations.length > 0) {
        // No assistant message yet - this happens when citations come before content
        session.addMessage({
          role: 'assistant',
          content: '', // Empty content that will be filled later
          citations: currentCitations,
          citations_loading: false
        });
        assistantMessageAdded = true;
      }
    }
    
    // Handle completion events
    function handleCompleteEvent(data) {
      console.log('[UserInput] Received completion event');
      
      // Use final text if provided
      if (data.responseText && data.responseText !== answer) {
        answer = deduplicateText(data.responseText);
      }
      
      // Use final citations if provided
      if (data.citations && data.citations.length > 0) {
        currentCitations = data.citations;
      }
      
      // Ensure we have a message
      if (!assistantMessageAdded) {
        session.addMessage({ 
          role: 'assistant', 
          content: answer,
          citations: currentCitations.length > 0 ? currentCitations : undefined
        });
      } else {
        // Update final content
        const lastMessageIndex = session.chatHistory.length - 1;
        const lastMessage = session.chatHistory[lastMessageIndex];
        
        // Use proper update method
        session.updateMessage(lastMessageIndex, {
          ...lastMessage,
          content: answer,
          citations: currentCitations.length > 0 ? currentCitations : lastMessage.citations
        });
      }
      
      // Mark as complete
      session.setResponseComplete(true);
    }
  } // Missing closing brace for setupSSE function
  
  async function onSend() {
    if (!input.value.trim()) return
    
    // Reset error message
    errorMessage.value = ''
    isGenerating.value = true
    
    // Log the question we're sending
    console.log('[UserInput] Sending question:', input.value)
    
    // Get the current and previous corpus filters
    const corpusFilter = selectedCorpus.value
    const previousCorpusFilter = session.corpusFilter
    
    // Set some state for the session
    session.setResponseComplete(false)
    session.setNewQuestionAsked(true)
    
    // Add user's question to history first
    const question = input.value
    session.addMessage({ role: 'user', content: question })
    
    try {
      // Always generate a new QA ID for each new question
      session.newQaId()
      
      // Prepare the request payload
      const payload = {
        question,
        session_id: session.sessionId,
        qa_id: session.qaId,
        chat_history: session.chatHistory.map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        corpus_filter: corpusFilter,
        previous_corpus_filter: previousCorpusFilter
      }
      
      // Add provider if specified
      if (selectedProvider.value) {
        payload.provider = selectedProvider.value
      }
      
      // Add trace context if available
      if (session.traceparent) {
        payload.trace_context = {
          traceparent: session.traceparent,
          tracestate: session.tracestate
        }
      }
      
      // Set up SSE connection and handle streaming
      await setupSSE(payload)
    } catch (error) {
      console.error('[UserInput] Error generating answer:', error)
      
      // Set error message for UI display
      errorMessage.value = error.message || 'Error generating response. Please try again.'
      
      // Reset flags on error and show error message
      session.setResponseComplete(false)
      session.setNewQuestionAsked(false)
      
      // Add error message to chat history
      session.addMessage({ 
        role: 'assistant', 
        content: `Sorry, there was an error generating a response: ${errorMessage.value}`,
        error: true
      })
    } finally {
      // Reset input field
      input.value = ''
      isGenerating.value = false
    }
  }
  </script>

<style scoped>
/* Minimalist user input and filter styles */
.user-input {
  background: transparent;
  padding: 1rem 1.2rem;
  border-radius: 6px;
}

.error-message {
  color: #e74c3c;
  background-color: #fdedec;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.field {
  margin-bottom: 0;
}

.control.is-corpus-selector {
  min-width: 120px;
  max-width: 220px;
  flex: 0 1 220px;
  overflow: hidden;
}

.select {
  background: none !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0;
  margin: 0;
  height: 2.2rem;
  display: flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  flex: 1 1 0%;
}
.select select {
  min-width: 0;
  max-width: 100%;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 2.2em; /* space for arrow */
  display: block;
}
.select option {
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
}
.select select {
  background: none !important;
  color: #111 !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  font-size: 1rem;
  height: 2.2rem;
  padding: 0 0.6rem 0 0.6rem;
  margin: 0;
  outline: none;
  appearance: none;
  min-width: 110px;
  border-radius: 2px 0 0 2px !important;
}

/* Make dropdown arrow black */
.select::after {
  border-color: #000 !important;
}
input.input {
  background: #fff !important;
  color: #111 !important;
  border: none !important;
  border-radius: 2px !important;
  box-shadow: none !important;
  font-size: 1rem;
  height: 2.2rem;
  padding: 0.25rem 0.75rem;
  transition: border 0.2s;
  margin-left: 0;
  caret-color: #111;
}
input.input::placeholder {
  color: #111;
  opacity: 0.6;
}
.my-4 {
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.mb-2 {
  margin-bottom: 0.5rem;
}

/* Button styling */
.send-button {
  background: #000 !important;
  color: #fff !important;
  border: none !important;
  border-radius: 2px !important;
  height: 2.2rem !important;
  width: 2.2rem !important;
  font-size: 1rem !important;
  line-height: 1 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
  position: relative !important;
}

/* Ensure the button is black even when disabled */
.send-button:disabled {
  background: #000 !important;
  color: #fff !important;
  opacity: 0.7 !important;
  cursor: not-allowed !important;
}

/* Fix for Firefox rendering issues */
.send-button:before {
  content: '' !important;
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  background: transparent !important;
}
</style>