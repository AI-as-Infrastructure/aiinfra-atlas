import 'bulma/css/bulma.css'
import './global.css'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'

// Debug mode setup based on environment variables
const isDebugMode = import.meta.env.VITE_DEBUG_MODE === 'true'

// Configure debug logging based on mode
if (isDebugMode) {
  console.info('🔍 Debug mode is enabled')
} else {
  // In production, suppress some console outputs
  const originalConsoleLog = console.log
  console.log = (...args) => {
    // Only suppress logs that start with specific prefixes
    const firstArg = args[0]
    const suppressPrefixes = ['[AskAPI]', '[StreamParser]']
    if (typeof firstArg === 'string' && suppressPrefixes.some(prefix => firstArg.startsWith(prefix))) {
      return // Suppress detailed logs in production
    }
    originalConsoleLog(...args)
  }
}

// Create and configure the Vue app
const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Configure Vue app based on debug mode
if (isDebugMode) {
  app.config.performance = true // Enable performance tracking
  app.config.devtools = true // Ensure devtools are enabled
}

// Mount the app
app.mount('#app')

// Initialize WebSocket only after Pinia is registered and app is mounted
import { nextTick } from 'vue'
import { useSocketStore } from '@/stores/socket'
nextTick(() => {
  const socketStore = useSocketStore()
  socketStore.initializeSocket()
})