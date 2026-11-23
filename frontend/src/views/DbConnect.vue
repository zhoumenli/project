<template>
  <div class="row" style="align-items:flex-start">
    <div class="col" style="max-width:420px;flex:0 0 400px">
      <div class="panel">
        <div class="panel-head"><h2>🗄 数据库连接</h2><span class="saved-count" v-if="savedList.length">{{ savedList.length }} 个已保存</span></div>
        <div class="panel-body">
          <div class="field">
            <label>数据库类型</label>
            <select class="select" v-model="form.db_type" @change="onTypeChange">
              <option v-for="t in dbTypes" :key="t.type" :value="t.type">
                {{ t.label }}{{ t.available ? '' : '（驱动未安装）' }}
              </option>
            </select>
          </div>
          <div v-if="form.db_type === 'sqlite'" class="field">
            <label>数据库文件路径</label>
            <input class="input" v-model="form.database" placeholder="D:/data/test.db" />
          </div>
          <template v-else>
            <div class="field-row">
              <div class="field col"><label>主机地址</label><input class="input" v-model="form.host" placeholder="127.0.0.1" /></div>
              <div class="field" style="width:110px"><label>端口</label><input class="input" v-model.number="form.port" type="number" /></div>
            </div>
            <div class="field" v-if="form.db_type !== 'oracle'">
              <label>数据库名</label>
              <input class="input" v-model="form.database" :placeholder="form.db_type === 'postgresql' ? 'postgres' : 'test_db'" />
            </div>
            <div class="field" v-if="form.db_type === 'oracle'">
              <label>DSN（可选，填了优先用）</label>
              <input class="input" v-model="form.dsn" placeholder="host:1521/service_name" />
            </div>
            <div class="field-row">
              <div class="field col"><label>用户名</label><input class="input" v-model="form.username" autocomplete="off" /></div>
              <div class="field col"><label>密码</label><input class="input" type="password" v-model="form.password" autocomplete="off" /></div>
            </div>
          </template>
          <div class="field">
            <label>连接超时（秒）</label>
            <input class="input" v-model.number="form.timeout" type="number" min="1" max="60" />
          </div>

          <div class="conn-actions">
            <button class="btn" @click="testConn" :disabled="testing">{{ testing ? '测试中...' : '🔗 测试连接' }}</button>
            <button class="btn" @click="saveConn">💾 保存连接</button>
          </div>
          <div v-if="testResult" class="result-note" :class="testResult.ok ? 'ok' : 'bad'">
            {{ testResult.ok ? '✓' : '✗' }} {{ testResult.message }}
            <span v-if="testResult.version">· {{ testResult.version }}</span>
            <span class="muted" v-if="testResult.elapsed_ms">{{ testResult.elapsed_ms }}ms</span>
          </div>

          <div class="driver-tip" v-if="currentType && !currentType.available">
            <div>{{ currentType.note || '该数据库驱动未安装' }}</div>
            <div v-if="currentType.pip_package" style="margin:8px 0">
              安装命令：<code>pip install {{ currentType.pip_package }}</code>
            </div>
            <button class="btn btn-sm btn-primary" v-if="currentType.pip_package" @click="installDriver"
              :disabled="installing">{{ installing ? '安装中（约10-60秒）...' : '⚡ 一键安装驱动' }}</button>
            <div v-if="installResult" class="result-note" :class="installResult.ok ? 'ok' : 'bad'" style="margin-top:10px">
              {{ installResult.ok ? '✓' : '✗' }} {{ installResult.message }}
            </div>
          </div>

          <div v-if="savedList.length" class="saved-list">
            <div class="saved-title">已保存的连接</div>
            <div v-for="(s, i) in savedList" :key="i" class="saved-item" @click="loadConn(i)">
              <span class="saved-name">{{ s.name }}</span>
              <span class="muted">{{ dbLabel(s.config.db_type) }}</span>
              <button class="icon-btn danger" @click.stop="removeConn(i)" title="删除">×</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel">
        <div class="panel-head">
          <h2>SQL 查询</h2>
          <div style="display:flex;gap:8px;align-items:center">
            <button class="btn btn-sm" @click="loadTables" :disabled="!connected">📋 表列表</button>
            <button class="btn btn-sm btn-primary" @click="runQuery" :disabled="!connected || running">{{ running ? '执行中...' : '▶ 执行' }}</button>
          </div>
        </div>
        <div class="panel-body">
          <div class="field">
            <label>SQL 语句</label>
            <textarea class="textarea sql-input" v-model="sql" placeholder="SELECT * FROM users LIMIT 20" spellcheck="false"></textarea>
          </div>
          <div class="query-opts">
            <label><input type="checkbox" v-model="allowWrite" /> 允许写操作（INSERT/UPDATE/DDL 建表改表，DROP 始终禁止）</label>
            <label>最多返回 <input class="input limit-in" type="number" v-model.number="limit" min="1" max="1000" /> 行</label>
          </div>
          <div v-if="!connected" class="empty" style="padding:26px">
            <div class="big">🔌</div>请先在左侧测试连接成功
          </div>
          <template v-else>
            <div v-if="queryResult" class="query-meta">
              <span class="badge" :class="queryResult.ok ? 'passed' : 'failed'">{{ queryResult.ok ? '执行成功' : '执行失败' }}</span>
              <span>{{ queryResult.row_count }} 行</span>
              <span v-if="queryResult.affected_rows !== undefined">影响 {{ queryResult.affected_rows }} 行</span>
              <span class="muted">{{ queryResult.elapsed_ms }}ms</span>
              <span v-if="queryResult.truncated" class="warn">结果已截断</span>
            </div>
            <div v-if="queryError" class="result-note bad">{{ queryError }}</div>
            <div v-if="queryResult && queryResult.rows && queryResult.rows.length" class="result-wrap">
              <table class="result-table">
                <thead><tr><th class="row-idx">#</th><th v-for="c in queryResult.columns" :key="c">{{ c }}</th></tr></thead>
                <tbody>
                  <tr v-for="(r, i) in queryResult.rows" :key="i">
                    <td class="row-idx">{{ i + 1 }}</td>
                    <td v-for="c in queryResult.columns" :key="c" :title="String(r[c])">{{ r[c] === null ? 'NULL' : r[c] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else-if="queryResult && queryResult.ok" class="empty" style="padding:24px">查询完成，无数据行</div>
          </template>
        </div>
      </div>

      <div class="panel" v-if="tables.length" style="margin-top:18px">
        <div class="panel-head"><h2>📋 表列表</h2><span class="muted">{{ tables.length }} 张表</span></div>
        <div class="panel-body">
          <div class="table-chips">
            <button v-for="t in tables" :key="t" class="table-chip" @click="sql = `SELECT * FROM ${t} LIMIT 20`">{{ t }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, notify } from '../api'
import { token } from '../auth'

const STORAGE_KEY = 'tef_db_connections'

const dbTypes = ref([])
const form = ref({ db_type: 'mysql', host: '127.0.0.1', port: 3306, database: '', username: '', password: '', dsn: '', timeout: 10 })
const testing = ref(false)
const running = ref(false)
const testResult = ref(null)
const connected = ref(false)
const sql = ref('')
const allowWrite = ref(false)
const limit = ref(200)
const queryResult = ref(null)
const queryError = ref('')
const tables = ref([])
const savedList = ref([])
const installing = ref(false)
const installResult = ref(null)

const currentType = computed(() => dbTypes.value.find(t => t.type === form.value.db_type))

function headers() {
  const h = { 'Content-Type': 'application/json' }
  if (token.value) h['Authorization'] = `Bearer ${token.value}`
  return h
}
function dbLabel(t) { return dbTypes.value.find(x => x.type === t)?.label || t }

async function post(path, body) {
  const resp = await fetch(path, { method: 'POST', headers: headers(), body: JSON.stringify(body) })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) throw new Error(data.detail || resp.statusText)
  return data
}

onMounted(async () => {
  try { dbTypes.value = await api('/api/db/types') } catch (e) { notify('加载数据库类型失败: ' + e.message, 'error') }
  loadSaved()
})

function onTypeChange() {
  const t = dbTypes.value.find(x => x.type === form.value.db_type)
  if (t) form.value.port = t.default_port
  connected.value = false
  testResult.value = null
}

async function installDriver() {
  if (!currentType.value?.pip_package) return
  installing.value = true
  installResult.value = null
  try {
    const r = await post(`/api/db/install-driver/${form.value.db_type}`, {})
    installResult.value = r
    if (r.ok) {
      notify('驱动安装成功，正在刷新...')
      dbTypes.value = await api('/api/db/types')  // 刷新驱动状态
    }
  } catch (e) { installResult.value = { ok: false, message: e.message } }
  finally { installing.value = false }
}

async function testConn() {
  testing.value = true
  testResult.value = null
  connected.value = false
  try {
    const r = await post('/api/db/test', form.value)
    testResult.value = r
    connected.value = r.ok
    if (r.ok) notify('连接成功')
  } catch (e) { testResult.value = { ok: false, message: e.message } }
  finally { testing.value = false }
}

async function runQuery() {
  if (!sql.value.trim()) { notify('请输入 SQL 语句', 'error'); return }
  running.value = true
  queryError.value = ''
  queryResult.value = null
  try {
    queryResult.value = await post('/api/db/query', { config: form.value, sql: sql.value, allow_write: allowWrite.value, limit: limit.value })
    if (!queryResult.value.ok) queryError.value = queryResult.value.message || '执行失败'
  } catch (e) { queryError.value = e.message }
  finally { running.value = false }
}

async function loadTables() {
  try {
    const r = await post('/api/db/tables', form.value)
    tables.value = r.tables || []
    notify(`已加载 ${tables.value.length} 张表`)
  } catch (e) { notify('加载表列表失败: ' + e.message, 'error') }
}

function loadSaved() {
  try { savedList.value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch (e) { savedList.value = [] }
}
function persist() { localStorage.setItem(STORAGE_KEY, JSON.stringify(savedList.value)) }
function saveConn() {
  const name = prompt('给这个连接起个名字：', `${dbLabel(form.value.db_type)} - ${form.value.host || 'local'}`)
  if (!name) return
  savedList.value.push({ name, config: { ...form.value } })
  persist()
  notify('连接已保存到本地浏览器')
}
function loadConn(i) {
  form.value = { ...savedList.value[i].config }
  connected.value = false
  testResult.value = null
  notify(`已载入「${savedList.value[i].name}」，请重新测试连接`)
}
function removeConn(i) {
  if (!confirm(`删除连接「${savedList.value[i].name}」？`)) return
  savedList.value.splice(i, 1)
  persist()
}
</script>

<style scoped>
.saved-count { font-size: 11px; color: var(--muted); }
.conn-actions { display: flex; gap: 8px; margin-top: 6px; }
.result-note {
  margin-top: 12px; padding: 9px 11px; border-radius: 8px; font-size: 12px; line-height: 1.6;
  word-break: break-all;
}
.result-note.ok { background: #e3f9e8; color: #12803a; border: 1px solid #bfe8cc; }
.result-note.bad { background: #fdeaf0; color: var(--danger); border: 1px solid #f5c4d0; }
.result-note .muted { margin-left: 6px; }
.driver-tip { margin-top: 12px; padding: 10px 12px; border-radius: 8px; background: #fff5e3; color: var(--warn); font-size: 12px; }
.driver-tip code { background: rgba(0,0,0,.05); padding: 1px 5px; border-radius: 4px; }
.saved-list { margin-top: 18px; border-top: 1px solid var(--border); padding-top: 14px; }
.saved-title { font-size: 12px; font-weight: 600; color: var(--muted); margin-bottom: 8px; }
.saved-item {
  display: flex; align-items: center; gap: 8px; padding: 7px 9px; border-radius: 7px;
  cursor: pointer; font-size: 12.5px; border: 1px solid transparent;
}
.saved-item:hover { background: var(--panel-2); border-color: var(--border); }
.saved-name { font-weight: 500; flex: 1; }
.saved-item .muted { font-size: 11px; }
.icon-btn { width: 22px; height: 22px; border: 1px solid var(--border); background: var(--panel); border-radius: 5px; cursor: pointer; color: var(--muted); line-height: 1; }
.icon-btn.danger:hover { color: var(--danger); border-color: var(--danger); }

.sql-input { font-family: "JetBrains Mono", Consolas, Monaco, monospace; font-size: 12.5px; min-height: 96px; line-height: 1.6; }
.query-opts { display: flex; gap: 22px; align-items: center; margin: 10px 0 14px; font-size: 12px; color: var(--muted); flex-wrap: wrap; }
.query-opts label { display: flex; align-items: center; gap: 6px; }
.limit-in { width: 70px; padding: 5px 8px; }
.query-meta { display: flex; gap: 12px; align-items: center; font-size: 12px; margin-bottom: 10px; flex-wrap: wrap; }
.query-meta .warn { color: var(--warn); }
.result-wrap { max-height: 440px; overflow: auto; border: 1px solid var(--border); border-radius: 8px; }
.result-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.result-table th, .result-table td { padding: 7px 10px; border-bottom: 1px solid var(--border); text-align: left; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.result-table th { position: sticky; top: 0; z-index: 1; background: var(--panel-2); font-size: 11px; }
.result-table .row-idx { width: 36px; color: var(--muted); text-align: center; background: var(--panel-2); }
.table-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.table-chip {
  padding: 5px 11px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel);
  font-size: 12px; cursor: pointer; font-family: "JetBrains Mono", Consolas, monospace;
}
.table-chip:hover { border-color: var(--primary); color: var(--primary); }
</style>
