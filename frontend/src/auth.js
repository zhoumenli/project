import { ref, computed } from 'vue'

const TOKEN_KEY = 'tef_auth_token'
const USER_KEY = 'tef_auth_user'

export const token = ref(localStorage.getItem(TOKEN_KEY) || '')
export const user = ref((() => {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch (e) { return null }
})())

export const isLoggedIn = computed(() => !!token.value)

export function setSession(newToken, newUser) {
  token.value = newToken
  user.value = newUser
  localStorage.setItem(TOKEN_KEY, newToken)
  localStorage.setItem(USER_KEY, JSON.stringify(newUser))
}

export function clearSession() {
  token.value = ''
  user.value = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
