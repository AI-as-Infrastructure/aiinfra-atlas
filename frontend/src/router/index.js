import { createRouter, createWebHistory } from 'vue-router'
import ChatContainer from '@/components/ChatContainer.vue'
import AboutPage from '@/pages/AboutPage.vue'
import FAQPage from '@/pages/FAQPage.vue'
import Callback from '@/pages/Callback.vue'
import AmplifyCallback from '@/pages/AmplifyCallback.vue'
import LogoutComplete from '../pages/LogoutComplete.vue'
import LogoutRedirect from '../pages/LogoutRedirect.vue'
import LogoutPage from '@/pages/LogoutPage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import AmplifyLogin from '@/pages/AmplifyLogin.vue'
import AuthDebug from '@/pages/AuthDebug.vue'
import TokenDebug from '@/pages/TokenDebug.vue'
import StorageTest from '@/pages/StorageTest.vue'
import { isCognitoEnabled, isAuthenticated } from '@/auth/cognito'

const routes = [
  { path: '/', component: ChatContainer, meta: { requiresAuth: true } },
  { path: '/about', component: AboutPage },
  { path: '/faq', component: FAQPage },
  
  // Original auth routes
  { path: '/login', component: LoginPage, name: 'login' },
  { path: '/callback', component: Callback, name: 'callback' },
  
  // Amplify-based auth routes
  { path: '/amplify-login', component: AmplifyLogin, name: 'amplify-login' },
  { path: '/amplify-callback', component: AmplifyCallback, name: 'amplify-callback' },
  
  // Logout routes
  { path: '/logout', component: LogoutPage, name: 'logout' },
  { path: '/logout-complete', component: LogoutComplete, name: 'logout-complete' },
  { path: '/logout.html', component: LogoutRedirect, name: 'logout-html' }, // Match Cognito's sign-out URL
  
  // Debug pages
  { path: '/auth-debug', component: AuthDebug, name: 'auth-debug' }, // Debug page for authentication
  { path: '/token-debug', component: TokenDebug, name: 'token-debug' }, // Token debugging page
  { path: '/storage-test', component: StorageTest, name: 'storage-test' }, // Storage testing page
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard for authentication
router.beforeEach((to, from, next) => {
  // Skip auth check if Cognito is disabled
  if (!isCognitoEnabled()) {
    next()
    return
  }

  // Debug current path and authentication state
  console.log('Route navigation:', to.path, 'Auth state:', isAuthenticated())

  // Debug pages should always be accessible
  if (to.path === '/auth-debug' || to.path === '/token-debug' || to.path === '/storage-test') {
    next()
    return
  }
  
  // Callback and logout routes - always accessible
  if (to.path === '/callback' || to.path === '/amplify-callback' || 
      to.path === '/logout.html' || to.path === '/logout-complete') {
    console.log('Allowing access to auth callback/logout page:', to.path)
    next()
    return
  }

  // Public routes that should always be accessible
  if (to.path === '/login' || to.path === '/about' || to.path === '/faq') {
    // If already authenticated and trying to access login, redirect to home
    if (to.path === '/login' && isAuthenticated()) {
      console.log('Already authenticated, redirecting from login to home')
      next('/')
      return
    }
    
    console.log('Allowing access to public page')
    next()
    return
  }

  // For routes requiring authentication, check if user is logged in
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isAuthenticated()) {
      console.log('Authentication required but not authenticated, redirecting to login')
      next({ name: 'login' })
      return
    }
  }

  // All checks passed, proceed
  next()
})

export default router