import { useTelemetryStore } from '@/stores/telemetry'

// Track if we've already set up the unload handler
let unloadHandlerSet = false

/**
 * Initialize session handling for telemetry
 * This sets up event listeners for page unload to sync pending QA turns
 * Must be called after Pinia is initialized
 */
export function initializeSessionHandlers() {
  // Only set up the handler once
  if (unloadHandlerSet || typeof window === 'undefined') return
  
  try {
    const telemetryStore = useTelemetryStore()
    
    // Function to handle page unload
    const handleBeforeUnload = async (event) => {
      // Skip if no pending QA turns
      if (!telemetryStore.getPendingQaTurns || telemetryStore.getPendingQaTurns.length === 0) return
      
      // Show a message to the user (most browsers won't show this, but it's good practice)
      event.preventDefault()
      event.returnValue = 'You have unsynchronized feedback. Please wait while we sync your data.'
      
      try {
        // Sync all pending QA turns
        console.log('Syncing pending QA turns before page unload...')
        await telemetryStore.syncAllPendingQaTurns()
        console.log('Successfully synced all pending QA turns before page unload')
      } catch (error) {
        console.error('Error syncing QA turns before unload:', error)
      }
      
      // Some browsers require returnValue to be set
      return event.returnValue
    }
  
    // Add event listeners for page unload
    window.addEventListener('beforeunload', handleBeforeUnload)
    
    // Also handle pagehide for better mobile support
    window.addEventListener('pagehide', handleBeforeUnload)
    
    // Cleanup function
    const cleanup = () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      window.removeEventListener('pagehide', handleBeforeUnload)
    }
    
    // Mark handler as set
    unloadHandlerSet = true
    
    // Return cleanup function
    return cleanup
  } catch (error) {
    console.error('Error initializing session handlers:', error)
  }
}

// Initialize session handlers when the module is loaded
if (typeof window !== 'undefined') {
  initializeSessionHandlers()
}
