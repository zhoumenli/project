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
          <button class="btn" @click="openSuiteDialog">📑 测试集</button>
          <button class="btn btn-primary" @click="openCaseDialog()">＋ 新建用例</button>
        </div>
        <div style="padding:0 18px 18px">
          <table>
            <thead><tr><th style="width:42%">用例标题</th><th>类型</th><th>优先级</th><th>标签</th><th>更新时间</th><th style="width:150px">操作</th></tr></thead>
            <tbody>
              <tr v-for="c in cases" :key="c.id">
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
              <tr v-if="!cases.length"><td colspan="6"><div class="empty">该目录下暂无用例，点击右上角新建</div></td></tr>
            </tbody>
          </table>
        </div>
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

const folders = ref([])
const cases = ref([])
const suites = ref([])
const selectedFolder = ref(null)
const keyword = ref('')
const typeFilter = ref('')
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
}
function selectFolder(f) { selectedFolder.value = f.id; loadCases() }
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
</style>
