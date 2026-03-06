/**
 * Telemetry Interceptor for ATLAS
 *
 * Wraps window.fetch to automatically attach telemetry headers
 * (X-Telemetry-Opt-In, X-Trace-Id, etc.) and track timing data.
 */

import { useTelemetryStore } from '../stores/telemetry';

/**
 * Setup telemetry interceptor for fetch API
 */
export function setupFetchInterceptor() {
  // Store original fetch function
  const originalFetch = window.fetch;

  // Replace with intercepted version
  window.fetch = async (resource, options = {}) => {
    const telemetryStore = useTelemetryStore();

    // Track timing for /api/ask requests
    const isAskRequest = resource.includes('/api/ask');
    if (isAskRequest) {
      telemetryStore.startResponse();
    }

    // Add telemetry headers to options
    const updatedOptions = {
      ...options,
      headers: {
        ...options.headers,
        ...telemetryStore.telemetryHeaders
      }
    };

    try {
      const response = await originalFetch(resource, updatedOptions);

      // Track response timing for /api/ask
      if (isAskRequest) {
        telemetryStore.endResponse({
          status: response.status,
          url: resource
        });
      }

      return response;
    } catch (error) {
      // Handle fetch errors
      if (isAskRequest) {
        telemetryStore.endResponse({
          error: error.message
        });
      }
      throw error;
    }
  };
}

/**
 * Setup telemetry interceptors.
 * Call once at app startup after Pinia is registered.
 */
export function setupTelemetryInterceptors() {
  setupFetchInterceptor();
}
