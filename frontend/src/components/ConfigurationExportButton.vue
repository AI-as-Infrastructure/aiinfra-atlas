<template>
  <button class="button is-link is-light config-export-btn" @click="exportConfiguration" title="Export corpus and test target configuration">
    <span class="icon">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <!-- Gear icon -->
        <path d="M8 4.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zM5.5 8a2.5 2.5 0 1 1 5 0 2.5 2.5 0 0 1-5 0z"/>
        <path d="M6.5 0L5.7 1.4c-.3.1-.6.2-.9.3L3.1.5 1 2.6l1.2 1.7c-.1.3-.2.6-.3.9L0 6v4l1.4.8c.1.3.2.6.3.9L.5 12.9 2.6 15l1.7-1.2c.3.1.6.2.9.3L6 16h4l.8-1.4c.3-.1.6-.2.9-.3l1.7 1.2 2.1-2.1-1.2-1.7c.1-.3.2-.6.3-.9L16 10V6l-1.4-.8c-.1-.3-.2-.6-.3-.9l1.2-1.7L13.4 1l-1.7 1.2c-.3-.1-.6-.2-.9-.3L10 0H6.5z"/>
        <!-- Download arrow overlay -->
        <path d="M8 6v3m0 0l-1.5-1.5M8 9l1.5-1.5" stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </span>
    <span>Export Config</span>
  </button>
</template>

<script setup>
import { ref } from 'vue'

const loading = ref(false)

async function exportConfiguration() {
  if (loading.value) return

  loading.value = true

  try {
    // Prompt for configuration name and description
    const configName = prompt('Enter a name for this configuration:', `ATLAS Config - ${new Date().toISOString().split('T')[0]}`)
    if (!configName) {
      loading.value = false
      return
    }

    const description = prompt('Enter an optional description:', '')

    // Fetch configuration from backend
    const params = new URLSearchParams()
    if (configName) params.append('config_name', configName)
    if (description) params.append('description', description)

    const response = await fetch(`/api/configuration/export?${params}`)

    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`)
    }

    // Get the JSON data
    const configData = await response.json()

    // Create download
    const data = JSON.stringify(configData, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url

    // Use timestamp in filename
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
    a.download = `atlas-config-${timestamp}.json`

    a.click()
    URL.revokeObjectURL(url)

    console.log('Configuration exported successfully')

  } catch (error) {
    console.error('Failed to export configuration:', error)
    alert(`Failed to export configuration: ${error.message}`)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.config-export-btn {
  min-width: 140px;
}

.config-export-btn .icon {
  margin-right: 0.5rem;
}

.config-export-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>