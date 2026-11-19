import { ref, computed } from 'vue'

const TOKEN_KEY = 'tef_auth_token'
const USER_KEY = 'tef_auth_user'
const ACTIVITY_KEY = 'tef_last_activity'
const IDLE_KEY = 'tef_idle_timeout'

/** 默认空闲超时（毫秒）——后端未返回时兜底 */
export const DEFAULT_IDLE_TIMEOUT_MS = 30 * 60 * 1000

export const token = ref(localStorage.getItem(TOKEN_KEY) || '')
export const user = ref((() => {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch (e) { return null }
})())

export const isLoggedIn = computed(() => !!token.value)

// ============================================================
// 会话空闲超时：连续无操作达到阈值后自动退出登录
// ============================================================

/** 空闲阈值（毫秒）。存 localStorage，保证刷新页面后仍然有效 */
export const idleTimeoutMs = ref(Number(localStorage.getItem(IDLE_KEY)) || DEFAULT_IDLE_TIMEOUT_MS)

/** 最后一次活跃时间戳。多标签页共享同一个 key，任一标签页有操作即刷新全部页面 */
function readActivity() {
  const raw = Number(localStorage.getItem(ACTIVITY_KEY) || 0)
  return raw || Date.now()
}

function writeActivity(ts) {
  try { localStorage.setItem(ACTIVITY_KEY, String(ts)) } catch (e) {}
}

/** 记录一次用户操作（带 1 秒节流，避免高频写 localStorage） */
let lastWrite = 0
export function touchActivity() {
  const now = Date.now()
  if (now - lastWrite < 1000) return
  lastWrite = now
  writeActivity(now)
}

/** 距离自动登出还剩多少毫秒 */
export function idleRemainingMs() {
  if (!isLoggedIn.value) return 0
  return Math.max(0, idleTimeoutMs.value - (Date.now() - readActivity()))
}

/** 是否已经空闲超时 */
export function isIdleExpired() {
  if (!isLoggedIn.value) return false
  return Date.now() - readActivity() >= idleTimeoutMs.value
}

// ---- 活动事件监听 ----
const ACTIVITY_EVENTS = ['mousedown', 'mousemove', 'keydown', 'scroll', 'wheel', 'touchstart']
let activityHandler = null
let idleTimer = null
let checkTimer = null

export function startIdleWatch(onExpire) {
  stopIdleWatch()
  if (!isLoggedIn.value) return

  activityHandler = () => touchActivity()
  ACTIVITY_EVENTS.forEach((ev) =>
    window.addEventListener(ev, activityHandler, { passive: true, capture: true })
  )

  // 每 10 秒巡检一次，超时则触发登出
  idleTimer = setInterval(() => {
    if (!isLoggedIn.value) { stopIdleWatch(); return }
    if (isIdleExpired()) {
      stopIdleWatch()
      onExpire && onExpire()
    }
  }, 10000)

  // 每 30 秒刷新一次「剩余时间」显示（供 UI 展示用）
  checkTimer = setInterval(() => { idleTick.value = Date.now() }, 30000)
}

export function stopIdleWatch() {
  if (activityHandler) {
    ACTIVITY_EVENTS.forEach((ev) =>
      window.removeEventListener(ev, activityHandler, { capture: true })
    )
    activityHandler = null
  }
  if (idleTimer) { clearInterval(idleTimer); idleTimer = null }
  if (checkTimer) { clearInterval(checkTimer); checkTimer = null }
}

/** 用于驱动「剩余时间」文本的响应式刷新 */
export const idleTick = ref(Date.now())

export function setSession(newToken, newUser, idleTimeoutSeconds) {
  token.value = newToken
  user.value = newUser
  localStorage.setItem(TOKEN_KEY, newToken)
  localStorage.setItem(USER_KEY, JSON.stringify(newUser))
  if (idleTimeoutSeconds) {
    idleTimeoutMs.value = idleTimeoutSeconds * 1000
    localStorage.setItem(IDLE_KEY, String(idleTimeoutMs.value))
  }
  writeActivity(Date.now())
}

export function clearSession() {
  token.value = ''
  user.value = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(ACTIVITY_KEY)
  stopIdleWatch()
}
