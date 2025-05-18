<template>
  <div class="logout-debug">
    <h3>Logout Debug Information</h3>
    <p>VITE_COGNITO_LOGOUT_ENDPOINT: {{ logoutEndpoint }}</p>
    <p>VITE_COGNITO_CLIENT_ID: {{ clientId }}</p>
    <p>VITE_COGNITO_LOGOUT_REDIRECT_URI: {{ logoutUri }}</p>
    <button @click="testLogout" class="button is-danger">Force Logout</button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      logoutEndpoint: import.meta.env.VITE_COGNITO_LOGOUT_ENDPOINT || 'Not set',
      clientId: import.meta.env.VITE_COGNITO_CLIENT_ID || 'Not set',
      logoutUri: import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI || 'Not set'
    };
  },
  methods: {
    testLogout() {
      // Direct logout without using the service
      try {
        const logoutUrl = new URL("https://ap-southeast-2fgupzmyvx.auth.ap-southeast-2.amazoncognito.com/logout");
        logoutUrl.searchParams.append('client_id', '6r835dagsj8m5nma1snno6st05');
        logoutUrl.searchParams.append('logout_uri', 'http://localhost:5173/logout.html');
        
        console.log("Force logout redirect to:", logoutUrl.toString());
        window.location.href = logoutUrl.toString();
      } catch (error) {
        console.error("Force logout error:", error);
      }
    }
  }
};
</script>

<style scoped>
.logout-debug {
  margin: 20px;
  padding: 15px;
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
}
</style> 