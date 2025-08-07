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
              
              <!-- Center section with main navigation items -->
              <div class="nav-section center-section">
                <div class="nav-item">
                  <NewSessionButton />
                </div>
                <div class="nav-item">
                  <router-link class="nav-text-link" to="/faq">FAQ</router-link>
                </div>
                <div class="nav-item">
                  <router-link class="nav-text-link" to="/about">About</router-link>
                </div>
              </div>
              
              <!-- Right section for Inter-rate and logout buttons -->
              <div class="nav-section right-section">
                <div class="nav-item">
                  <InterRaterButton />
                </div>
                <div class="nav-item">
                  <AuthControls class="auth-controls" />
                </div>
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
import InterRaterButton from './components/InterRaterButton.vue'
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
  height: 100%;
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
  vertical-align: top;
  line-height: 1;
}

.center-section .nav-item {
  margin: 0 1.25rem; /* Add consistent horizontal margins to each item */
  padding: 0;
  display: flex;
  align-items: center;
}

/* Removed old nav-link padding - using consistent styling */

.right-section {
  justify-content: flex-end;
  flex: 1;
  min-width: 50px; /* Ensure minimum spacing to the right edge */
}

.right-section .nav-item {
  margin: 0 0.5rem; /* Add horizontal spacing between right section items */
  padding: 0;
  display: flex;
  align-items: center;
}

.right-section .nav-item:last-child {
  margin-right: 0; /* Remove right margin from last item */
}

/* Ensure the auth controls have consistent spacing and alignment */
.auth-controls {
  margin-left: 0;
  display: flex;
  align-items: center;
}



.navbar-item {
  font-weight: 400 !important;
  text-decoration: none !important;
}

/* Removed old new-session-link styling - now uses nav-link */

/* Navigation link styling - matching global black button styling */
.nav-link {
  background-color: #000 !important;
  color: #fff !important;
  border: none !important;
  text-decoration: none !important;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.875rem;
  padding: 0;
  border-radius: 2px;
  outline: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100px;
  height: 40px;
  transition: background-color 0.2s;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  -webkit-appearance: none !important;
  -moz-appearance: none !important;
  appearance: none !important;
  box-shadow: none !important;
}

.nav-link:hover, .nav-link:focus {
  background-color: #888 !important;
  color: #fff !important;
  text-decoration: none !important;
}

/* Override any router-link specific styling */
.nav-link.router-link-active {
  background-color: #888 !important;
  color: #fff !important;
}

.nav-link.router-link-exact-active {
  background-color: #888 !important;
  color: #fff !important;
}

/* Simple underlined text links for navigation */
.nav-text-link {
  color: #181818 !important;
  text-decoration: none !important;
  font-weight: 500;
  font-size: 0.875rem;
  padding: 8px 12px;
  border-radius: 0;
  transition: color 0.2s;
  border-bottom: 2px solid transparent;
  position: relative;
}

.nav-text-link:hover, .nav-text-link:focus {
  color: #111 !important;
  text-decoration: underline !important;
  border-bottom: none;
}

.nav-text-link.router-link-active {
  color: #111 !important;
  text-decoration: underline !important;
  border-bottom: none;
}

.nav-text-link.router-link-exact-active {
  color: #111 !important;
  text-decoration: underline !important;
  border-bottom: none;
}

/* You may add any App.vue-specific tweaks here if required. */

</style>