import { createRouter, createWebHistory } from 'vue-router'
import ChatContainer from '@/components/ChatContainer.vue'
import AboutPage from '@/pages/AboutPage.vue'
import FAQPage from '@/pages/FAQPage.vue'
import AmplifyCallback from '@/pages/AmplifyCallback.vue'
import LoginPage from '@/pages/LoginPage.vue'
import { isCognitoEnabled, isAuthenticated } from '@/auth/amplify-auth'

const routes = [
  { path: '/', component: ChatContainer, meta: { requiresAuth: true } },
  { path: '/about', component: AboutPage },
  { path: '/faq', component: FAQPage },
  
  // Authentication routes
  { path: '/login', component: LoginPage, name: 'login' },
  { path: '/callback', component: AmplifyCallback, name: 'callback' },
  
  // No debug pages needed
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  // Skip auth check if Cognito is disabled
  if (!isCognitoEnabled()) {
    next()
    return
  }

  // Debug current path
  console.log('Route navigation:', to.path)
  
  // Special case for coming from logout page to login page - always allow
  // if (to.path === '/login' && from.path === '/logout') {
  //   console.log('Coming from logout, allowing access to login page')
  //   next()
  //   return
  // }
  
  // Callback and logout routes - always accessible
  if (to.path === '/callback') {
    console.log('Allowing access to auth callback page:', to.path)
    next()
    return
  }
  
  // Check for logout query parameter as a force-logout signal
  if (to.query.logout === 'true') {
    console.log('Logout query parameter detected, treating as unauthenticated')
    next()
    return
  }

  // For public routes (login, about, faq) - check authentication to handle redirects
  if (to.path === '/login' || to.path === '/about' || to.path === '/faq') {
    // Special case: force check of storage for explicit logout
    if (to.path === '/login' && localStorage.getItem('force_logout') === 'true') {
      console.log('Force logout detected, allowing login page access')
      localStorage.removeItem('force_logout')
      next()
      return
    }
    
    // Regular authentication check for other cases
    try {
      const authenticated = await isAuthenticated()
      
      // If already authenticated and trying to access login, redirect to home
      if (to.path === '/login' && authenticated) {
        console.log('Already authenticated, redirecting from login to home')
        next('/')
        return
      }
      
      console.log('Allowing access to public page')
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
      console.log('Authentication required but not authenticated, redirecting to login')
      next({ path: '/login' })
      return
    }
    
    // User is authenticated or route doesn't require auth
    next()
  } catch (error) {
    console.error('Auth check error:', error)
    next({ path: '/login' })
  }

  // All checks passed, proceed
  next()
})

export default router