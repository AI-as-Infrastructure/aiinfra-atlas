<template>
  <div class="app">
    <header>
      <nav class="navbar is-light" role="navigation" aria-label="main navigation">
        <div class="container">
          <div class="navbar-brand"> 
            <router-link to="/" class="navbar-item has-text-weight-bold site-title-link">{{ siteTitle }}</router-link>
          </div>
          <div class="navbar-menu" v-if="!isLoginPage">
            <div class="navbar-link-group">
              <!-- Empty left section for spacing -->
              <div class="nav-section left-section"></div>
              
              <!-- Center section with all navigation items grouped together -->
              <div class="nav-section center-section">
                <div class="nav-item">
                  <NewSessionButton />
                </div>
                <div class="nav-item">
                  <router-link class="nav-link" to="/about">About</router-link>
                </div>
                <div class="nav-item">
                  <router-link class="nav-link" to="/faq">FAQ</router-link>
                </div>
              </div>
              
              <!-- Right section for auth controls -->
              <div class="nav-section right-section">
                <AuthControls class="auth-controls" />
              </div>
            </div>
          </div>
        </div>
      </nav>
    </header>
    <main>
      <div class="container">
        <router-view />
      </div>
    </main>
    <footer>
     ATLAS: Analysis and Testing of Language Models for Archival Systems. An output of the <a href="https://aiinfra.anu.edu.au" target="_blank" rel="noreferrer"> AI as Infrastructure (AIINFRA)</a> project. 2024 - 2026.
    </footer>
  </div>
</template>

<script setup>
import NewSessionButton from './components/NewSessionButton.vue'
import AuthControls from './components/AuthControls.vue'
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const siteTitle = ref(import.meta.env.VITE_SITE_TITLE || 'ATLAS')
const atlasVersion = ref(import.meta.env.VITE_ATLAS_VERSION || '0.1.0')
const lastModified = ref(import.meta.env.VITE_LAST_MODIFIED || 'May 2025')

// Determine if we're on the home page
const isHomePage = computed(() => {
  return route.path === '/' || route.path === '/index.html'
})

// Determine if we're on the login page
const isLoginPage = computed(() => {
  return route.path === '/login'
})

// Retrieve auth store for use in auth-related functionality
const authStore = useAuthStore()

// Initialize auth state when app is mounted
onMounted(() => {
  // Only run this if we're not on the callback page to avoid doubled initialization
  if (route.path !== '/callback') {
    authStore.initialize()
  }
})
</script>

<style>
.site-title-link {
  color: #181818;
  text-decoration: none;
  font-weight: 800;
  font-size: 1.35em;
  cursor: pointer;
  letter-spacing: -0.5px;
  padding: 0;
  margin: 0;
  background: none;
  border: none;
  outline: none;
}
.site-title-link:hover, .site-title-link:focus {
  text-decoration: underline;
  color: #111;
}

.invisible-link {
  color: inherit;
  text-decoration: none;
  background: none;
  border: none;
  cursor: pointer;
  outline: none;
  /* Make the link invisible visually, but accessible to screen readers */
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  pointer-events: auto;
  z-index: 10;
}

/* Only include component-specific styles if needed; global styles now handle layout and typography. */
.navbar {
  padding: 0.5rem 0;
  box-shadow: 0 2px 3px rgba(10, 10, 10, 0.1);
}

.navbar-brand {
  display: flex;
  align-items: center;
}

.navbar-link-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  flex: 1;
}

.nav-section {
  display: flex;
  align-items: center;
}

.left-section {
  justify-content: flex-start;
  flex: 1;
  min-width: 50px; /* Ensure minimum spacing from the site title */
}

.center-section {
  justify-content: center;
  flex: 2;
  display: flex;
  gap: 0; /* Remove gap as we'll control spacing with margins */
  margin: 0 auto; /* Center the navigation group */
  max-width: 500px; /* Limit width to keep items closer together */
}

.nav-item {
  display: flex;
  align-items: center;
  justify-content: center;
}

.center-section .nav-item {
  margin: 0 1.25rem; /* Add consistent horizontal margins to each item */
  padding: 0;
}

.center-section .nav-link {
  padding: 0.5rem 0.75rem;
  display: block;
}

.right-section {
  justify-content: flex-end;
  flex: 1;
  min-width: 50px; /* Ensure minimum spacing to the right edge */
}

/* Ensure the auth controls have consistent spacing */
.auth-controls {
  margin-left: 1rem;
}



.navbar-item {
  font-weight: 400 !important;
  text-decoration: none !important;
}

.new-session-link {
  color: #000;
  text-decoration: none;
  cursor: pointer;
  font-weight: 500;
  font-size: 1rem;
  padding: 0.25rem 1.3rem;
  transition: color 0.2s, text-decoration 0.2s;
  background: none;
  border: none;
  outline: none;
}
.new-session-link:hover, .new-session-link:focus {
  color: #888;
  text-decoration: none;
}

/* Navigation link styling */
.nav-link {
  color: #000;
  text-decoration: underline;
  cursor: pointer;
  font-weight: 500;
  font-size: 1rem;
  padding: 0.25rem 1.3rem;
  transition: color 0.2s;
  background: none;
  border: none;
  outline: none;
}

.nav-link:hover, .nav-link:focus {
  color: #888;
  text-decoration: underline;
}

/* You may add any App.vue-specific tweaks here if required. */

</style>