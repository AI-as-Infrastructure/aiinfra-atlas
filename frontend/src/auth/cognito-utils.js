/**
 * Utility functions for AWS Cognito authentication
 * Extracted from cognito.js to allow reuse in other components
 */

/**
 * Generate a random string for PKCE challenge
 * @param {number} length - Length of the random string
 * @returns {string} Random string
 */
export const generateRandomString = (length) => {
  const array = new Uint8Array(length);
  window.crypto.getRandomValues(array);
  return Array.from(array, byte => ('0' + (byte & 0xFF).toString(16)).slice(-2)).join('');
};

/**
 * Create a SHA-256 hash of the code verifier
 * @param {string} codeVerifier - Code verifier to hash
 * @returns {Promise<string>} Base64 URL encoded hash
 */
export const generateCodeChallenge = async (codeVerifier) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(codeVerifier);
  const digest = await window.crypto.subtle.digest('SHA-256', data);
  
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
};

// Key for persistent storage of code verifier
const CODE_VERIFIER_KEY = 'atlas_pkce_code_verifier';
const CODE_STATE_KEY = 'atlas_pkce_state';

/**
 * Handle code verifier storage for PKCE
 * @returns {string} The generated code verifier
 */
export const storeCodeVerifier = () => {
  // Generate new code verifier
  const codeVerifier = generateRandomString(64);
  
  // Generate a unique state to associate with this login flow
  const state = generateRandomString(16);
  
  // Store in localStorage for better persistence across redirects
  localStorage.setItem(CODE_VERIFIER_KEY, codeVerifier);
  localStorage.setItem(CODE_STATE_KEY, state);
  
  console.log('Stored new code verifier with state:', state);
  return { codeVerifier, state };
};

/**
 * Get the stored code verifier for PKCE
 * @returns {string|null} The stored code verifier or null if not found
 */
export const getCodeVerifier = () => {
  return localStorage.getItem(CODE_VERIFIER_KEY);
};

/**
 * Get the stored state for PKCE
 * @returns {string|null} The stored state or null if not found
 */
export const getCodeState = () => {
  return localStorage.getItem(CODE_STATE_KEY);
};

/**
 * Clear the stored code verifier
 */
export const clearCodeVerifier = () => {
  localStorage.removeItem(CODE_VERIFIER_KEY);
  localStorage.removeItem(CODE_STATE_KEY);
  console.log('Cleared PKCE code verifier and state');
};
