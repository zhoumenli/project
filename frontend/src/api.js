import { ref } from 'vue'
import { token, clearSession } from './auth'

export const API_BASE = ''

export async function api(path, options = {}) {
  const { method = 'GET', body, rawBody, ...rest } = options
  const config = { method, headers: {}, ...rest }
  if (token.value) config.headers['Authorization'] = `Bearer ${token.value}`
  if (rawBody) {
    // FormData: let the browser set Content-Type with boundary
    config.body = body
  } else {
    config.headers['Content-Type'] = 'application/json'
    if (body !== undefined) config.body = JSON.stringify(body)
  }
  const resp = await fetch(API_BASE + path, config)
  if (resp.status === 401 && !path.startsWith('/api/auth/')) {
    clearSession()
    const pub = ['/', '/login', '/register']
    if (!pub.includes(window.location.pathname)) {
      window.location.href = '/login'
    }
  }
  if (!resp.ok) {
    let msg = resp.statusText
    try { msg = (await resp.json()).detail || msg } catch (e) {}
    throw new Error(msg)
  }
  return resp.json()
}

// shared global state
export const currentProject = ref(null)
export const projects = ref([])
export const toast = ref(null)

export function notify(msg, type = 'success') {
  toast.value = { msg, type }
  setTimeout(() => { toast.value = null }, 2600)
}

export async function loadProjects() {
  projects.value = await api('/api/projects')
  if (!currentProject.value && projects.value.length) {
    currentProject.value = projects.value[0]
  }
}
