<template>
  <div>
    <div class="row" style="align-items:flex-start">
    <!-- folder tree -->
    <div class="panel" style="width:250px;flex-shrink:0">
      <div class="panel-head"><h2>用例目录</h2><button class="btn btn-sm" @click="addFolder">＋</button></div>
      <div class="panel-body" style="padding:10px">
        <div v-for="f in rootFolders" :key="f.id">
          <div class="tree-item" :class="{active: selectedFolder===f.id}" @click="selectFolder(f)">
            <span @dblclick.stop="renameFolder(f)">📁 {{ f.name }}</span>
            <span class="muted" style="font-size:11px">{{ f.case_count }}</span>
          </div>
          <div class="tree-children">
            <div v-for="c in childrenOf(f.id)" :key="c.id" class="tree-item" :class="{active: selectedFolder===c.id}" @click="selectFolder(c)">
              <span @dblclick.stop="renameFolder(c)">📂 {{ c.name }}</span>
              <span class="muted" style="font-size:11px">{{ c.case_count }}</span>
            </div>
          </div>
        </div>
        <div v-if="!folders.length" class="empty" style="padding:20px 0">暂无目录</div>
      </div>
    </div>

    <!-- case list -->
    <div class="col">
      <div class="panel">
        <div class="toolbar" style="padding:16px 18px;margin:0">
          <input class="input" v-model="keyword" placeholder="搜索用例标题..." @keyup.enter="loadCases" />
          <select class="select" v-model="typeFilter" style="width:130px" @change="loadCases">
            <option value="">全部类型</option><option value="api">接口</option><option value="ui">UI</option><option value="manual">手工</option>
          </select>
          <button class="btn" @click="loadCases">🔍 查询</button>
          <div class="spacer"></div>
          <select class="select" v-model="exportFormat" style="width:120px" title="导出文件格式">
            <option value="xlsx">Excel (.xlsx)</option>
            <option value="csv">CSV (.csv)</option>
          </select>
          <button class="btn" @click="exportCases" :disabled="exporting" title="按当前筛选条件导出用例">{{ exporting ? '导出中...' : '⬇ 导出' }}</button>
          <button class="btn" @click="openAutoGen" title="按接口自动化框架模板生成可运行的 pytest 项目">🤖 自动化</button>
          <button class="btn" @click="openSuiteDialog">📑 测试集</button>
          <button class="btn btn-primary" @click="openCaseDialog()">＋ 新建用例</button>
        </div>
        <div v-if="selectedIds.size" class="batch-bar">
          <span class="batch-info">已选 <b>{{ selectedIds.size }}</b> 条（接口 {{ selApiCount }} 条）</span>
          <button class="btn btn-sm" @click="batchExport">⬇ 批量导出</button>
          <button class="btn btn-sm" @click="batchAutoGen">🤖 生成自动化</button>
          <button class="btn btn-sm btn-danger" @click="batchDelete">🗑 批量删除</button>
          <button class="btn btn-sm" @click="clearSel">取消选择</button>
        </div>
        <div class="case-scroll" style="padding:0 18px 18px">
          <table>
            <thead><tr>
              <th style="width:36px"><input type="checkbox" class="row-check" :checked="allSelected" :indeterminate="someSelected && !allSelected" @change="toggleAll" title="全选/全不选" /></th>
              <th style="width:42%">用例标题</th><th>类型</th><th>优先级</th><th>标签</th><th>更新时间</th><th style="width:150px">操作</th>
            </tr></thead>
            <tbody>
              <tr v-for="c in pagedCases" :key="c.id" :class="{ 'row-checked': selectedIds.has(c.id) }">
                <td><input type="checkbox" class="row-check" :checked="selectedIds.has(c.id)" @change="toggleRow(c)" /></td>
                <td><b>{{ c.title }}</b><div class="muted" style="font-size:11px">#{{ c.id }} {{ c.url || c.expected.slice(0,30) }}</div></td>
                <td><span class="tag">{{ typeName(c.case_type) }}</span></td>
                <td><span class="badge" :class="c.priority">{{ c.priority }}</span></td>
                <td><span v-for="t in c.tags" :key="t" class="tag gray">{{ t }}</span></td>
                <td class="muted" style="font-size:12px">{{ fmtTime(c.updated_at) }}</td>
                <td>
                  <button class="btn btn-sm" @click="openCaseDialog(c)">编辑</button>
                  <button class="btn btn-sm btn-danger" @click="delCase(c)">删除</button>
                </td>
              </tr>
              <tr v-if="!cases.length"><td colspan="7"><div class="empty">该目录下暂无用例，点击右上角新建</div></td></tr>
            </tbody>
          </table>
        </div>
        <div style="padding:0 18px 14px"><TablePager v-model:page="casePage" v-model:size="casePageSize" :total="cases.length" /></div>
      </div>
    </div>
  </div>

  <!-- case editor modal -->
  <div v-if="caseDialog" class="modal-mask" @click.self="caseDialog=false">
    <div class="modal wide">
      <div class="modal-head">{{ editing?.id ? '编辑用例' : '新建用例' }}<button class="close-x" @click="caseDialog=false">×</button></div>
      <div class="modal-body">
        <div class="tabs">
          <div v-for="t in ['basic','api','ui']" :key="t" class="tab" :class="{active:tab===t}" @click="tab=t">{{ {basic:'基本信息',api:'接口配置',ui:'UI 步骤'}[t] }}</div>
        </div>
        <div v-if="tab==='basic'">
          <div class="field-row">
            <div class="field col"><label>用例标题 *</label><input class="input" v-model="form.title" placeholder="请输入用例标题" /></div>
            <div class="field" style="width:130px"><label>类型</label><select class="select" v-model="form.case_type"><option value="api">接口</option><option value="ui">UI 自动化</option><option value="manual">手工</option></select></div>
            <div class="field" style="width:110px"><label>优先级</label><select class="select" v-model="form.priority"><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select></div>
          </div>
          <div class="field"><label>标签（逗号分隔）</label><input class="input" v-model="tagsStr" placeholder="如：登录,冒烟" /></div>
          <div class="field"><label>所属目录</label><select class="select" v-model="form.folder_id"><option v-for="f in allFolders" :key="f.id" :value="f.id">{{ f.name }}</option></select></div>
          <div class="field"><label>前置条件</label><textarea class="textarea" v-model="form.precondition"></textarea></div>
          <div class="field" v-if="form.case_type==='manual'"><label>测试步骤</label><textarea class="textarea" v-model="form.steps"></textarea></div>
          <div class="field"><label>预期结果</label><textarea class="textarea" v-model="form.expected"></textarea></div>
        </div>
        <div v-if="tab==='api'">
          <div class="field-row">
            <div class="field" style="width:130px"><label>方法</label><select class="select" v-model="form.method"><option>GET</option><option>POST</option><option>PUT</option><option>DELETE</option><option>PATCH</option></select></div>
            <div class="field col"><label>URL（支持双花括号变量）</label><input class="input" v-model="form.url" placeholder="/api/login 或 http://..." /></div>
          </div>
          <div class="field"><label>请求头（JSON）</label><textarea class="textarea" v-model="headersStr" placeholder='{"Content-Type":"application/json"}'></textarea></div>
          <div class="field"><label>请求体</label><textarea class="textarea" v-model="form.body" placeholder='{"username":"admin"}'></textarea></div>
          <div class="field">
            <label>断言规则</label>
            <div v-for="(a,i) in form.assertions" :key="i" class="assert-row">
              <select class="select" v-model="a.type" style="width:90px"><option value="status">状态码</option><option value="json">JSON字段</option><option value="header">响应头</option><option value="body">响应体</option></select>
              <input class="input" v-if="a.type==='json'||a.type==='header'" v-model="a.key" placeholder="字段路径" style="width:110px" />
              <select class="select" v-model="a.op" style="width:85px"><option value="eq">=</option><option value="ne">≠</option><option value="contains">包含</option><option value="gt">&gt;</option><option value="gte">≥</option><option value="lt">&lt;</option><option value="exists">存在</option><option value="regex">正则</option></select>
              <input class="input" v-model="a.value" placeholder="期望值" style="flex:1" />
              <button class="btn btn-sm btn-danger" @click="form.assertions.splice(i,1)">×</button>
            </div>
            <button class="btn btn-sm" @click="form.assertions.push({type:'status',op:'eq',key:'',value:'200'})">＋ 添加断言</button>
          </div>
          <div class="field">
            <label>变量提取（供后续用例使用）</label>
            <div v-for="(e,i) in form.extractors" :key="i" class="assert-row">
              <input class="input" v-model="e.name" placeholder="变量名" style="width:100px" />
              <select class="select" v-model="e.source" style="width:90px"><option value="json">JSON</option><option value="header">响应头</option><option value="body">响应体</option></select>
              <input class="input" v-model="e.key" placeholder="字段路径，如 data.token" style="flex:1" />
              <button class="btn btn-sm btn-danger" @click="form.extractors.splice(i,1)">×</button>
            </div>
            <button class="btn btn-sm" @click="form.extractors.push({name:'',source:'json',key:''})">＋ 添加提取</button>
          </div>
        </div>
        <div v-if="tab==='ui'">
          <div class="muted" style="font-size:12px;margin-bottom:10px">编排 Web 自动化步骤（JSON 数组）。支持动作：goto / click / fill / assert_visible / wait / screenshot</div>
          <textarea class="textarea" v-model="form.steps" style="min-height:220px;font-family:Consolas,monospace;font-size:12px" placeholder='[{"action":"goto","target":"https://example.com"},{"action":"fill","target":"#username","value":"admin"}]'></textarea>
        </div>
      </div>
      <div class="modal-foot"><button class="btn" @click="caseDialog=false">取消</button><button class="btn btn-primary" @click="saveCase">保存</button></div>
    </div>
  </div>

  <!-- autogen dialog -->
  <div v-if="autoGenDialog" class="modal-mask" @click.self="autoGenDialog=false">
    <div class="modal">
      <div class="modal-head">生成接口自动化项目<button class="close-x" @click="autoGenDialog=false">×</button></div>
      <div class="modal-body">
        <div class="field"><label>生成范围</label>
          <div class="muted" style="font-size:13px">{{ autoGenScope }}</div>
        </div>
        <div class="field"><label>接口基础地址（BASE_URL）</label>
          <input class="input" v-model="autoGenBase" placeholder="http://127.0.0.1:9001" />
        </div>
        <div class="muted" style="font-size:12px">按接口自动化框架模板（pytest + requests + allure 数据驱动）生成完整可运行项目：
          config.py / caseData/data.yaml / testcase/&lt;模块&gt;/test_xxx.py，断言与变量提取自动转换，zip 下载解压后
          <code>pip install -r requirements.txt</code> 即可 <code>pytest</code> 运行。仅生成接口类型用例。</div>
      </div>
      <div class="modal-foot">
        <button class="btn" @click="autoGenDialog=false">取消</button>
        <button class="btn btn-primary" @click="doAutoGen" :disabled="autoGenLoading">{{ autoGenLoading ? '生成中...' : '🤖 生成并下载' }}</button>
      </div>
    </div>
  </div>

  <!-- suite dialog -->
  <div v-if="suiteDialog" class="modal-mask" @click.self="suiteDialog=false">
    <div class="modal">
      <div class="modal-head">测试集管理<button class="close-x" @click="suiteDialog=false">×</button></div>
      <div class="modal-body">
        <div class="field-row">
          <div class="field col"><label>新建测试集名称</label><input class="input" v-model="newSuiteName" placeholder="如：接口冒烟测试集" /></div>
          <div class="field" style="width:150px;align-self:flex-end"><button class="btn btn-primary" style="width:100%" @click="createSuite">创建</button></div>
        </div>
        <div v-if="suites.length">
          <div v-for="s in suites" :key="s.id" class="suite-item">
            <div><b>{{ s.name }}</b> <span class="muted">（{{ s.case_ids.length }} 个用例）</span></div>
            <button class="btn btn-sm btn-danger" @click="delSuite(s)">删除</button>
          </div>
        </div>
        <div v-else class="empty">暂无测试集</div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { api, currentProject, notify } from '../api'
import { token } from '../auth'
import TablePager from '../components/TablePager.vue'

const folders = ref([])
const cases = ref([])
const suites = ref([])
const selectedFolder = ref(null)
const keyword = ref('')
const typeFilter = ref('')
const exportFormat = ref('xlsx')
const exporting = ref(false)
const autoGenDialog = ref(false)
const autoGenBase = ref('http://127.0.0.1:9001')
const autoGenLoading = ref(false)
const autoGenIds = ref([])   // 勾选模式：指定用例id；空数组=按筛选范围
const selectedIds = ref(new Set())
const casePage = ref(1)
const casePageSize = ref(30)
const pagedCases = computed(() => {
  const start = (casePage.value - 1) * casePageSize.value
  return cases.value.slice(start, start + casePageSize.value)
})

const allSelected = computed(() => pagedCases.value.length > 0 && pagedCases.value.every(c => selectedIds.value.has(c.id)))
const someSelected = computed(() => selectedIds.value.size > 0)
const selApiCount = computed(() => cases.value.filter(c => selectedIds.value.has(c.id) && c.case_type === 'api').length)

function toggleRow(c) {
  const s = new Set(selectedIds.value)
  s.has(c.id) ? s.delete(c.id) : s.add(c.id)
  selectedIds.value = s
}
function toggleAll() {
  // 全选按钮只针对当前页的行
  const pageIds = pagedCases.value.map(c => c.id)
  const allOn = pageIds.every(id => selectedIds.value.has(id))
  const s = new Set(selectedIds.value)
  allOn ? pageIds.forEach(id => s.delete(id)) : pageIds.forEach(id => s.add(id))
  selectedIds.value = s
}
function clearSel() { selectedIds.value = new Set() }

const autoGenScope = computed(() => {
  if (autoGenIds.value.length) {
    return `已勾选 ${autoGenIds.value.length} 条用例，其中接口用例 ${autoGenApiCount.value} 条将参与生成`
  }
  const apiCount = cases.value.filter(c => c.case_type === 'api').length
  const scope = selectedFolder.value ? '当前目录' : '当前项目全部目录'
  return `${scope}下共 ${cases.value.length} 条用例，其中接口用例 ${apiCount} 条将参与生成`
})
const autoGenApiCount = computed(() => {
  if (!autoGenIds.value.length) return 0
  return cases.value.filter(c => autoGenIds.value.includes(c.id) && c.case_type === 'api').length
})
const caseDialog = ref(false)
const suiteDialog = ref(false)
const editing = ref(null)
const tab = ref('basic')
const tagsStr = ref('')
const headersStr = ref('{}')
const newSuiteName = ref('')
const form = ref(blankForm())

function blankForm() {
  return { folder_id: null, title: '', case_type: 'api', priority: 'P2', tags: [],
    precondition: '', steps: '', expected: '', method: 'GET', url: '', headers: {},
    body: '', assertions: [], extractors: [] }
}

const rootFolders = computed(() => folders.value.filter(f => !f.parent_id))
const allFolders = computed(() => folders.value)
function childrenOf(pid) { return folders.value.filter(f => f.parent_id === pid) }

watch(() => currentProject.value?.id, () => { selectedFolder.value = null; loadAll() })
onMounted(loadAll)

async function loadAll() {
  if (!currentProject.value) return
  folders.value = await api(`/api/folders?project_id=${currentProject.value.id}`)
  await loadCases()
  loadSuites()
}
async function loadCases() {
  if (!currentProject.value) return
  let url = `/api/cases?project_id=${currentProject.value.id}`
  if (selectedFolder.value) url += `&folder_id=${selectedFolder.value}`
  if (typeFilter.value) url += `&case_type=${typeFilter.value}`
  if (keyword.value) url += `&keyword=${encodeURIComponent(keyword.value)}`
  cases.value = await api(url)
  selectedIds.value = new Set()   // 列表刷新后清空勾选
  casePage.value = 1              // 数据变化回到第一页
}
function selectFolder(f) { selectedFolder.value = f.id; loadCases() }

async function exportCases() {
  if (!currentProject.value) return
  if (!cases.value.length) { notify('当前筛选条件下没有可导出的用例', 'error'); return }
  exporting.value = true
  try {
    let url = `/api/cases/export?format=${exportFormat.value}`
    if (selectedFolder.value) url += `&folder_id=${selectedFolder.value}`
    else url += `&project_id=${currentProject.value.id}`
    if (typeFilter.value) url += `&case_type=${typeFilter.value}`
    if (keyword.value) url += `&keyword=${encodeURIComponent(keyword.value)}`
    const headers = {}
    if (token.value) headers['Authorization'] = `Bearer ${token.value}`
    const resp = await fetch(url, { headers })
    if (!resp.ok) { let m = resp.statusText; try { m = (await resp.json()).detail || m } catch (e) {} throw new Error(m) }
    const blob = await resp.blob()
    const cd = resp.headers.get('Content-Disposition') || ''
    let name = `用例导出.${exportFormat.value}`
    const m = cd.match(/filename\*=UTF-8''([^;]+)/)
    if (m) { try { name = decodeURIComponent(m[1]) } catch (e) {} }
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(a.href)
    notify(`已导出 ${name}`)
  } catch (e) { notify('导出失败：' + e.message, 'error') }
  finally { exporting.value = false }
}

function openAutoGen() {
  if (!cases.value.some(c => c.case_type === 'api')) { notify('当前范围内没有接口用例，无法生成自动化项目', 'error'); return }
  autoGenIds.value = []
  autoGenDialog.value = true
}

function batchAutoGen() {
  const ids = [...selectedIds.value]
  if (!cases.value.some(c => ids.includes(c.id) && c.case_type === 'api')) {
    notify('勾选的用例中没有接口用例，无法生成自动化项目', 'error'); return
  }
  autoGenIds.value = ids
  autoGenDialog.value = true
}

async function batchExport() {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  exporting.value = true
  try {
    const url = `/api/cases/export?format=${exportFormat.value}&case_ids=${ids.join(',')}`
    const headers = {}
    if (token.value) headers['Authorization'] = `Bearer ${token.value}`
    const resp = await fetch(url, { headers })
    if (!resp.ok) { let m = resp.statusText; try { m = (await resp.json()).detail || m } catch (e) {} throw new Error(m) }
    const blob = await resp.blob()
    const cd = resp.headers.get('Content-Disposition') || ''
    let name = `用例导出.${exportFormat.value}`
    const m = cd.match(/filename\*=UTF-8''([^;]+)/)
    if (m) { try { name = decodeURIComponent(m[1]) } catch (e) {} }
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(a.href)
    notify(`已导出 ${ids.length} 条用例 → ${name}`)
  } catch (e) { notify('导出失败：' + e.message, 'error') }
  finally { exporting.value = false }
}

async function batchDelete() {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  if (!confirm(`确定批量删除选中的 ${ids.length} 条用例？此操作不可恢复！`)) return
  try {
    const r = await api('/api/cases/batch-delete', { method: 'POST', body: { ids } })
    notify(`已删除 ${r.deleted} 条用例`)
    loadCases()
  } catch (e) { notify('删除失败：' + e.message, 'error') }
}

async function doAutoGen() {
  if (!currentProject.value) return
  autoGenLoading.value = true
  try {
    const body = {
      project_id: currentProject.value.id,
      base_url: autoGenBase.value.trim() || 'http://127.0.0.1:9001',
    }
    if (autoGenIds.value.length) body.case_ids = autoGenIds.value
    else {
      if (selectedFolder.value) body.folder_id = selectedFolder.value
      if (keyword.value) body.keyword = keyword.value
    }
    const headers = { 'Content-Type': 'application/json' }
    if (token.value) headers['Authorization'] = `Bearer ${token.value}`
    const resp = await fetch('/api/cases/autogen', { method: 'POST', headers, body: JSON.stringify(body) })
    if (!resp.ok) { let m = resp.statusText; try { m = (await resp.json()).detail || m } catch (e) {} throw new Error(m) }
    const blob = await resp.blob()
    const cd = resp.headers.get('Content-Disposition') || ''
    let name = '接口自动化项目.zip'
    const m = cd.match(/filename\*=UTF-8''([^;]+)/)
    if (m) { try { name = decodeURIComponent(m[1]) } catch (e) {} }
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(a.href)
    autoGenDialog.value = false
    autoGenIds.value = []
    notify(`已生成 ${name}，解压后 pip install -r requirements.txt 即可运行`)
  } catch (e) { notify('生成失败：' + e.message, 'error') }
  finally { autoGenLoading.value = false }
}
async function loadSuites() {
  if (!currentProject.value) return
  suites.value = await api(`/api/suites?project_id=${currentProject.value.id}`)
}

async function addFolder() {
  const name = prompt('输入目录名称：')
  if (!name || !currentProject.value) return
  await api('/api/folders', { method: 'POST', body: { project_id: currentProject.value.id, name } })
  notify('目录已创建'); loadAll()
}
async function renameFolder(f) {
  const name = prompt('重命名目录：', f.name)
  if (!name) return
  // no update endpoint: delete + recreate loses children; simple approach via direct PUT-less save
  notify('重命名功能需后端 PUT 接口，本版本可先删除重建', 'error')
}

function openCaseDialog(c) {
  editing.value = c || null
  if (c) {
    form.value = JSON.parse(JSON.stringify(c))
    tagsStr.value = (c.tags || []).join(',')
    headersStr.value = JSON.stringify(c.headers || {}, null, 2)
  } else {
    form.value = blankForm()
    form.value.folder_id = selectedFolder.value || folders.value[0]?.id
    tagsStr.value = ''; headersStr.value = '{}'
  }
  tab.value = 'basic'
  caseDialog.value = true
}
async function saveCase() {
  if (!form.value.title?.trim()) { notify('请填写用例标题', 'error'); return }
  try {
    form.value.tags = tagsStr.value.split(',').map(s=>s.trim()).filter(Boolean)
    form.value.headers = JSON.parse(headersStr.value || '{}')
    if (!form.value.folder_id) { notify('请选择所属目录', 'error'); return }
    if (editing.value?.id) {
      await api(`/api/cases/${editing.value.id}`, { method: 'PUT', body: form.value })
      notify('用例已更新')
    } else {
      await api('/api/cases', { method: 'POST', body: form.value })
      notify('用例已创建')
    }
    caseDialog.value = false; loadAll()
  } catch (e) { notify('保存失败：' + e.message, 'error') }
}
async function delCase(c) {
  if (!confirm(`确定删除用例「${c.title}」？`)) return
  await api(`/api/cases/${c.id}`, { method: 'DELETE' })
  notify('已删除'); loadCases()
}

async function createSuite() {
  if (!newSuiteName.value.trim() || !currentProject.value) return
  await api('/api/suites', { method: 'POST', body: {
    project_id: currentProject.value.id, name: newSuiteName.value,
    case_ids: cases.value.map(c=>c.id),
  }})
  newSuiteName.value = ''; notify('测试集已创建'); loadSuites()
}
async function delSuite(s) {
  if (!confirm(`删除测试集「${s.name}」？`)) return
  await api(`/api/suites/${s.id}`, { method: 'DELETE' }); loadSuites()
}

function typeName(t) { return ({api:'接口',ui:'UI',manual:'手工'})[t] || t }
function fmtTime(t) { return t ? t.replace('T',' ').slice(0,16) : '-' }
</script>

<style scoped>
.assert-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
.suite-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border); }
/* 表格容器内滚动 + 表头吸顶：长列表滚动时全选框始终可见，随时可全部取消勾选 */
.case-scroll { max-height: calc(100vh - 240px); overflow: auto; }
.case-scroll table :deep(thead th) {
  position: sticky; top: 0; z-index: 2;
  background: #f8f9fd;
  box-shadow: 0 1px 0 var(--border);
}
.batch-bar { display: flex; align-items: center; gap: 10px; margin: 0 18px 12px; padding: 10px 14px; background: var(--primary-light, #eef0ff); border: 1px solid var(--border); border-radius: 10px; animation: fadeIn .2s ease; }
.batch-info { font-size: 13px; }
.row-check { cursor: pointer; width: 15px; height: 15px; accent-color: var(--primary, #5b6bf5); }
.row-checked { background: rgba(91, 107, 245, 0.06); }
</style>
