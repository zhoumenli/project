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

  // 响应体只解析一次，后续逻辑复用
  let payload = null
  let parsed = false
  try { payload = await resp.json(); parsed = true } catch (e) {}

  if (resp.status === 401 && !path.startsWith('/api/auth/')) {
    const detail = (parsed && payload && payload.detail) || ''
    const code = (parsed && payload && payload.code) || resp.headers.get('X-Auth-Error') || ''
    clearSession()
    const pub = ['/', '/login', '/register']
    if (!pub.includes(window.location.pathname)) {
      const reason = code === 'idle_timeout' || detail.includes('未操作') ? 'idle' : 'expired'
      window.location.href = '/login?reason=' + reason
    }
  }
  if (!resp.ok) {
    const msg = (parsed && payload && payload.detail) || resp.statusText
    throw new Error(msg)
  }
  return payload
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
