/**
 * Polyfills for AWS Amplify compatibility with Vite
 */

// Polyfill for global object (required by AWS Amplify)
window.global = window;
window.process = {
  env: { DEBUG: undefined },
};
