<template>
  <div class="row" style="align-items:flex-start">
    <div class="col">
      <div class="panel">
        <div class="panel-head"><h2>🌐 UI 自动化用例</h2><router-link to="/cases" class="btn btn-sm">管理全部用例 →</router-link></div>
        <div class="panel-body">
          <div class="field-row">
            <div class="field col"><label>选择 UI 用例</label><select class="select" v-model="selectedId" @change="loadSteps"><option :value="null">-- 请选择 --</option><option v-for="c in uiCases" :key="c.id" :value="c.id">{{ c.title }}</option></select></div>
            <div class="field" style="width:160px;align-self:flex-end"><button class="btn btn-primary" style="width:100%" @click="runCase" :disabled="!selectedId || running">{{ running ? '运行中...' : '▶ 运行用例' }}</button></div>
          </div>
          <div v-if="selectedId">
            <div class="muted" style="font-size:12px;margin:8px 0">用例步骤（点击步骤可编辑，拖拽暂不支持）</div>
            <div class="step-list">
              <div v-for="(s,i) in steps" :key="i" class="step" :class="{editing: editIdx===i}" @click="editIdx=i">
                <span class="step-no">{{ i+1 }}</span>
                <template v-if="editIdx!==i">
                  <span class="step-action tag">{{ s.action }}</span>
                  <span class="step-target">{{ s.target || '(空)' }}</span>
                  <span v-if="s.value" class="muted">= {{ s.value }}</span>
                  <button class="btn btn-sm btn-danger" style="margin-left:auto" @click.stop="steps.splice(i,1)">×</button>
                </template>
                <template v-else>
                  <input class="input" v-model="s.action" style="width:110px" list="actions" />
                  <datalist id="actions"><option v-for="a in actions" :key="a" :value="a"></option></datalist>
                  <input class="input" v-model="s.target" placeholder="选择器 / URL" style="flex:1" />
                  <input class="input" v-model="s.value" placeholder="值(可选)" style="width:110px" />
                  <button class="btn btn-sm" @click.stop="editIdx=-1">✓</button>
                </template>
              </div>
            </div>
            <div style="margin-top:12px;display:flex;gap:8px">
              <button class="btn btn-sm" @click="addStep">＋ 添加步骤</button>
              <button class="btn btn-sm" @click="saveSteps">💾 保存步骤</button>
              <button class="btn btn-sm" @click="showJson=!showJson">{{ showJson ? '隐藏' : '查看' }} JSON</button>
            </div>
            <div v-if="showJson" class="field" style="margin-top:12px"><pre class="code">{{ jsonSteps }}</pre></div>
          </div>
          <div v-else class="empty"><div class="big">🌐</div>请选择一个 UI 用例，或前往用例中心新建</div>
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel">
        <div class="panel-head"><h2>执行日志</h2><div v-if="lastResult.status" class="badge" :class="lastResult.status">{{ statusName(lastResult.status) }}</div></div>
        <div class="panel-body">
          <div v-if="lastResult.error_msg" class="result-error">⚠️ {{ lastResult.error_msg }}</div>
          <div v-if="lastResult.logs" class="field" style="margin-top:8px"><label>步骤日志</label><pre class="code">{{ lastResult.logs }}</pre></div>
          <div v-if="lastResult.request_info?.screenshots?.length" class="field">
            <label>截图记录（演示模式标记）</label>
            <div v-for="s in lastResult.request_info.screenshots" :key="s.step" class="tag">步骤{{ s.step }}: {{ s.target }}</div>
          </div>
          <div v-if="!lastResult.status" class="empty"><div class="big">▶️</div>运行用例后显示执行结果</div>
          <div class="hint">💡 演示环境使用模拟执行引擎。生产环境可接入真实 Playwright 浏览器（见 README）。</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, notify } from '../api'

const uiCases = ref([])
const selectedId = ref(null)
const steps = ref([])
const editIdx = ref(-1)
const showJson = ref(false)
const running = ref(false)
const lastResult = ref({})
const actions = ['goto','click','fill','assert_visible','wait','screenshot','select','press']

const jsonSteps = computed(() => JSON.stringify(steps.value, null, 2))

onMounted(async () => {
  uiCases.value = await api('/api/cases?case_type=ui')
})
function loadSteps() {
  const c = uiCases.value.find(x => x.id === selectedId.value)
  if (!c) return
  try { steps.value = typeof c.steps === 'string' ? JSON.parse(c.steps||'[]') : (c.steps||[]) }
  catch(e) { steps.value = [] }
  lastResult.value = {}
  editIdx.value = -1
}
function addStep() { steps.value.push({ action: 'click', target: '', value: '' }); editIdx.value = steps.value.length-1 }
async function saveSteps() {
  if (!selectedId.value) return
  const c = uiCases.value.find(x => x.id === selectedId.value)
  await api(`/api/cases/${selectedId.value}`, { method: 'PUT', body: { steps: jsonSteps.value } })
  c.steps = jsonSteps.value
  notify('步骤已保存')
}
async function runCase() {
  if (!selectedId.value) return
  running.value = true
  lastResult.value = {}
  try {
    const c = uiCases.value.find(x => x.id === selectedId.value)
    lastResult.value = await api('/api/runs', { method: 'POST', body: { case_ids: [selectedId.value], trigger: 'manual' } }).then(async run => {
      const details = await api(`/api/runs/${run.id}/details`)
      return details[0] || {}
    })
  } catch (e) { notify('执行失败: '+e.message, 'error') }
  finally { running.value = false }
}
function statusName(s) { return ({passed:'通过',failed:'失败',error:'异常',skipped:'跳过'})[s]||s }
</script>

<style scoped>
.step-list { display: flex; flex-direction: column; gap: 6px; }
.step { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 13px; }
.step:hover { border-color: var(--primary); }
.step.editing { border-color: var(--primary); background: #fafbff; flex-wrap: wrap; }
.step-no { width: 22px; height: 22px; border-radius: 50%; background: #eef1ff; color: var(--primary); display: grid; place-items: center; font-size: 11px; flex-shrink: 0; }
.step-target { font-family: Consolas, monospace; font-size: 12px; }
.result-error { background: #fdeaea; color: var(--danger); padding: 14px; border-radius: 8px; line-height: 1.6; }
.hint { margin-top: 16px; padding: 12px; background: #eef1ff; color: var(--primary); border-radius: 8px; font-size: 12px; line-height: 1.6; }
</style>
