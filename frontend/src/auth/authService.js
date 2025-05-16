export const logout = () => {
  const logoutUrl = new URL(import.meta.env.VITE_COGNITO_LOGOUT_ENDPOINT);
  
  // Add the client_id parameter
  logoutUrl.searchParams.append('client_id', import.meta.env.VITE_COGNITO_CLIENT_ID);
  
  // Add the logout URL parameter
  logoutUrl.searchParams.append('logout_uri', import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI);
  
  // Redirect to the Cognito logout endpoint
  window.location.href = logoutUrl.toString();
}; 