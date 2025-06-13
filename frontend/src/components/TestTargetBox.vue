<script setup>
import { ref, onMounted, computed } from 'vue'
import VectorStoreInfo from './VectorStoreInfo.vue'

const config = ref(null)
const error = ref(false)
const showSystemPromptModal = ref(false)
const systemPrompt = ref('')
const truncatedSystemPrompt = ref('')

const configDescriptions = {
  ATLAS_VERSION: "The version of the ATLAS application.",
  composite_target: "The combined identifier for the target configuration.",
  embedding_model: "The model used to create vector embeddings.",
  LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS: "The number of documents initially retrieved from the HNSW vector index when searching a single corpus (HNSW -K).",
  LARGE_RETRIEVAL_SIZE_ALL_CORPUS: "The number of documents initially retrieved from the HNSW vector index when searching across all corpora. This value is multiplied by the number of corpora to determine the total retrieval size.",
  algorithm: "The algorithm used for vector similarity search.",
  search_type: "The retrieval algorithm used for searching the vector store.",
  search_k: "The number of top documents passed to the LLM for answer generation.",
  search_score_threshold: "The minimum similarity score required for document retrieval.",
  chunk_size: "The size of each text chunk stored in the vector index.",
  chunk_overlap: "The overlap between text chunks for better context.",
  pooling: "The pooling strategy used to aggregate token embeddings (cls, mean, mean+max).",
  llm_provider: "The provider of the language model.",
  llm_model: "The language model used to generate answers.",
  MULTI_CORPUS_VECTORSTORE: "If true, enables the corpus selector dropdown and multi-corpus vectorstore features.",
  SYSTEM_PROMPT: "The system prompt used to guide the AI's behavior and define its capabilities."
};

// List of fields to exclude from display
const unwantedFields = [
  'CORPUS_OPTIONS', 'FULL_SYSTEM_PROMPT', 'SYSTEM_PROMPT',
  'target_id', 'target_version', 'citation_limit', 'index_name', 'redis_database',
  'CHROMA_COLLECTION_NAME', 'large_retrieval_size'
];

function formatFieldName(key) {
  // Special cases
  const exceptions = {
    llm_provider: 'LLM Provider',
    llm_model: 'LLM Model',
    CHROMA_COLLECTION_NAME: 'Chroma Collection Name',
    MULTI_CORPUS_VECTORSTORE: 'Multi Corpus Vectorstore',
    composite_target: 'Composite Target',
    ATLAS_VERSION: 'Atlas Version',
    LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS: 'Retrieval Size Single Corpus',
    LARGE_RETRIEVAL_SIZE_ALL_CORPUS: 'Retrieval Size All Corpora'
  };
  if (exceptions[key]) return exceptions[key];
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// Define the order and grouping of fields
const fieldGroups = {
  primary: [
    'ATLAS_VERSION',
    'composite_target',
    'llm_provider',
    'llm_model',
    'SYSTEM_PROMPT'
  ],
  vectorStore: [
    'embedding_model',
    'algorithm',
    'search_type',
    'LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS',
    'LARGE_RETRIEVAL_SIZE_ALL_CORPUS',
    'search_k',
    'search_score_threshold',
    'chunk_size',
    'chunk_overlap',
    'pooling'
  ],
  other: [] // Will contain any remaining fields
}

// Initialize filteredEntries with empty arrays
const filteredEntries = ref({
  primary: [],
  vectorStore: [],
  other: []
})

async function fetchConfig() {
  try {
    const res = await fetch('/api/config')
    if (!res.ok) throw new Error('Failed to fetch /api/config')
    const data = await res.json()
    config.value = data
    
    // Debug log to see what we're getting
    console.log('Config data:', data)
    
    // Extract system prompt data
    if (data.FULL_SYSTEM_PROMPT) {
      systemPrompt.value = data.FULL_SYSTEM_PROMPT
      truncatedSystemPrompt.value = data.SYSTEM_PROMPT || 
        (systemPrompt.value.length > 150 ? 
          systemPrompt.value.substring(0, 150) + '...' : 
          systemPrompt.value)
    }
    
    // Filter and organize entries
    const allEntries = Object.entries(data).filter(([k]) => !unwantedFields.includes(k))
    
    // Debug log to see filtered entries
    console.log('Filtered entries:', allEntries)
    
    // Group entries according to fieldGroups
    const groupedEntries = {
      primary: [],
      vectorStore: [],
      other: []
    }
    
    // Add system prompt to primary entries if we have it
    if (data.FULL_SYSTEM_PROMPT) {
      groupedEntries.primary.push(['SYSTEM_PROMPT', truncatedSystemPrompt.value])
    }
    
    allEntries.forEach(([key, value]) => {
      if (fieldGroups.primary.includes(key)) {
        groupedEntries.primary.push([key, value])
      } else if (fieldGroups.vectorStore.includes(key)) {
        groupedEntries.vectorStore.push([key, value])
      } else {
        groupedEntries.other.push([key, value])
      }
    })
    
    // Sort each group according to the order in fieldGroups
    groupedEntries.primary.sort((a, b) => 
      fieldGroups.primary.indexOf(a[0]) - fieldGroups.primary.indexOf(b[0]))
    groupedEntries.vectorStore.sort((a, b) => 
      fieldGroups.vectorStore.indexOf(a[0]) - fieldGroups.vectorStore.indexOf(b[0]))
    
    // Debug log to see final grouped entries
    console.log('Grouped entries:', groupedEntries)
    
    filteredEntries.value = groupedEntries
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
    <div v-else>
      <!-- Primary Information -->
      <div v-if="filteredEntries.primary.length" class="config-section">
        <div v-for="[key, value] in filteredEntries.primary" :key="key" class="config-field">
          <template v-if="key === 'SYSTEM_PROMPT'">
            <div class="field-label-with-info">
              <strong>System Prompt</strong>
              <div class="tooltip-container">
                <span class="info-icon">ⓘ</span>
                <div class="tooltip-text">{{ configDescriptions[key] }}</div>
              </div>
            </div>
            <div class="field-value">
              <div class="prompt-text">
                {{ truncatedSystemPrompt }} 
                <a href="#" @click.prevent="showSystemPromptModal = true" class="view-full-prompt-link">View Full Prompt</a>
              </div>
            </div>
          </template>
          <template v-else>
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
          </template>
        </div>
      </div>

      <!-- Vector Store Overview -->
      <div class="config-section">
        <div class="config-field">
          <div class="field-label-with-info">
            <strong>Vector Store Overview</strong>
            <div class="tooltip-container">
              <span class="info-icon">ⓘ</span>
              <div class="tooltip-text">Details about the vector store composition, including corpus distribution, processing times, and overall statistics. This information helps understand the scope and characteristics of the searchable content.</div>
            </div>
          </div>
          <div class="field-value">
            <VectorStoreInfo />
          </div>
        </div>
      </div>

      <!-- Vector Store Configuration -->
      <div v-if="filteredEntries.vectorStore.length" class="config-section">
        <div v-for="[key, value] in filteredEntries.vectorStore" :key="key" class="config-field">
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

      <!-- Other Configuration -->
      <div v-if="filteredEntries.other.length" class="config-section">
        <div v-for="[key, value] in filteredEntries.other" :key="key" class="config-field">
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

      <div v-if="!filteredEntries.primary.length && !filteredEntries.vectorStore.length && !filteredEntries.other.length">
        <em>Loading config...</em>
      </div>
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
.test-target-box { 
  padding: 1em; 
  border: 1px solid #ddd; 
  border-radius: 8px; 
  background: #fff; 
}

.config-section {
  margin: 0;
  padding: 0.5em 0;
  border-bottom: 1px solid #eee;
}

.config-section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.config-field {
  margin: 0;
  padding: 0.5em 0;
  border-bottom: 1px solid #eee;
}

.config-field:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.field-label-with-info {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 0.25em;
}

.tooltip-container {
  display: inline-block;
  margin-left: 4px;
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
  margin: 0 0 0.5em 0;
  font-size: 1.5em;
  color: #181818;
  font-weight: 800;
  letter-spacing: -0.5px;
}

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

.tooltip-container:hover .tooltip-text {
  display: block;
}

.field-value {
  margin: 0;
  color: #3a3a3a;
  font-size: 0.97em;
  line-height: 1.4;
  word-break: break-word;
  flex: 1;
}

/* System Prompt Styles */
.system-prompt-field {
  margin: 0;
  padding: 0.5em 0;
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
}

/* Modal Styles */
.system-prompt-modal,
.vector-store-modal {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
}

.system-prompt-modal.is-active,
.vector-store-modal.is-active {
  display: block;
}

.modal-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
}

.modal-card {
  position: relative;
  max-width: 800px;
  width: 90%;
  margin: 2rem auto;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 3px rgba(10, 10, 10, 0.1);
  max-height: calc(100vh - 4rem);
  display: flex;
  flex-direction: column;
}

.modal-card-head {
  padding: 1rem;
  border-bottom: 1px solid #dbdbdb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-card-body {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
}

.modal-card-foot {
  padding: 1rem;
  border-top: 1px solid #dbdbdb;
  display: flex;
  justify-content: flex-end;
}

.system-prompt-content,
.vector-store-content {
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 0.9em;
  line-height: 1.5;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 4px;
  max-height: 60vh;
  overflow-y: auto;
}
</style>