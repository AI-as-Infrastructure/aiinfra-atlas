import { ref } from 'vue'
import { Auth } from 'aws-amplify'

const useCognito = import.meta.env.VITE_USE_COGNITO_AUTH === 'true'
const user = ref(null)

export function useAuth() {
  async function signIn() {
    if (useCognito) {
      await Auth.federatedSignIn()
      user.value = await Auth.currentAuthenticatedUser()
    } else {
      user.value = { username: 'devuser', email: 'dev@local' }
    }
  }
  async function signOut() {
    if (useCognito) {
      await Auth.signOut()
      user.value = null
    } else {
      user.value = null
    }
  }
  return { user, signIn, signOut, isAuthenticated: () => !!user.value }
} 