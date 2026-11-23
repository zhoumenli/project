<template>
  <div class="row" style="align-items:flex-start">
    <!-- ============ left: form + history ============ -->
    <div class="col" style="flex:1;max-width:420px">
      <div class="panel">
        <div class="panel-head"><h2>🎯 元素定位提取</h2></div>
        <div class="panel-body">
          <div class="hint-bar">
            先填页面地址（需要 Basic Auth 时再填 username/password），然后选一种定位方式：<b>直接定位</b>（自动打开页面按关键词提取）或 <b>交互浏览器</b>（你亲自操作到目标页后再提取）。定位按 <b>角色 → CSS → XPath</b> 优先级并验证唯一性。
          </div>

          <!-- 公共：URL + 可选 Basic Auth -->
          <div class="field"><label>url *</label><input class="input" v-model="form.url" /></div>
          <div class="field"><label>username（可选，Basic Auth）</label><input class="input" v-model="form.username" autocomplete="off" name="tef_basic_auth_user" data-no-autofill="user" @pointerdown="markTouched('user')" @keydown="markTouched('user')" /></div>
          <div class="field"><label>password（可选，Basic Auth）</label><input class="input" type="password" v-model="form.password" autocomplete="off" name="tef_basic_auth_pass" data-no-autofill="pass" @pointerdown="markTouched('pass')" @keydown="markTouched('pass')" /></div>
          <div class="url-preview">实际访问：<code>{{ maskUrl(builtUrl) || '（请填写 url）' }}</code></div>

          <!-- 定位方式 -->
          <div class="field" style="margin-top:14px">
            <label>获取元素定位方式</label>
            <div class="radio-row">
              <label class="radio"><input type="radio" value="direct" v-model="locateMode" /> 直接定位</label>
              <label class="radio"><input type="radio" value="interactive" v-model="locateMode" /> 交互浏览器（我操作页面）</label>
            </div>
          </div>

          <!-- 方式一：直接定位 -->
          <template v-if="locateMode === 'direct'">
            <div class="field"><label>元素关键词 *（如：登录、用户名、请输入密码）</label><input class="input" v-model="form.keyword" @keyup.enter="extract" /></div>
            <div class="field">
              <label>匹配模式</label>
              <div class="radio-row">
                <label class="radio"><input type="radio" value="contains" v-model="form.mode" /> 包含匹配</label>
                <label class="radio"><input type="radio" value="exact" v-model="form.mode" /> 精确匹配</label>
              </div>
            </div>
            <div class="field"><label>页面加载等待（毫秒）</label><input class="input" type="number" v-model.number="form.wait_ms" min="0" max="10000" /></div>
            <div class="field">
              <div class="adv-toggle" @click="showAdv=!showAdv">{{ showAdv ? '▾' : '▸' }} 高级：前置操作步骤（先登录/先点击再提取）</div>
              <div v-if="showAdv">
                <textarea class="textarea mono" v-model="stepsStr"></textarea>
                <div class="adv-tip">支持的 action：fill / click / check / wait / goto，target 为 CSS 选择器</div>
              </div>
            </div>
            <button class="btn btn-primary" style="width:100%;padding:11px" @click="extract" :disabled="loading || !builtUrl || !form.keyword">
              {{ loading ? '🌐 正在打开浏览器提取...' : '🎯 提取元素定位' }}
            </button>
            <div v-if="loading" class="loading-note">正在启动浏览器加载页面并分析元素，约需 3~10 秒</div>
          </template>

          <!-- 方式二：交互浏览器 -->
          <template v-else>
            <div class="field" v-if="!interactive.sid">
              <button class="btn btn-primary" style="width:100%;padding:11px" @click="openInteractive" :disabled="!builtUrl || interactiveStarting">
                {{ interactiveStarting ? '正在打开浏览器...' : '🌐 打开浏览器' }}
              </button>
              <div class="adv-tip">弹出真实浏览器窗口，可在里面登录、跳转、滚动到目标页面</div>
            </div>
            <div v-else class="interactive-panel">
              <div class="interactive-status">
                <span class="dot" :class="interactive.status"></span>
                浏览器已打开 · {{ interactive.status === 'ready' ? '可以定位' : interactive.status }}
                <button class="btn btn-sm btn-danger" style="margin-left:auto" @click="closeInteractive">关闭浏览器</button>
              </div>
              <div class="adv-tip" v-if="interactive.currentUrl">当前页面：{{ interactive.currentUrl }}</div>
              <div class="field" style="margin-top:10px">
                <label>元素关键词（对当前页面定位）</label>
                <input class="input" v-model="form.keyword" @keyup.enter="locateInteractive" />
              </div>
              <button class="btn btn-primary" style="width:100%;padding:11px" @click="locateInteractive" :disabled="!form.keyword || interactiveLocating">
                {{ interactiveLocating ? '正在分析当前页面...' : '🎯 在当前页面定位元素' }}
              </button>
              <div class="adv-tip">可在浏览器里换到别的页面后，再次输入关键词定位，浏览器会一直保持打开</div>
            </div>
          </template>
        </div>
      </div>

      <!-- history -->
      <div class="panel" style="margin-top:16px">
        <div class="panel-head"><h2>📜 提取历史</h2><button v-if="history.length" class="btn btn-sm btn-danger" @click="clearHistory">清空</button></div>
        <div class="panel-body" style="padding:10px">
          <div v-for="(h,i) in history" :key="i" class="hist-item" @click="applyHistory(h)">
            <div class="hist-main"><b>{{ h.keyword }}</b><span class="muted" style="font-size:11px">{{ h.matched }} 个元素</span></div>
            <div class="muted hist-url">{{ h.url }}</div>
          </div>
          <div v-if="!history.length" class="empty" style="padding:16px 0">暂无提取记录</div>
        </div>
      </div>
    </div>

    <!-- ============ right: result ============ -->
    <div class="col" style="flex:1.7">
      <div class="panel">
        <div class="panel-head">
          <h2>提取结果</h2>
          <div v-if="result && result.matched" class="muted" style="font-size:12px">{{ result.page_title }} · 命中 {{ result.matched }} 个元素</div>
        </div>
        <div class="panel-body" style="max-height:78vh;overflow:auto">

          <div v-if="!result" class="empty"><div class="big">🎯</div>填写网址和元素关键词，点击左侧「提取元素定位」</div>
          <div v-else-if="result.message" class="empty"><div class="big">🔍</div>{{ result.message }}</div>
          <template v-else>
            <!-- element switcher -->
            <div v-if="result.matched > 1" class="elem-switch">
              <div v-for="el in result.elements" :key="el.index"
                   class="elem-pill" :class="{active: selected===el.index}" @click="selected=el.index">
                <span class="tag">{{ el.tag }}</span>
                <span class="pill-text">{{ el.direct_text || el.accessible_name || el.attrs.placeholder || ('#' + el.attrs.id) || el.outer_html.slice(0, 30) }}</span>
              </div>
            </div>

            <div v-if="current" class="result-body">
              <!-- screenshots -->
              <div class="shots-row">
                <div class="shot-box">
                  <div class="shot-label">📄 页面截图（红框 = 匹配元素）</div>
                  <img v-if="result.full_shot" :src="apiBase + result.full_shot" class="full-shot" @click="openImage(result.full_shot)" />
                </div>
                <div class="shot-box" style="width:200px">
                  <div class="shot-label">🖼️ 元素截图</div>
                  <img v-if="current.element_shot" :src="apiBase + current.element_shot" class="elem-shot" @click="openImage(current.element_shot)" />
                  <div v-else class="muted" style="font-size:12px;padding:20px 0">无截图</div>
                </div>
              </div>

              <!-- element meta -->
              <div class="meta-grid">
                <div><span class="muted">标签</span><b>&lt;{{ current.tag }}&gt;</b></div>
                <div><span class="muted">语义角色</span><b>{{ current.role || '—（无语义角色）' }}</b></div>
                <div><span class="muted">可访问名</span><b>{{ current.accessible_name || '—' }}</b></div>
                <div><span class="muted">匹配依据</span><b>{{ matchedOnName(current.matched_on) }}</b></div>
              </div>

              <!-- locator cards: role > css > xpath -->
              <div class="loc-cards">
                <div v-for="(card, ci) in locatorCards" :key="card.key" class="loc-card" :class="{recommended: card.best?.recommended}">
                  <div class="loc-head">
                    <span class="loc-pri">{{ ci + 1 }}</span>
                    <span class="loc-type">{{ card.label }}</span>
                    <span v-if="card.best?.recommended" class="badge passed">⭐ 推荐使用</span>
                    <span v-if="card.best" class="badge" :class="card.best.unique ? 'passed' : 'failed'">
                      {{ card.best.unique ? '✓ 唯一' : `匹配 ${card.best.match_count} 个` }}
                    </span>
                    <span v-if="!card.best" class="badge skipped">不可用</span>
                  </div>
                  <div class="loc-desc">{{ card.desc }}</div>
                  <template v-if="card.best">
                    <div class="loc-code-row">
                      <code class="loc-code">{{ card.display }}</code>
                      <button class="btn btn-sm" @click="copy(card.copyValue)">复制</button>
                    </div>
                    <div v-if="card.usage" class="loc-usage">Playwright: <code>{{ card.usage }}</code></div>
                    <details v-if="card.all && card.all.length > 1" class="loc-alts">
                      <summary>备选 {{ card.all.length - 1 }} 个</summary>
                      <div v-for="(a, ai) in card.all.slice(1)" :key="ai" class="alt-row" @click="copy(a.value)">
                        <span class="badge" :class="a.unique ? 'passed' : 'failed'" style="flex-shrink:0">{{ a.unique ? '唯一' : a.match_count + '个' }}</span>
                        <code>{{ a.value }}</code>
                        <span class="muted alt-note">{{ a.note }}</span>
                      </div>
                    </details>
                  </template>
                  <div v-else class="muted" style="font-size:12px;padding:8px 0">该元素无法生成此类定位</div>
                </div>
              </div>

              <!-- attributes -->
              <details class="attrs">
                <summary>元素属性与 HTML</summary>
                <div class="attrs-grid">
                  <div v-for="(v, k) in current.attrs" :key="k" v-show="v !== '' && v !== null" class="attr-item">
                    <span class="muted">{{ k }}</span><code>{{ v }}</code>
                  </div>
                </div>
                <pre class="code">{{ current.outer_html }}</pre>
              </details>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api, notify } from '../api'

const apiBase = ''
const form = ref({
  url: '',
  username: '',
  password: '',
  keyword: '', mode: 'contains', wait_ms: '',
})
const locateMode = ref('direct')
const stepsStr = ref('')
const showAdv = ref(false)
const loading = ref(false)
const result = ref(null)
const selected = ref(0)
const history = ref([])
const HIST_KEY = 'locator_history'

// 交互式浏览器会话
const interactive = ref({ sid: '', status: '', currentUrl: '' })
const interactiveStarting = ref(false)
const interactiveLocating = ref(false)
let statusTimer = null

// ------------------------------------------------------------------
// 清除浏览器自动填充
// 四层防护：
//   1) autocomplete="off" —— 模板层，多数浏览器直接放弃填充
//   2) name 用非语义名 —— 不参与密码管理器的「用户名-密码」配对识别
//   3) :-/:-moz-autofill 伪类检测 —— 识别被填充过的元素
//   4) 持续巡检 —— 自动填充的时机不可控（可能发生在任何时刻，
//      甚至用户聚焦之后），必须持续盯着而不是只查一次
// ------------------------------------------------------------------
const touchedFields = new Set()
let autofillTimers = []
let autofillWatcher = null

function markTouched(key) {
  touchedFields.add(key)
}

function clearBrowserAutofill() {
  document.querySelectorAll('[data-no-autofill]').forEach((el) => {
    if (!el.value) return
    const key = el.dataset.noAutofill

    // 浏览器自动填充的元素会命中 :-webkit-autofill / :-moz-autofill 伪类
    let isAutoFilled = false
    try {
      isAutoFilled = el.matches(':-webkit-autofill') || el.matches(':-moz-autofill')
    } catch (e) {
      isAutoFilled = false
    }

    // 用户主动操作过（点过/敲过键盘）且不是自动填充 → 是用户自己填的，保留
    if (!isAutoFilled && touchedFields.has(key)) return

    // 其余情况一律视为自动填充并清空：
    //   伪类命中              → 确定是浏览器填的
    //   用户从未交互过却有值 → 只能是浏览器填的
    el.value = ''
    if (key === 'user') form.value.username = ''
    else if (key === 'pass') form.value.password = ''
  })
}

onMounted(() => {
  try { history.value = JSON.parse(localStorage.getItem(HIST_KEY) || '[]') } catch (e) {}
  // 浏览器「记住密码」会把用户自己的账号密码自动填进 Basic Auth 框，
  // 但这里要的是「目标站点」的凭据，自动填充只会造成误访问，必须清掉。
  clearBrowserAutofill()
  autofillTimers = [300, 1000, 2000].map((ms) => setTimeout(clearBrowserAutofill, ms))
  // 持续巡检：自动填充可能发生在任意时刻，也可能在用户聚焦之后才发生
  autofillWatcher = setInterval(clearBrowserAutofill, 1500)
})
onBeforeUnmount(() => {
  if (statusTimer) clearInterval(statusTimer)
  autofillTimers.forEach((t) => clearTimeout(t))
  autofillTimers = []
  if (autofillWatcher) clearInterval(autofillWatcher)
  autofillWatcher = null
})

async function openInteractive() {
  interactiveStarting.value = true
  try {
    const r = await api('/api/locator/interactive/start', { method: 'POST', body: { url: builtUrl.value } })
    interactive.value = { sid: r.session_id, status: r.status, currentUrl: '' }
    notify('浏览器已打开，请在窗口中操作（登录/跳转/滚动），然后回来定位元素')
    statusTimer = setInterval(pollInteractiveStatus, 1500)
  } catch (e) { notify('打开失败：' + e.message, 'error') }
  finally { interactiveStarting.value = false }
}

async function pollInteractiveStatus() {
  if (!interactive.value.sid) return
  try {
    const s = await api(`/api/locator/interactive/${interactive.value.sid}/status`)
    interactive.value.status = s.status
    interactive.value.currentUrl = s.url || ''
  } catch (e) {
    if (statusTimer) clearInterval(statusTimer)
    interactive.value.status = 'closed'
  }
}

async function locateInteractive() {
  if (!interactive.value.sid || !form.value.keyword) return
  interactiveLocating.value = true
  result.value = null
  try {
    const r = await api(`/api/locator/interactive/${interactive.value.sid}/locate`, {
      method: 'POST', body: { keyword: form.value.keyword.trim(), exact: form.value.mode === 'exact' },
    })
    result.value = r
    selected.value = r.elements?.[0]?.index ?? 0
    if (r.matched) {
      notify(`定位成功：当前页面命中 ${r.matched} 个元素`)
      saveHistory({ url: r.url || builtUrl.value, keyword: form.value.keyword.trim(), matched: r.matched, t: Date.now() })
    } else {
      notify(r.message || '未匹配到元素', 'error')
    }
  } catch (e) { notify('定位失败：' + e.message, 'error') }
  finally { interactiveLocating.value = false }
}

async function closeInteractive() {
  if (statusTimer) { clearInterval(statusTimer); statusTimer = null }
  try { await api(`/api/locator/interactive/${interactive.value.sid}/close`, { method: 'POST' }) } catch (e) {}
  interactive.value = { sid: '', status: '', currentUrl: '' }
  notify('浏览器已关闭')
}

// 填写了 username 才拼 Basic Auth（username:password@host），否则直接访问 url
const builtUrl = computed(() => {
  let host = (form.value.url || '').trim()
  if (!host) return ''
  const user = (form.value.username || '').trim()
  if (!user) return host
  const pass = form.value.password || ''
  host = host.replace(/^https?:\/\//i, '').replace(/^\/+/, '')
  return `http://${encodeURIComponent(user)}:${encodeURIComponent(pass)}@${host}`
})
// 预览时对 Basic Auth 密码打码，避免明文展示
const maskUrl = (u) => u ? u.replace(/(:\/\/[^:/@]+:)[^@]+(@)/, '$1****$2') : ''

const current = computed(() => {
  if (!result.value?.elements) return null
  return result.value.elements.find(e => e.index === selected.value) || result.value.elements[0]
})

const locatorCards = computed(() => {
  const c = current.value
  if (!c) return []
  const role = c.best?.role, css = c.best?.css, xp = c.best?.xpath
  return [
    {
      key: 'role', label: '角色定位（语义）', best: role, all: c.locators?.role || [],
      desc: '基于 ARIA 角色与可访问名，最稳定、最贴近用户行为语义',
      display: role ? `page.${role.value}` : '',
      usage: role ? `await page.${role.value.replace(/"/g, "'")}` : '',
      copyValue: role ? `page.${role.value}` : '',
    },
    {
      key: 'css', label: 'CSS 定位', best: css, all: c.locators?.css || [],
      desc: 'id > data-testid > 属性 > class > 结构路径，通用性强',
      display: css ? css.value : '',
      usage: css ? `page.locator("${css.value}")` : '',
      copyValue: css ? css.value : '',
    },
    {
      key: 'xpath', label: 'XPath 定位', best: xp, all: c.locators?.xpath || [],
      desc: '兜底方案，支持文本与层级，兼容 Selenium 等工具',
      display: xp ? xp.value : '',
      usage: xp ? `page.locator("xpath=${xp.value}")` : '',
      copyValue: xp ? xp.value : '',
    },
  ]
})

async function extract() {
  if (!builtUrl.value || !form.value.keyword) return
  loading.value = true
  result.value = null
  try {
    let steps = []
    if (stepsStr.value.trim()) {
      try { steps = JSON.parse(stepsStr.value) } catch (e) { throw new Error('前置步骤 JSON 格式错误') }
    }
    const finalUrl = builtUrl.value
    const body = {
      url: finalUrl,
      keyword: form.value.keyword.trim(),
      exact: form.value.mode === 'exact',
      wait_ms: form.value.wait_ms || 0,
      steps,
    }
    result.value = await api('/api/locator/extract', { method: 'POST', body })
    selected.value = result.value.elements?.[0]?.index ?? 0
    if (result.value.matched) {
      notify(`提取成功：命中 ${result.value.matched} 个元素`)
      saveHistory({ url: finalUrl, keyword: body.keyword, matched: result.value.matched, t: Date.now() })
    } else {
      notify(result.value.message || '未匹配到元素', 'error')
    }
  } catch (e) {
    notify('提取失败：' + e.message, 'error')
  } finally { loading.value = false }
}

function saveHistory(h) {
  history.value = [h, ...history.value.filter(x => !(x.url === h.url && x.keyword === h.keyword))].slice(0, 10)
  localStorage.setItem(HIST_KEY, JSON.stringify(history.value))
}
function applyHistory(h) {
  locateMode.value = 'direct'
  form.value.url = h.url; form.value.keyword = h.keyword
  notify('已回填网址，点击「提取元素定位」重新运行')
}
function clearHistory() { history.value = []; localStorage.removeItem(HIST_KEY) }

async function copy(text) {
  if (!text) return
  try { await navigator.clipboard.writeText(text); notify('已复制到剪贴板') }
  catch (e) {
    const ta = document.createElement('textarea')
    ta.value = text; document.body.appendChild(ta); document.execCommand('copy'); ta.remove()
    notify('已复制到剪贴板')
  }
}
function openImage(path) { window.open(apiBase + path, '_blank') }
function matchedOnName(m) {
  return ({ text: '元素自身文本', 'aria-label': 'aria-label 属性', placeholder: '占位符',
    title: 'title 属性', value: 'value 值', alt: 'alt 文本', 'accessible-name': '可访问名（label 关联等）',
    name: 'name 属性', 'data-testid': 'data-testid', id: 'id', inner: '元素文本', tag: '标签名' })[m] || m
}
</script>

<style scoped>
.hint-bar { background: var(--primary-light); color: var(--primary); border-radius: 8px; padding: 10px 12px; font-size: 12px; line-height: 1.7; margin-bottom: 14px; }
/* 抹掉浏览器自动填充时自带的黄色高亮，避免和"用户已填"状态混淆 */
input[data-no-autofill]:-webkit-autofill,
input[data-no-autofill]:-webkit-autofill:hover,
input[data-no-autofill]:-webkit-autofill:focus {
  -webkit-text-fill-color: #1e2440;
  -webkit-box-shadow: 0 0 0 1000px var(--panel) inset;
  caret-color: #1e2440;
  transition: background-color 9999s ease-out 0s;
}
.radio-row { display: flex; gap: 16px; }
.radio-row.wrap { flex-wrap: wrap; gap: 10px; }
.interactive-panel { background:rgba(39,166,68,.08); border:1px solid rgba(39,166,68,.3); border-radius:8px; padding:12px; margin-top:10px; }
.interactive-status { display:flex; align-items:center; gap:6px; font-size:12px; }
.dot { width:8px; height:8px; border-radius:50%; background:#bbb; display:inline-block; }
.dot.ready { background:var(--success); }
.dot.starting { background:#e2a33c; }
.dot.closed, .dot.expired, .dot.error { background:#e8534e; }
.radio { display: flex; align-items: center; gap: 5px; font-size: 13px; cursor: pointer; }
.adv-toggle { cursor: pointer; font-size: 12px; color: var(--muted); user-select: none; }
.adv-toggle:hover { color: var(--primary); }
.adv-tip { font-size: 11px; color: var(--muted); margin-top: 4px; }
.url-preview { font-size: 11px; color: var(--muted); margin-top: 6px; word-break: break-all; }
.url-preview code { background: var(--primary-light); color: var(--primary); padding: 2px 6px; border-radius: 4px; }
.mono { font-family: Consolas, Monaco, monospace; font-size: 12px; }
.loading-note { text-align: center; color: var(--muted); font-size: 12px; margin-top: 10px; }
.hist-item { padding: 8px 10px; border-radius: 8px; cursor: pointer; }
.hist-item:hover { background: var(--primary-light); }
.hist-main { display: flex; justify-content: space-between; align-items: center; }
.hist-url { font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.elem-switch { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.elem-pill { display: flex; align-items: center; gap: 6px; border: 1px solid var(--border); border-radius: 20px; padding: 5px 12px; cursor: pointer; font-size: 12px; max-width: 240px; }
.elem-pill:hover { border-color: var(--primary); }
.elem-pill.active { border-color: var(--primary); background: var(--primary-light); color: var(--primary); font-weight: 600; }
.pill-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.shots-row { display: flex; gap: 14px; margin-bottom: 14px; }
.shot-box { flex: 1; min-width: 0; }
.shot-label { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.full-shot { width: 100%; border: 1px solid var(--border); border-radius: 8px; cursor: zoom-in; }
.elem-shot { max-width: 100%; max-height: 120px; border: 1px solid var(--border); border-radius: 8px; cursor: zoom-in; }
.meta-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; background: var(--panel-2); border-radius: 8px; padding: 12px; margin-bottom: 16px; }
.meta-grid > div { display: flex; flex-direction: column; gap: 3px; font-size: 13px; min-width: 0; }
.meta-grid b { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta-grid .muted { font-size: 11px; }
.loc-cards { display: flex; flex-direction: column; gap: 12px; }
.loc-card { border: 1px solid var(--border); border-radius: 10px; padding: 14px; }
.loc-card.recommended { border-color: var(--success); background: rgba(39,166,68,.08); }
.loc-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.loc-pri { width: 22px; height: 22px; border-radius: 50%; background: var(--primary-light); color: var(--primary); display: grid; place-items: center; font-size: 12px; font-weight: 700; }
.loc-card.recommended .loc-pri { background: var(--success); color: #fff; }
.loc-type { font-weight: 600; font-size: 14px; }
.loc-desc { font-size: 12px; color: var(--muted); margin-bottom: 10px; }
.loc-code-row { display: flex; gap: 8px; align-items: stretch; }
.loc-code { flex: 1; background: var(--text); color: #8ef0b6; padding: 10px 12px; border-radius: 8px; font-family: Consolas, Monaco, monospace; font-size: 13px; word-break: break-all; }
.loc-usage { margin-top: 8px; font-size: 12px; color: var(--muted); }
.loc-usage code { background: #f0f2f5; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
.loc-alts { margin-top: 10px; }
.loc-alts summary { cursor: pointer; font-size: 12px; color: var(--muted); }
.alt-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; cursor: pointer; border-bottom: 1px dashed var(--border); }
.alt-row:hover code { color: var(--primary); }
.alt-row code { font-family: Consolas, monospace; font-size: 12px; word-break: break-all; }
.alt-note { font-size: 11px; flex-shrink: 0; }
.attrs { margin-top: 14px; }
.attrs summary { cursor: pointer; font-size: 12px; color: var(--muted); }
.attrs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 10px 0; }
.attr-item { display: flex; flex-direction: column; gap: 2px; font-size: 12px; background: var(--panel-2); border-radius: 6px; padding: 6px 8px; min-width: 0; }
.attr-item code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
</style>
