<template>
  <!-- ... -->
  <button @click="handleLogout">Logout</button>
  <!-- ... -->
</template>

<script>
import { logout } from '@/auth/authService';

export default {
  methods: {
    handleLogout() {
      console.log('Logout button clicked');
      logout();
    }
  }
};
</script> 