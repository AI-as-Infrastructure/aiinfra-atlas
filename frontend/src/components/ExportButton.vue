<template>
  <button class="button is-link is-light" @click="exportSession">Export Session</button>
</template>
<script setup>
import { useSessionStore } from '@/stores/session'
const session = useSessionStore()
async function exportSession() {
  // Fetch unified config from backend
  let config = null
  try {
    const res = await fetch('/api/config')
    if (res.ok) {
      config = await res.json()
    }
  } catch (e) {
    console.error('Failed to fetch config for export:', e)
  }
  const exportData = {
    chatHistory: session.chatHistory,
    config: config
  }
  const data = JSON.stringify(exportData, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'atlas-session.json'
  a.click()
  URL.revokeObjectURL(url)
}
</script> 