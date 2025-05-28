/**
 * Telemetry Interceptor for ATLAS
 * 
 * This module provides interceptors for API requests to automatically
 * attach telemetry headers and track timing data.
 */

import { useTelemetryStore } from '../stores/telemetry';

/**
 * Setup telemetry interceptors for fetch API
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
 * Setup telemetry interceptors for Axios
 * @param {import('axios').AxiosInstance} axios - Axios instance
 */
export function setupAxiosInterceptor(axios) {
  // Request interceptor
  axios.interceptors.request.use(config => {
    const telemetryStore = useTelemetryStore();
    
    // Add telemetry headers
    config.headers = {
      ...config.headers,
      ...telemetryStore.telemetryHeaders
    };
    
    // Track timing for /api/ask requests
    if (config.url?.includes('/api/ask')) {
      telemetryStore.startResponse();
    }
    
    return config;
  });
  
  // Response interceptor
  axios.interceptors.response.use(
    response => {
      const telemetryStore = useTelemetryStore();
      
      // Track timing for /api/ask responses
      if (response.config.url?.includes('/api/ask')) {
        telemetryStore.endResponse({
          status: response.status,
          data_size: JSON.stringify(response.data).length,
          url: response.config.url
        });
      }
      
      return response;
    },
    error => {
      const telemetryStore = useTelemetryStore();
      
      // Track timing for errors
      if (error.config?.url?.includes('/api/ask')) {
        telemetryStore.endResponse({
          error: error.message,
          status: error.response?.status
        });
      }
      
      return Promise.reject(error);
    }
  );
}

/**
 * Setup all available telemetry interceptors
 * @param {import('axios').AxiosInstance} [axios] - Optional Axios instance
 */
export function setupTelemetryInterceptors(axios) {
  // Always setup fetch interceptor
  setupFetchInterceptor();
  
  // Setup axios interceptor if provided
  if (axios) {
    setupAxiosInterceptor(axios);
  }
}
