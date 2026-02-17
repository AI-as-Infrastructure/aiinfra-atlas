import { createRouter, createWebHistory } from 'vue-router'
import ChatContainer from '@/components/ChatContainer.vue'
import AboutPage from '@/pages/AboutPage.vue'
import FAQPage from '@/pages/FAQPage.vue'
import InterRaterPage from '@/pages/InterRaterPage.vue'
import AmplifyCallback from '@/pages/AmplifyCallback.vue'
import LoginPage from '@/pages/LoginPage.vue'
import CorpusWizard from '@/pages/CorpusWizard.vue'
import ModeSelector from '@/components/ModeSelector.vue'
import ConfigManager from '@/pages/ConfigManager.vue'
import { isCognitoEnabled, isAuthenticated } from '@/auth/amplify-auth'

const routes = [
  // Main application route (requires deployment mode)
  { path: '/chat', component: ChatContainer, meta: { requiresAuth: true, requiresDeploy: true }, name: 'chat' },

  // Mode selection (entry point after auth)
  { path: '/', component: ModeSelector, meta: { requiresAuth: true }, name: 'mode-selector' },
  { path: '/mode', component: ModeSelector, meta: { requiresAuth: true }, name: 'mode' },

  // Configuration routes (require authentication and configuration mode)
  { path: '/corpus-wizard', component: CorpusWizard, name: 'corpus-wizard', meta: { requiresAuth: true, requiresConfigure: true } },
  { path: '/config-manager', component: ConfigManager, name: 'config-manager', meta: { requiresAuth: true, requiresConfigure: true } },
  { path: '/setup', redirect: '/corpus-wizard' },  // Alias for corpus wizard

  // Public routes
  { path: '/about', component: AboutPage },
  { path: '/faq', component: FAQPage },

  // Inter-rater (requires deployment mode)
  { path: '/inter-rater', component: InterRaterPage, meta: { requiresAuth: true, requiresDeploy: true } },

  // Authentication routes
  { path: '/login', component: LoginPage, name: 'login' },
  { path: '/callback', component: AmplifyCallback, name: 'callback' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Helper function to check system mode
async function checkSystemMode() {
  try {
    const response = await fetch('/api/mode/status')
    if (response.ok) {
      const data = await response.json()
      return data
    }
  } catch (error) {
    console.error('Failed to check system mode:', error)
  }
  return { mode: null, config_complete: false }
}

// Navigation guard for authentication and mode
router.beforeEach(async (to, from, next) => {
  // Skip auth check if Cognito is disabled
  if (!isCognitoEnabled()) {
    // Even without auth, check mode for configuration vs deploy routes
    const modeStatus = await checkSystemMode()

    // If in deploy mode and accessing root, redirect to chat
    if (to.path === '/' && modeStatus.mode === 'deploy') {
      next('/chat')
      return
    }

    // Mode-based routing
    if (to.meta.requiresDeploy && modeStatus.mode !== 'deploy') {
      next('/')  // Go to mode selector
      return
    }

    if (to.meta.requiresConfigure && modeStatus.mode === 'deploy') {
      next('/chat')
      return
    }

    next()
    return
  }

  // Callback and logout routes - always accessible
  if (to.path === '/callback') {
    next()
    return
  }

  // Check for logout query parameter as a force-logout signal
  if (to.query.logout === 'true') {
    next()
    return
  }

  // For public routes (login, about, faq) - check authentication to handle redirects
  if (to.path === '/login' || to.path === '/about' || to.path === '/faq') {
    // Special case: force check of storage for explicit logout
    if (to.path === '/login' && localStorage.getItem('force_logout') === 'true') {
      localStorage.removeItem('force_logout')
      next()
      return
    }

    // Regular authentication check for other cases
    try {
      const authenticated = await isAuthenticated()

      // If already authenticated and trying to access login, redirect to home
      if (to.path === '/login' && authenticated) {
        next('/')
        return
      }

      next()
    } catch (error) {
      console.error('Auth check error for public page:', error)
      next() // Still allow access to public pages on error
    }
    return
  }

  // For routes requiring authentication, check if user is logged in
  try {
    const authenticated = await isAuthenticated()

    if (to.matched.some(record => record.meta.requiresAuth) && !authenticated) {
      next({ path: '/login' })
      return
    }

    // If authenticated, also check mode requirements
    if (authenticated) {
      const modeStatus = await checkSystemMode()

      // If in deploy mode and accessing root, redirect to chat
      if ((to.path === '/' || to.path === '/mode') && modeStatus.mode === 'deploy') {
        next('/chat')
        return
      }

      // Mode-based routing for authenticated users
      if (to.meta.requiresDeploy && modeStatus.mode !== 'deploy') {
        next('/')  // Go to mode selector
        return
      }

      if (to.meta.requiresConfigure && modeStatus.mode === 'deploy') {
        next('/chat')
        return
      }
    }

    // User is authenticated and mode requirements are met
    next()
  } catch (error) {
    console.error('Auth check error:', error)
    next({ path: '/login' })
  }
})

export default router
