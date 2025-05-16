<template>
  <div>
    <button v-if="!isAuthenticated()" @click="signIn">Sign In</button>
    <button v-if="isAuthenticated()" @click="signOut">Sign Out</button>
    <div v-if="isAuthenticated()">Hello, {{ user?.username }}</div>
  </div>
</template>

<script setup>
import { useAuth } from '../composables/useAuth'
const { user, signIn, signOut, isAuthenticated } = useAuth()
</script> 