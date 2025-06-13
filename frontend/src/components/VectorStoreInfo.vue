<template>
  <div class="vector-store-info">
    <div class="field-value">
      <div class="vector-store-text">
        <template v-if="content">
          {{ truncatedContent }}
          <a href="#" @click.prevent="showModal = true" class="view-full-link">View Overview</a>
        </template>
        <template v-else-if="error">
          <span class="error-text">Failed to load vector store information</span>
        </template>
        <template v-else>
          <span class="loading-text">Loading vector store information...</span>
        </template>
      </div>
    </div>
  </div>
  
  <!-- Vector Store Modal -->
  <div class="vector-store-modal" :class="{ 'is-active': showModal }">
    <div class="modal-background" @click="showModal = false"></div>
    <div class="modal-card">
      <header class="modal-card-head">
        <p class="modal-card-title">Vector Store Overview</p>
      </header>
      <section class="modal-card-body">
        <div class="vector-store-content">
          <pre v-if="content">{{ content }}</pre>
          <p v-else-if="error" class="error-text">Failed to load vector store information.</p>
          <p v-else class="loading-text">Loading vector store information...</p>
        </div>
      </section>
      <footer class="modal-card-foot">
        <button class="button" @click="showModal = false">Close</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'

const showModal = ref(false)
const content = ref(null)
const error = ref(false)

const truncatedContent = computed(() => {
  if (!content.value) return ''
  return ''  // Return empty string to show only the link
})

onMounted(async () => {
  try {
    const response = await fetch('/api/vector-store-info')
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to fetch vector store info')
    }
    const data = await response.json()
    content.value = data.content
  } catch (e) {
    console.error('Error loading vector store information:', e)
    error.value = true
  }
})
</script>

<style scoped>
.vector-store-info {
  margin-bottom: 0.5em;
  padding-bottom: 0.2em;
}

.field-value {
  margin-top: 0;
  color: #3a3a3a;
  font-size: 0.97em;
  line-height: 1.4;
  word-break: break-word;
  flex: 1;
}

.vector-store-text {
  color: #3a3a3a;
  font-size: 0.97em;
  line-height: 1.4;
  font-family: inherit;
  padding-left: 0;
}

.loading-text,
.error-text {
  font-family: inherit;
  font-style: italic;
}

.error-text {
  color: #dc3545;
}

.view-full-link {
  text-decoration: underline;
  color: #000;
  cursor: pointer;
  margin-left: 0;
  font-family: inherit;
  display: block;
  text-align: left;
}

.vector-store-modal {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
}

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

.vector-store-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: monospace;
}

.vector-store-content .loading-text,
.vector-store-content .error-text {
  font-family: inherit;
  margin: 0;
}
</style> 