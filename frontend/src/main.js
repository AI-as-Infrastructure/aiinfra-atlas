import 'bulma/css/bulma.css'
import './global.css'
// Changed from side-effect import to namespace import
import * as Polyfills from './polyfills' // Must be imported before Amplify
// Rest of imports
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { configureAmplify } from './auth/amplify-auth'
import { setupTelemetryInterceptors } from './utils/telemetryInterceptor'

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

// Initialize Amplify with Cognito configuration
configureAmplify()

// Create and configure the Vue app
const app = createApp(App)
const pinia = createPinia()

// Register the persistedstate plugin for Pinia
pinia.use(piniaPluginPersistedstate)

app.use(pinia)
app.use(router)

// Configure Vue app based on debug mode
if (isDebugMode) {
  app.config.performance = true // Enable performance tracking
  app.config.devtools = true // Ensure devtools are enabled
}

// Mount the app
app.mount('#app')

// Initialize telemetry after Pinia is registered and app is mounted
import { nextTick } from 'vue'
import { useTelemetryStore } from '@/stores/telemetry'

nextTick(() => {
  // Initialize telemetry interceptors
  setupTelemetryInterceptors()
  
  // Ensure telemetry store is initialized
  const telemetryStore = useTelemetryStore()
  if (!telemetryStore.traceId) {
    telemetryStore.regenerateTraceId()
  }
})