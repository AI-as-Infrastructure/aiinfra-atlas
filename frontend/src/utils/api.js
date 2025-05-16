/**
 * API client with Cognito authentication integration.
 * Automatically adds the ID token to API requests when Cognito auth is enabled.
 */

import { isCognitoEnabled, getIdToken } from '../auth/amplify-auth';

// Base API URL
const API_BASE_URL = '/api';

/**
 * Make an HTTP request with authentication token if available and enabled
 *
 * @param {string} url - The API endpoint (will be appended to API_BASE_URL)
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<any>} - Response from the API
 */
export async function apiRequest(url, options = {}) {
  const requestUrl = `${API_BASE_URL}${url.startsWith('/') ? url : '/' + url}`;
  
  // Initialize headers
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  // Add auth token if Cognito is enabled
  if (isCognitoEnabled()) {
    try {
      const idToken = await getIdToken();
      if (idToken) {
        headers['Authorization'] = `Bearer ${idToken}`;
      }
    } catch (error) {
      console.error('Error getting ID token for API request:', error);
      // Continue without token - the API will handle unauthenticated requests
    }
  }
  
  // Create the request
  const requestOptions = {
    ...options,
    headers,
  };
  
  try {
    const response = await fetch(requestUrl, requestOptions);
    
    // Handle non-OK responses
    if (!response.ok) {
      const error = await response.json().catch(() => ({ 
        message: response.statusText || 'Unknown error' 
      }));
      
      // Throw standardized error
      throw {
        status: response.status,
        message: error.message || 'API request failed',
        data: error,
      };
    }
    
    // For streaming responses
    if (options.streaming) {
      return response;
    }
    
    // For text responses
    if (options.responseType === 'text') {
      return await response.text();
    }
    
    // Default to JSON
    return await response.json();
  } catch (error) {
    console.error('API request error:', error);
    throw error;
  }
}

/**
 * Convenience method for GET requests
 */
export function get(url, options = {}) {
  return apiRequest(url, { ...options, method: 'GET' });
}

/**
 * Convenience method for POST requests
 */
export function post(url, data, options = {}) {
  return apiRequest(url, {
    ...options,
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Convenience method for PUT requests
 */
export function put(url, data, options = {}) {
  return apiRequest(url, {
    ...options,
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Convenience method for DELETE requests
 */
export function del(url, options = {}) {
  return apiRequest(url, { ...options, method: 'DELETE' });
}
