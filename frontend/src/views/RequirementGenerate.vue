<template>
  <div>
    <!-- toolbar -->
    <div class="toolbar">
      <div class="tabs" style="margin:0;border:none">
        <div class="tab" :class="{active: view==='create'}" @click="view='create'">🚀 生成用例</div>
        <div class="tab" :class="{active: view==='history'}" @click="view='history'; loadHistory()">📜 历史记录 <span class="badge" style="margin-left:4px">{{ history.length }}</span></div>
      </div>
      <div class="spacer"></div>
      <span class="muted" style="font-size:12px">上传需求文档，自动全方位生成测试用例</span>
    </div>

    <!-- ============ CREATE VIEW ============ -->
    <div v-if="view==='create'" class="row" style="align-items:flex-start">
      <div class="col" style="flex:1.1">
        <div class="panel">
          <div class="panel-head"><h2>① 上传需求文档</h2><span class="muted" style="font-size:12px">支持多格式</span></div>
          <div class="panel-body">
            <div class="dropzone" :class="{dragover: dragging}" @dragover.prevent="dragging=true" @dragleave.prevent="dragging=false" @drop.prevent="onDrop" @click="$refs.fileInput.click()">
              <input ref="fileInput" type="file" style="display:none" @change="onFile" :accept="acceptTypes" />
              <div class="dz-icon">📄</div>
              <div class="dz-title">{{ file ? file.name : '点击或拖拽上传需求文档' }}</div>
              <div class="dz-sub" v-if="!file">支持 PDF / Word / Excel / PPT / TXT / Markdown / 图片 等，最大 20MB</div>
              <div class="dz-sub" v-else>{{ fmtSize(file.size) }} · 点击更换文件</div>
              <div v-if="uploading" class="dz-progress"><div class="bar" :style="{width: progress+'%'}"></div></div>
            </div>
            <div class="format-grid">
              <div v-for="f in formats" :key="f.label" class="format-chip"><span>{{ f.icon }}</span>{{ f.label }}</div>
            </div>
            <div class="field" style="margin-top:16px">
              <label>用例类型（可多选）</label>
              <div class="ctype-row">
                <label class="ctype" :class="{checked: caseTypes.includes('functional')}">
                  <input type="checkbox" value="functional" v-model="caseTypes" />
                  <div><b>功能测试用例</b><span>正向 / 边界 / 异常 / 状态流转等，操作步骤描述，人工执行</span></div>
                </label>
                <label class="ctype" :class="{checked: caseTypes.includes('api')}">
                  <input type="checkbox" value="api" v-model="caseTypes" />
                  <div><b>接口测试用例</b><span>自动提取需求中的接口，带方法 / URL / 请求体 / 断言，导入后可直接执行</span></div>
                </label>
              </div>
              <div class="tpl-tip" v-if="!caseTypes.length" style="color:var(--danger)">请至少选择一种用例类型</div>
            </div>
            <div class="field">
              <label>生成引擎</label>
              <select class="select" v-model="backend">
                <option value="local">本地智能引擎（离线、免费、开箱即用）</option>
                <option value="llm">大模型引擎（需配置 LLM_API_KEY，未配置自动回退本地）</option>
              </select>
            </div>
            <div class="field">
              <label>生成维度（全选 = 全方位覆盖）</label>
              <div class="dim-grid">
                <label v-for="d in allDims" :key="d" class="dim"><input type="checkbox" :value="d" v-model="selectedDims" /> {{ d }}</label>
              </div>
            </div>
            <div class="field">
              <label>输出语言（用例正文）</label>
              <div class="radio-row">
                <label class="radio"><input type="radio" value="zh" v-model="language" /> 中文</label>
                <label class="radio"><input type="radio" value="en" v-model="language" /> English</label>
              </div>
            </div>
            <div class="field">
              <label>输出模板（自定义用例格式）</label>
              <textarea class="textarea tpl mono" v-model="outputTemplate" rows="6"></textarea>
              <div class="tpl-tip">可用占位符：<code>{编号}</code><code>{标题}</code><code>{维度}</code><code>{优先级}</code><code>{类型}</code><code>{前置条件}</code><code>{步骤}</code><code>{预期结果}</code><code>{标签}</code><code>{风险}</code>（也支持英文别名如 {no} {title} {steps} {expected}）</div>
              <button class="btn btn-sm" style="margin-top:6px" @click="resetTemplate">恢复默认模板</button>
            </div>
            <button class="btn btn-primary" style="width:100%;padding:11px" @click="generate" :disabled="!file || generating || !caseTypes.length">
              {{ generating ? '⚙️ 正在解析文档并生成用例...' : `✨ 一键生成${caseTypes.length === 1 ? (caseTypes[0] === 'api' ? '接口测试用例' : '功能测试用例') : '测试用例（功能 + 接口）'}` }}
            </button>
          </div>
        </div>
      </div>

      <div class="col" style="flex:1.4">
        <div class="panel">
          <div class="panel-head">
            <h2>② 生成结果</h2>
            <div v-if="result" class="result-actions">
              <span class="badge passed">{{ result.cases_count }} 条用例</span>
              <select class="select" v-model="exportFormat" style="width:130px" title="导出文件格式">
                <option value="xlsx">Excel (.xlsx)</option>
                <option value="docx">Word (.docx)</option>
                <option value="md">Markdown (.md)</option>
                <option value="csv">CSV (.csv)</option>
                <option value="json">JSON (.json)</option>
                <option value="txt">TXT (.txt)</option>
                <option value="html">HTML (.html)</option>
              </select>
              <button class="btn btn-sm" @click="exportResult" :disabled="exporting">{{ exporting ? '导出中...' : '⬇ 导出' }}</button>
              <button class="btn btn-sm btn-primary" @click="openImport">📥 导入用例中心</button>
            </div>
          </div>
          <div class="panel-body" style="max-height:640px;overflow:auto">
            <div v-if="!result" class="empty"><div class="big">✨</div>上传文档并点击生成，结果将在这里展示</div>
            <template v-else>
              <div class="gen-meta">
                <div><span class="muted">文档：</span><b>{{ result.doc_name }}</b></div>
                <div><span class="muted">格式：</span>{{ result.doc_format }} · <span class="muted">引擎：</span>{{ result.backend === 'llm' ? '大模型' : '本地智能' }} · <span class="muted">语言：</span>{{ result.cases?.[0]?.language === 'en' ? 'English' : '中文' }}</div>
                <div><span class="muted">覆盖维度：</span><span v-for="d in result.dimensions" :key="d" class="tag">{{ d }}</span></div>
              </div>
              <div class="dim-filter">
                <span class="muted" style="font-size:12px">筛选：</span>
                <select class="select" v-model="filterDim" style="width:150px"><option value="">全部维度</option><option v-for="d in result.dimensions" :key="d" :value="d">{{ d }}</option></select>
                <select class="select" v-model="filterPriority" style="width:100px"><option value="">全部优先级</option><option>P0</option><option>P1</option><option>P2</option></select>
                <span class="muted" style="font-size:12px;margin-left:auto">显示 {{ filteredCases.length }} 条</span>
              </div>
              <div class="case-preview-list">
                <div v-for="c in filteredCases" :key="c.no" class="pcase">
                  <div class="pcase-head" @click="toggleExpand(c.no)">
                    <span class="badge" :class="c.priority" style="flex-shrink:0">{{ c.priority }}</span>
                    <span class="pcase-title">{{ c.title }}</span>
                    <span class="tag" style="flex-shrink:0">{{ c.dimension }}</span>
                    <span class="tag gray" style="flex-shrink:0">{{ typeName(c.case_type) }}</span>
                    <span style="margin-left:auto;color:var(--muted);font-size:12px;flex-shrink:0">{{ expanded[c.no] ? '收起' : '展开' }}</span>
                  </div>
                  <div v-if="expanded[c.no]" class="pcase-body">
                    <div class="fmt-view">
                      <div class="fmt-view-head">
                        <span class="muted">按模板输出</span>
                        <button class="btn btn-sm" @click="copyText(c.formatted)">复制</button>
                      </div>
                      <pre class="fmt-text">{{ c.formatted }}</pre>
                    </div>
                    <details class="struct-view">
                      <summary>查看结构化字段（用于导入用例中心）</summary>
                      <div v-if="c.method" class="api-line">
                        <b>接口：</b>
                        <span class="tag method">{{ c.method }}</span>
                        <code class="api-url">{{ c.url }}</code>
                      </div>
                      <div v-if="c.assertions?.length"><b>断言：</b><span v-for="(a,i) in c.assertions" :key="i" class="tag gray">{{ a.type }} {{ a.key ? a.key + ' ' : '' }}{{ a.op }} {{ a.value }}</span></div>
                      <div v-if="c.risk" class="risk">🎯 {{ c.risk }}</div>
                      <div><b>前置条件：</b>{{ c.precondition }}</div>
                      <div><b>步骤：</b><pre class="code" style="white-space:pre-wrap">{{ c.steps }}</pre></div>
                      <div><b>预期结果：</b>{{ c.expected }}</div>
                      <div v-if="c.tags?.length"><span v-for="t in c.tags" :key="t" class="tag gray">{{ t }}</span></div>
                    </details>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ HISTORY VIEW ============ -->
    <div v-else class="panel">
      <div class="panel-head"><h2>生成历史记录</h2><button class="btn btn-sm" @click="loadHistory">🔄 刷新</button></div>
      <div class="panel-body">
        <table>
          <thead><tr><th>ID</th><th>文档名称</th><th>格式</th><th>用例数</th><th>引擎</th><th>状态</th><th>生成时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="h in pagedHistory" :key="h.id">
              <td><b>#{{ h.id }}</b></td>
              <td>📄 {{ h.doc_name }}</td>
              <td><span class="tag gray">{{ h.doc_format }}</span></td>
              <td><b>{{ h.cases_count }}</b> 条</td>
              <td>{{ h.backend === 'llm' ? '大模型' : '本地智能' }}</td>
              <td><span class="badge" :class="h.imported ? 'passed':'pending'">{{ h.imported ? '已导入' : '未导入' }}</span></td>
              <td class="muted" style="font-size:12px">{{ fmtTime(h.created_at) }}</td>
              <td>
                <button class="btn btn-sm" @click="viewRecord(h)">查看</button>
                <button class="btn btn-sm" @click="openImport(h)">导入</button>
                <button class="btn btn-sm btn-danger" @click="delRecord(h)">删</button>
              </td>
            </tr>
            <tr v-if="!history.length"><td colspan="8"><div class="empty">暂无生成记录</div></td></tr>
          </tbody>
        </table>
        <TablePager v-model:page="histPage" v-model:size="histPageSize" :total="history.length" />
      </div>
    </div>

    <!-- import modal -->
    <div v-if="importModal" class="modal-mask" @click.self="importModal=false">
      <div class="modal">
        <div class="modal-head">导入到用例中心<button class="close-x" @click="importModal=false">×</button></div>
        <div class="modal-body">
          <div class="field"><label>目标目录</label><select class="select" v-model="importFolderId"><option v-for="f in allFolders" :key="f.id" :value="f.id">{{ f.name }}</option></select></div>
          <div class="field">
            <label>选择要导入的用例（默认全部 {{ importSource?.cases_count }} 条）</label>
            <div class="import-hint">可全选导入，也可在生成结果的用例列表中先查看再决定。此处默认导入该次生成的全部用例。</div>
          </div>
        </div>
        <div class="modal-foot"><button class="btn" @click="importModal=false">取消</button><button class="btn btn-primary" @click="doImport" :disabled="importing">{{ importing ? '导入中...' : '确认导入' }}</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api, notify, currentProject } from '../api'
import TablePager from '../components/TablePager.vue'

const emit = defineEmits(['imported'])
const props = defineProps({ folders: { type: Array, default: () => [] } })

const view = ref('create')
const file = ref(null)
const dragging = ref(false)
const uploading = ref(false)
const progress = ref(0)
const generating = ref(false)
const result = ref(null)
const history = ref([])
const histPage = ref(1)
const histPageSize = ref(30)
const pagedHistory = computed(() => {
  const start = (histPage.value - 1) * histPageSize.value
  return history.value.slice(start, start + histPageSize.value)
})
const backend = ref('local')
const language = ref('zh')
const outputTemplate = ref('')
const selectedDims = ref([])
// 用例类型：functional=功能测试用例，api=接口测试用例
const caseTypes = ref(['functional', 'api'])
const filterDim = ref('')
const filterPriority = ref('')
const expanded = ref({})
const importModal = ref(false)
const importSource = ref(null)
const importFolderId = ref(null)
const importing = ref(false)
const exportFormat = ref('xlsx')
const exporting = ref(false)

const allDims = ['功能正确性','边界值','异常输入','数据校验','权限与安全','状态流转','性能与并发','UI与兼容性','易用性与提示']
const acceptTypes = '.pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.md,.markdown,.csv,.json,.log,.yaml,.yml,.xml,.ini,.sql,.html,.htm,.png,.jpg,.jpeg,.bmp,.gif,.webp'
const formats = [
  { icon: '📕', label: 'PDF' }, { icon: '📘', label: 'Word' }, { icon: '📗', label: 'Excel' },
  { icon: '📙', label: 'PPT' }, { icon: '📝', label: 'TXT/MD' }, { icon: '🖼️', label: '图片' },
]

const DEFAULT_TEMPLATES = {
  zh: '【{编号}】{标题}\n维度：{维度} ｜ 优先级：{优先级} ｜ 类型：{类型}\n前置条件：{前置条件}\n步骤：\n{步骤}\n预期结果：{预期结果}',
  en: '[{no}] {title}\nDimension: {dimension} | Priority: {priority} | Type: {case_type}\nPrecondition: {precondition}\nSteps:\n{steps}\nExpected: {expected}',
}
let templateTouched = false
let internalUpdate = false

function resetTemplate() {
  internalUpdate = true
  outputTemplate.value = DEFAULT_TEMPLATES[language.value]
  templateTouched = false
  setTimeout(() => { internalUpdate = false }, 0)
}
watch(() => outputTemplate.value, (v) => {
  if (internalUpdate) return
  if (v !== DEFAULT_TEMPLATES[language.value]) templateTouched = true
  else templateTouched = false
})
watch(language, () => { if (!templateTouched) resetTemplate() })

onMounted(() => {
  selectedDims.value = [...allDims]
  resetTemplate()
  loadHistory()
  if (!props.folders?.length) loadFolders()
})

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); notify('已复制到剪贴板') }
  catch (e) {
    const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta)
    ta.select(); document.execCommand('copy'); ta.remove(); notify('已复制到剪贴板')
  }
}

// 用户编辑模板后置位，语言切换不再覆盖
watch(() => outputTemplate.value, (v) => {
  if (v !== DEFAULT_TEMPLATES[language.value]) templateTouched = true
})
watch(language, () => { if (!templateTouched) outputTemplate.value = DEFAULT_TEMPLATES[language.value] })

const allFolders = computed(() => (props.folders?.length ? props.folders : localFolders.value))

// 作为独立页面使用时（路由 /gen-cases），自行加载目录；嵌入其他页面时用 props.folders
const localFolders = ref([])
async function loadFolders() {
  if (!currentProject.value) return
  try { localFolders.value = await api(`/api/folders?project_id=${currentProject.value.id}`) } catch (e) {}
}
watch(() => currentProject.value?.id, () => { if (!props.folders?.length) loadFolders() })
const filteredCases = computed(() => {
  if (!result.value) return []
  return result.value.cases.filter(c =>
    (!filterDim.value || c.dimension === filterDim.value) &&
    (!filterPriority.value || c.priority === filterPriority.value))
})

function onFile(e) { const f = e.target.files[0]; if (f) { file.value = f; result.value = null } }
function onDrop(e) { dragging.value = false; const f = e.dataTransfer.files[0]; if (f) { file.value = f; result.value = null } }
function fmtSize(n) { return n > 1024*1024 ? (n/1024/1024).toFixed(1)+' MB' : Math.round(n/1024)+' KB' }
function toggleExpand(no) { expanded.value[no] = !expanded.value[no] }
function typeName(t) { return ({api:'接口',ui:'UI',manual:'手工'})[t] || t }
function fmtTime(t) { return t ? t.replace('T',' ').slice(0,19) : '-' }

async function generate() {
  if (!file.value) { notify('请先上传文档', 'error'); return }
  if (!caseTypes.value.length) { notify('请至少选择一种用例类型', 'error'); return }
  generating.value = true
  uploading.value = true
  progress.value = 20
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('backend', backend.value)
    fd.append('dimensions', selectedDims.value.join(','))
    fd.append('language', language.value)
    fd.append('template', outputTemplate.value)
    fd.append('case_types', caseTypes.value.join(','))
    progress.value = 50
    result.value = await api('/api/generate', { method: 'POST', body: fd, rawBody: true })
    progress.value = 100
    notify(`生成完成，共 ${result.value.cases_count} 条用例`)
    expanded.value = {}
    filterDim.value = ''; filterPriority.value = ''
  } catch (e) { notify('生成失败：' + e.message, 'error') }
  finally { generating.value = false; uploading.value = false }
}

async function loadHistory() {
  try { history.value = await api('/api/generations'); histPage.value = 1 } catch (e) {}
}
async function viewRecord(h) {
  result.value = await api(`/api/generations/${h.id}`)
  expanded.value = {}; filterDim.value = ''; filterPriority.value = ''
  view.value = 'create'
}
async function openImport(source) {
  importSource.value = source || result.value
  // 目录尚未加载完（如刚进入页面就点击导入）时先加载，避免下拉为空
  if (!allFolders.value.length) await loadFolders()
  importFolderId.value = importFolderId.value || allFolders.value[0]?.id
  importModal.value = true
}
async function exportResult() {
  if (!result.value?.id) { notify('当前结果尚未保存，无法导出', 'error'); return }
  exporting.value = true
  try {
    const url = `/api/generations/${result.value.id}/export?format=${exportFormat.value}`
    const resp = await fetch(url)
    if (!resp.ok) { let m = resp.statusText; try { m = (await resp.json()).detail || m } catch (e) {} throw new Error(m) }
    const blob = await resp.blob()
    const cd = resp.headers.get('Content-Disposition') || ''
    let name = `${result.value.doc_name || 'cases'}.${exportFormat.value}`
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

async function doImport() {

  if (!importFolderId.value) { notify('请选择目标目录', 'error'); return }
  importing.value = true
  try {
    const r = await api(`/api/generations/${importSource.value.id}/import`, {
      method: 'POST', body: { record_id: importSource.value.id, folder_id: importFolderId.value, case_ids: [] },
    })
    notify(`成功导入 ${r.imported} 条用例到用例中心`)
    importModal.value = false
    emit('imported')
    loadHistory()
  } catch (e) { notify('导入失败：' + e.message, 'error') }
  finally { importing.value = false }
}
async function delRecord(h) {
  if (!confirm(`删除生成记录 #${h.id}（${h.doc_name}）？`)) return
  await api(`/api/generations/${h.id}`, { method: 'DELETE' })
  notify('已删除'); loadHistory()
}
</script>

<style scoped>
.dropzone { border: 2px dashed var(--border); border-radius: 12px; padding: 28px 20px; text-align: center; cursor: pointer; transition: .15s; background: var(--panel-2); }
.dropzone:hover, .dropzone.dragover { border-color: var(--primary); background: var(--primary-light); }
.dz-icon { font-size: 40px; margin-bottom: 8px; }
.dz-title { font-weight: 600; font-size: 14px; }
.dz-sub { color: var(--muted); font-size: 12px; margin-top: 6px; }
.dz-progress { height: 5px; background: #e6e9f0; border-radius: 3px; margin: 12px auto 0; max-width: 300px; overflow: hidden; }
.dz-progress .bar { height: 100%; background: var(--primary); transition: width .3s; }
.format-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
.format-chip { padding: 4px 9px; border: 1px solid var(--border); border-radius: 6px; font-size: 11px; display: flex; align-items: center; gap: 4px; background: var(--panel); }
.dim-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.ctype-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ctype {
  display: flex; gap: 9px; align-items: flex-start; cursor: pointer;
  border: 1.5px solid var(--border); border-radius: 8px; padding: 11px 12px;
  transition: border-color .15s, background .15s; background: var(--panel);
}
.ctype:hover { border-color: var(--primary); }
.ctype.checked { border-color: var(--primary); background: var(--primary-light); }
.ctype input { margin-top: 3px; accent-color: var(--primary); }
.ctype b { font-size: 13px; display: block; margin-bottom: 3px; }
.ctype span { font-size: 11px; color: var(--muted); line-height: 1.5; display: block; }
.api-line { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }
.api-line .method { background: var(--primary-light); color: var(--primary); font-weight: 700; }
.api-url { background: var(--panel-2); padding: 2px 7px; border-radius: 4px; font-size: 11px; font-family: Consolas, monospace; word-break: break-all; }
.dim { font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer; padding: 4px 0; }
.dim input { accent-color: var(--primary); }
.radio-row { display: flex; gap: 16px; }
.radio { display: flex; align-items: center; gap: 5px; font-size: 12px; cursor: pointer; }
.textarea.tpl { width: 100%; box-sizing: border-box; font-size: 11px; line-height: 1.5; resize: vertical; }
.tpl-tip { font-size: 11px; color: var(--muted); line-height: 1.8; margin-top: 5px; }
.tpl-tip code { background: var(--primary-light); color: var(--primary); padding: 1px 4px; border-radius: 3px; margin-right: 3px; font-size: 10px; }
.fmt-view { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin-bottom: 8px; }
.fmt-view-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.fmt-text { margin: 0; white-space: pre-wrap; word-break: break-word; font-size: 11px; line-height: 1.7; font-family: Consolas, Monaco, monospace; }
.struct-view { font-size: 12px; }
.struct-view summary { cursor: pointer; color: var(--muted); font-size: 11px; }
.result-actions { display: flex; align-items: center; gap: 10px; }
.gen-meta { background: var(--panel-2); border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; font-size: 12px; line-height: 1.9; }
.gen-meta .tag { margin-right: 4px; }
.dim-filter { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.case-preview-list { display: flex; flex-direction: column; gap: 8px; }
.pcase { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.pcase-head { display: flex; align-items: center; gap: 8px; padding: 9px 12px; cursor: pointer; font-size: 12px; background: var(--panel); }
.pcase-head:hover { background: var(--panel-2); }
.pcase-title { font-weight: 600; flex: 1; min-width: 0; }
.pcase-body { padding: 12px; border-top: 1px solid var(--border); background: var(--panel-2); font-size: 12px; line-height: 1.8; }
.pcase-body pre.code { margin: 6px 0; white-space: pre-wrap; font-size: 11px; }
.risk { color: var(--warn); margin-bottom: 6px; }
.import-hint { background: var(--primary-light); color: var(--primary); padding: 10px; border-radius: 6px; font-size: 12px; }
.badge { padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 600; }
</style>
