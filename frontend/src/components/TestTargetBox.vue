<script setup>
import { ref, onMounted } from 'vue'

const config = ref(null)
const error = ref(false)
const showSystemPromptModal = ref(false)
const systemPrompt = ref('')
const truncatedSystemPrompt = ref('')

const configDescriptions = {
  ATLAS_VERSION: "The version of the ATLAS application.",
  composite_target: "The combined identifier for the target configuration.",
  CHROMA_COLLECTION_NAME: "The Chroma collection name used for storing and retrieving document vectors.",
  embedding_model: "The model used to create vector embeddings.",
  large_retrieval_size: "The number of documents initially retrieved from the HNSW vector index (HNSW -K).",
  algorithm: "The algorithm used for vector similarity search.",
  search_type: "The retrieval algorithm used for searching the vector store.",
  search_k: "The number of top documents passed to the LLM for answer generation.",
  search_score_threshold: "The minimum similarity score required for document retrieval.",
  chunk_size: "The size of each text chunk stored in the vector index.",
  chunk_overlap: "The overlap between text chunks for better context.",
  llm_provider: "The provider of the language model.",
  llm_model: "The language model used to generate answers.",
  MULTI_CORPUS_VECTORSTORE: "If true, enables the corpus selector dropdown and multi-corpus vectorstore features."
};

// List of fields to exclude from display
const unwantedFields = [
  'CORPUS_OPTIONS', 'FULL_SYSTEM_PROMPT', 'SYSTEM_PROMPT',
  'target_id', 'target_version', 'citation_limit', 'index_name', 'redis_database'
];

function formatFieldName(key) {
  // Special cases
  const exceptions = {
    llm_provider: 'LLM Provider',
    llm_model: 'LLM Model',
    CHROMA_COLLECTION_NAME: 'Chroma Collection Name',
    MULTI_CORPUS_VECTORSTORE: 'Multi Corpus Vectorstore',
    composite_target: 'Composite Target',
    ATLAS_VERSION: 'Atlas Version'
  };
  if (exceptions[key]) return exceptions[key];
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

const filteredEntries = ref([])

async function fetchConfig() {
  try {
    const res = await fetch('/api/config')
    if (!res.ok) throw new Error('Failed to fetch /api/config')
    const data = await res.json()
    config.value = data
    
    // Extract system prompt data
    if (data.FULL_SYSTEM_PROMPT) {
      // Store the full system prompt
      systemPrompt.value = data.FULL_SYSTEM_PROMPT
      // Create truncated version for display
      truncatedSystemPrompt.value = data.SYSTEM_PROMPT || 
        (systemPrompt.value.length > 150 ? 
          systemPrompt.value.substring(0, 150) + '...' : 
          systemPrompt.value)
      
      console.log('Full system prompt loaded:', systemPrompt.value.length, 'characters')
    } else {
      console.warn('FULL_SYSTEM_PROMPT not found in config response')
    }
    
    // Filter unwanted fields and keep order as in response
    filteredEntries.value = Object.entries(data).filter(([k]) =>
      !unwantedFields.includes(k)
    )
  } catch (e) {
    error.value = true
    console.error('Error fetching config:', e)
  }
}

onMounted(fetchConfig)

function capitalizeFirst(val) {
  if (!val) return '';
  return val.charAt(0).toUpperCase() + val.slice(1).toLowerCase();
}

function formatProviderValue(val) {
  if (!val) return '';
  const map = {
    'OPENAI': 'OpenAI',
    'ANTHROPIC': 'Anthropic',
    'GOOGLE': 'Google',
    'COHERE': 'Cohere',
    'MISTRAL': 'Mistral',
    'LLAMA': 'Llama',
    'GPT4': 'GPT-4',
    'GPT3': 'GPT-3',
    // Add more as needed
  };
  return map[val.toUpperCase()] || val.charAt(0).toUpperCase() + val.slice(1).toLowerCase();
}
</script>

<template>
  <div class="test-target-box">
    <h3 class="atlas-title">Test Target</h3>
    <div v-if="error">
      <em>Failed to load configuration. Please refresh the page or try again later.</em>
    </div>
    <div v-else-if="filteredEntries.length">
      <!-- System Prompt Section -->
      <div class="config-field system-prompt-field">
        <div class="field-label-with-info">
          <strong>System Prompt</strong>
          <div class="tooltip-container">
            <span class="info-icon">ⓘ</span>
            <div class="tooltip-text">The system prompt used to guide the AI's behavior</div>
          </div>
        </div>
        <div class="field-value">
          <div class="prompt-text">
            {{ truncatedSystemPrompt }} 
            <a href="#" @click.prevent="showSystemPromptModal = true" class="view-full-prompt-link">View Full Prompt</a>
          </div>
        </div>
      </div>
      
      <!-- Other Configuration Fields -->
      <div v-for="[key, value] in filteredEntries" :key="key" class="config-field">
        <div class="field-label-with-info">
          <strong>{{ formatFieldName(key) }}</strong>
          <div class="tooltip-container">
            <span class="info-icon">ⓘ</span>
            <div class="tooltip-text">{{ configDescriptions[key] || 'No description available' }}</div>
          </div>
        </div>
        <div class="field-value">
          <template v-if="key === 'llm_provider'">{{ formatProviderValue(value) }}</template>
          <template v-else-if="key === 'algorithm'">{{ value.toUpperCase() }}</template>
          <template v-else-if="key === 'search_type'">{{ capitalizeFirst(value) }}</template>
          <template v-else>{{ value }}</template>
        </div>
      </div>
    </div>
    <div v-else>
      <em>Loading config...</em>
    </div>
  </div>
  
  <!-- System Prompt Modal -->
  <div class="system-prompt-modal" :class="{ 'is-active': showSystemPromptModal }">
    <div class="modal-background" @click="showSystemPromptModal = false"></div>
    <div class="modal-card">
      <header class="modal-card-head">
        <p class="modal-card-title">System Prompt</p>
      </header>
      <section class="modal-card-body">
        <div class="system-prompt-content">
          <div v-if="systemPrompt" class="system-prompt-full">{{ systemPrompt }}</div>
          <p v-else class="no-prompt-message">System prompt could not be loaded.</p>
        </div>
      </section>
      <footer class="modal-card-foot">
        <button class="button" @click="showSystemPromptModal = false">Close</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.test-target-box { padding: 1em; border: 1px solid #ddd; border-radius: 8px; background: #fff; }
.config-field {
  margin-bottom: 0.5em;
  padding-bottom: 0.2em;
}
.field-label-with-info {
  display: flex;
  align-items: center;
  gap: 0;
}
.tooltip-container {
  display: inline-block;
  margin-left: 0;
  position: relative;
  vertical-align: middle;
}
.config-field strong {
  color: #111;
  font-weight: 600;
  font-size: 0.97em;
  margin-right: 0;
  line-height: 1.3;
}
.atlas-title {
  margin-bottom: 1em;
  font-size: 1.5em;
  color: #181818;
  font-weight: 800;
  letter-spacing: -0.5px;
}
.tooltip-container {
  display: inline-block;
  margin-left: 4px;
  position: relative;
  vertical-align: middle;
}
.info-icon { cursor: pointer; }
.tooltip-text {
  display: none;
  position: absolute;
  left: 20px;
  top: -5px;
  background: #333;
  color: #fff;
  padding: 0.5em;
  border-radius: 4px;
  white-space: pre-line;
  z-index: 10;
  width: 250px;
}
.tooltip-container:hover .tooltip-text { display: block; }
.field-value {
  margin-top: 0;
  color: #3a3a3a;
  font-size: 0.97em;
  line-height: 1.4;
  word-break: break-word;
  flex: 1;
}
/* System Prompt Styles */
.system-prompt-field {
  margin-bottom: 0.5em;
  padding-bottom: 0.5em;
  border-bottom: 1px solid #eee;
}



.prompt-text {
  color: #3a3a3a;
  font-size: 0.97em;
  line-height: 1.4;
}

.view-full-prompt-link {
  text-decoration: underline;
  color: #000;
  cursor: pointer;
  font-size: 0.85em;
  display: inline;
  margin-left: 0.3em;
}

.view-full-prompt-link:hover,
.view-full-prompt-link:focus {
  color: #888;
  text-decoration: underline;
}



/* Modal Styles */
.system-prompt-modal {
  display: none;
}

.system-prompt-modal.is-active {
  display: flex;
  align-items: center;
  justify-content: center;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
}

.system-prompt-modal .modal-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.9);
}

.system-prompt-modal .modal-card {
  position: relative;
  width: 80%;
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background-color: white;
  border-radius: 6px;
  box-shadow: 0 2px 15px rgba(0, 0, 0, 0.1);
}

.system-prompt-modal .modal-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  border-bottom: 1px solid #dbdbdb;
  background-color: white;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
}

.system-prompt-modal .modal-card-title {
  color: black;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.system-prompt-modal .delete {
  background-color: rgba(0, 0, 0, 0.1);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  height: 20px;
  width: 20px;
  position: relative;
}

.system-prompt-modal .delete::before,
.system-prompt-modal .delete::after {
  background-color: #333;
  content: "";
  display: block;
  height: 2px;
  width: 50%;
  position: absolute;
  top: 50%;
  left: 25%;
}

.system-prompt-modal .delete::before {
  transform: rotate(45deg);
}

.system-prompt-modal .delete::after {
  transform: rotate(-45deg);
}

.system-prompt-modal .modal-card-body {
  flex-grow: 1;
  overflow-y: auto;
  padding: 1.25rem;
  background-color: white;
}

.system-prompt-modal .system-prompt-content {
  color: black;
}

.system-prompt-modal .system-prompt-full {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  line-height: 1.5;
  color: #3a3a3a;
  font-size: 0.97em;
}

.system-prompt-modal .modal-card-foot {
  display: flex;
  justify-content: flex-end;
  padding: 1.25rem;
  background-color: white;
  border-top: 1px solid #dbdbdb;
  border-bottom-left-radius: 6px;
  border-bottom-right-radius: 6px;
}

.system-prompt-modal .button {
  background-color: #f5f5f5;
  border: 1px solid #dbdbdb;
  border-radius: 4px;
  color: #363636;
  cursor: pointer;
  padding: 0.5em 1em;
  font-size: 1rem;
}

.system-prompt-modal .button:hover {
  background-color: #e8e8e8;
}
</style>