<template>
  <button
    class="button is-link is-light"
    @click="exportConfiguration"
    :disabled="loading"
    title="Export corpus and test target configuration"
    aria-label="Export ATLAS configuration as JSON"
  >
    Export Config
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
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>