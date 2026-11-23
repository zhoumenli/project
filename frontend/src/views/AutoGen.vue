<template>
  <div>
    <div class="panel">
      <div class="panel-head"><h2>接口自动化项目生成</h2><span class="muted" style="font-size:12px">按接口自动化框架模板（pytest + requests + allure 数据驱动）一键生成可运行项目</span></div>
      <div class="toolbar" style="padding:16px 18px;margin:0;flex-wrap:wrap">
        <select class="select" v-model="folderId" style="width:190px" @change="estimate">
          <option :value="null">全部目录</option>
          <option v-for="f in folders" :key="f.id" :value="f.id">{{ f.name }}</option>
        </select>
        <input class="input" v-model="keyword" placeholder="按标题关键字过滤（可选）" style="width:200px" @keyup.enter="estimate" />
        <input class="input" v-model="baseUrl" placeholder="BASE_URL，如 http://127.0.0.1:9001" style="width:250px" />
        <button class="btn btn-primary" @click="generate" :disabled="loading || !apiCount">{{ loading ? '生成中...' : '🤖 生成并下载' }}</button>
        <span class="muted" style="font-size:12px;align-self:center">
          {{ pickedIds.length ? `已从用例中心带入 ${pickedIds.length} 条勾选用例` : `当前范围将生成 ${apiCount} 条接口用例` }}
        </span>
      </div>
      <div style="padding:0 18px 16px">
        <div v-if="pickedIds.length" class="tip-card warn">
          <b>勾选模式</b>：仅生成从用例中心勾选带入的 {{ pickedIds.length }} 条用例（非接口用例自动忽略）。如需按范围生成，请点击「清除勾选」。
          <button class="btn btn-sm" style="margin-left:8px" @click="clearPicked">清除勾选</button>
        </div>
        <div class="tip-card">
          <b>生成的项目结构</b>（框架文件取自 <code>{{ templateDir }}</code>，可用环境变量 <code>API_TEMPLATE_DIR</code> 更换模板）：
          <pre class="tree" v-pre>config.py            # BASE_URL（取自上方输入）
pytest.ini / main.py / API/demo1.py / Tools/*    # 框架原样
caseData/data.yaml   # 按目录 kw 分组的数据驱动用例
Tools/render.py      # {{var}} 占位符渲染（如登录提取 token）
Tools/assert_util.py # 断言执行器 + 变量提取
testcase/&lt;模块&gt;/test_xxx.py   # parametrize + allure</pre>
          使用方式：解压 zip → <code>pip install -r requirements.txt</code> → <code>pytest</code>（或 <code>python main.py</code> 生成 allure 报告）。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api, currentProject, notify, loadProjects } from '../api'
import { token } from '../auth'

const route = useRoute()
const folders = ref([])
const folderId = ref(null)
const keyword = ref('')
const baseUrl = ref('http://127.0.0.1:9001')
const apiCount = ref(0)
const loading = ref(false)
const pickedIds = ref([])
const templateDir = 'C:/project/initial_api_framework'

async function loadFolders() {
  if (!currentProject.value) return
  folders.value = await api(`/api/folders?project_id=${currentProject.value.id}`)
}

async function estimate() {
  if (!currentProject.value) return
  try {
    if (pickedIds.value.length) {
      const all = await api(`/api/cases?project_id=${currentProject.value.id}&case_type=api`)
      apiCount.value = all.filter(c => pickedIds.value.includes(c.id)).length
      return
    }
    let url = `/api/cases?project_id=${currentProject.value.id}&case_type=api`
    if (folderId.value) url += `&folder_id=${folderId.value}`
    if (keyword.value) url += `&keyword=${encodeURIComponent(keyword.value)}`
    apiCount.value = (await api(url)).length
  } catch (e) { apiCount.value = 0 }
}

function clearPicked() {
  pickedIds.value = []
  estimate()
}

async function generate() {
  if (!currentProject.value) await loadProjects()
  if (!currentProject.value) { notify('请先创建项目', 'error'); return }
  if (!apiCount.value) { notify('当前范围内没有接口用例', 'error'); return }
  loading.value = true
  try {
    const body = {
      project_id: currentProject.value.id,
      base_url: baseUrl.value.trim() || 'http://127.0.0.1:9001',
    }
    if (pickedIds.value.length) body.case_ids = pickedIds.value
    else {
      if (folderId.value) body.folder_id = folderId.value
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
    notify(`已生成 ${name}，解压后 pip install -r requirements.txt 即可运行`)
  } catch (e) { notify('生成失败：' + e.message, 'error') }
  finally { loading.value = false }
}

onMounted(async () => {
  if (!currentProject.value) await loadProjects()
  await loadFolders()
  // 从用例中心勾选跳转带入 case_ids
  const qids = (route.query.ids || '').toString().split(',').map(Number).filter(Boolean)
  pickedIds.value = qids
  await estimate()
})
watch(() => keyword.value, () => { if (keyword.value === '') estimate() })
</script>

<style scoped>
.tip-card { background: var(--surface-2, #f6f7fb); border: 1px solid var(--border, var(--border)); border-radius: 10px; padding: 12px 14px; font-size: 13px; line-height: 1.7; margin-bottom: 10px; }
.tip-card.warn { background: rgba(226,163,60,.13); border-color: rgba(226,163,60,.35); }
.tip-card code { background: #eceef6; border-radius: 4px; padding: 1px 5px; font-size: 12px; }
.tree { background: var(--text); color: #c9d4f5; border-radius: 8px; padding: 10px 12px; font-size: 12px; line-height: 1.6; font-family: Consolas, monospace; white-space: pre; overflow: auto; margin: 8px 0 0; }
</style>
