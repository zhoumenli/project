<template>
  <div>
    <div class="panel">
      <div class="toolbar" style="padding:16px 18px;margin:0">
        <button class="btn btn-primary" @click="openRunDialog">▶ 新建执行</button>
        <div class="spacer"></div>
        <span class="muted" style="font-size:12px">共 {{ runs.length }} 条记录</span>
      </div>
      <table>
        <thead><tr><th>执行ID</th><th>状态</th><th>用例统计</th><th>通过率</th><th>触发方式</th><th>开始时间</th><th>耗时</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="r in runs" :key="r.id">
            <td><b>#{{ r.id }}</b></td>
            <td><span class="badge" :class="r.status">{{ statusName(r.status) }}</span></td>
            <td><span class="badge passed">{{ r.passed }}</span> / <span class="badge failed">{{ r.failed }}</span> / <span class="badge skipped">{{ r.skipped }}</span></td>
            <td><b :style="{color: passRate(r) >= 80 ? 'var(--success)':'var(--danger)'}">{{ passRate(r) }}%</b></td>
            <td class="muted">{{ r.trigger }}</td>
            <td class="muted" style="font-size:12px">{{ fmt(r.start_time) }}</td>
            <td class="muted" style="font-size:12px">{{ duration(r) }}</td>
            <td><button class="btn btn-sm" @click="viewReport(r)">查看报告</button> <button class="btn btn-sm btn-danger" @click="delRun(r)">删</button></td>
          </tr>
          <tr v-if="!runs.length"><td colspan="8"><div class="empty">暂无执行记录</div></td></tr>
        </tbody>
      </table>
    </div>

    <!-- run dialog -->
    <div v-if="runDialog" class="modal-mask" @click.self="runDialog=false">
      <div class="modal">
        <div class="modal-head">新建执行<button class="close-x" @click="runDialog=false">×</button></div>
        <div class="modal-body">
          <div class="field"><label>执行方式</label><select class="select" v-model="runMode"><option value="suite">按测试集</option><option value="type">按用例类型</option><option value="manual">手动选择用例</option></select>
            <div class="adv-tip">用例按顺序执行；前一条用例「提取的变量」会自动传给后续用例，可在 URL/请求头/Body 用 <code>&#123;&#123;变量名&#125;&#125;</code> 引用（接口关联）</div>
          </div>
          <div v-if="runMode==='suite'" class="field"><label>选择测试集</label><select class="select" v-model="runPayload.suite_id"><option :value="null">-- 请选择 --</option><option v-for="s in suites" :key="s.id" :value="s.id">{{ s.name }} ({{ s.case_ids.length }}用例)</option></select></div>
          <div v-if="runMode==='type'" class="field"><label>用例类型</label><select class="select" v-model="runPayload.case_type"><option value="api">接口用例</option><option value="ui">UI 用例</option></select></div>
          <div v-if="runMode==='manual'" class="field"><label>选择用例</label><div class="case-checks"><label v-for="c in allCases" :key="c.id" class="check"><input type="checkbox" :value="c.id" v-model="runPayload.case_ids" /> {{ c.title }}</label></div></div>
          <div class="field"><label>执行环境</label><select class="select" v-model="runPayload.env_id"><option :value="null">-- 无环境 --</option><option v-for="e in envs" :key="e.id" :value="e.id">{{ e.name }} ({{ e.base_url }})</option></select></div>
        </div>
        <div class="modal-foot"><button class="btn" @click="runDialog=false">取消</button><button class="btn btn-primary" @click="startRun" :disabled="starting">{{ starting ? '执行中...' : '开始执行' }}</button></div>
      </div>
    </div>

    <!-- report drawer modal -->
    <div v-if="reportRun" class="modal-mask" @click.self="reportRun=null">
      <div class="modal wide">
        <div class="modal-head">执行报告 #{{ reportRun.id }} <button class="close-x" @click="reportRun=null">×</button></div>
        <div class="modal-body">
          <div class="report-summary">
            <div><b>{{ reportRun.total }}</b><span>总用例</span></div>
            <div style="color:var(--success)"><b>{{ reportRun.passed }}</b><span>通过</span></div>
            <div style="color:var(--danger)"><b>{{ reportRun.failed }}</b><span>失败</span></div>
            <div style="color:var(--muted)"><b>{{ reportRun.skipped }}</b><span>跳过</span></div>
          </div>
          <div v-for="d in reportDetails" :key="d.id" class="detail">
            <div class="detail-head" @click="toggleDetail(d.id)">
              <span class="badge" :class="d.status">{{ statusName(d.status) }}</span>
              <b>{{ d.case_title }}</b>
              <span class="muted" style="font-size:12px">{{ d.duration_ms }}ms</span>
              <span style="margin-left:auto" class="muted">{{ expanded[d.id] ? '收起':'展开' }}</span>
            </div>
            <div v-if="expanded[d.id]" class="detail-body">
              <div v-if="d.error_msg" class="result-error">⚠️ {{ d.error_msg }}</div>
              <div v-if="d.request_info?.url" class="field"><label>请求</label><pre class="code">{{ d.request_info.method }} {{ d.request_info.url }}{{ d.request_info.body ? '\n\n'+d.request_info.body : '' }}</pre></div>
              <div v-if="d.response_info?.status_code" class="field"><label>响应</label><pre class="code">{{ fmtBody(d.response_info.body) }}</pre></div>
              <div v-if="d.assertions_result?.length" class="field"><label>断言</label><div v-for="(a,i) in d.assertions_result" :key="i" class="assert-result" :class="a.passed?'ok':'no'"><span>{{ a.passed?'✓':'✗' }}</span><span>{{ a.type }}{{ a.key?'.'+a.key:'' }} {{ a.op }} {{ a.expected }} → {{ fmtVal(a.actual) }}</span></div></div>
              <div v-if="d.extracted && Object.keys(d.extracted).length" class="field"><label>🔗 提取并传递的变量（供后续用例使用）</label><pre class="code">{{ fmtBody(d.extracted) }}</pre></div>
              <div v-if="d.logs" class="field"><label>日志</label><pre class="code">{{ d.logs }}</pre></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { api, notify, currentProject } from '../api'

const runs = ref([])
const suites = ref([])
const envs = ref([])
const allCases = ref([])
const runDialog = ref(false)
const runMode = ref('suite')
const runPayload = ref({ suite_id: null, case_type: 'api', case_ids: [], env_id: null })
const starting = ref(false)
const reportRun = ref(null)
const reportDetails = ref([])
const expanded = reactive({})

onMounted(loadAll)
async function loadAll() {
  runs.value = await api('/api/runs')
  envs.value = await api('/api/environments')
  suites.value = currentProject.value ? await api(`/api/suites?project_id=${currentProject.value.id}`) : []
  allCases.value = currentProject.value ? await api(`/api/cases?project_id=${currentProject.value.id}`) : []
}
function openRunDialog() { runDialog.value = true; runPayload.value = { suite_id: null, case_type: 'api', case_ids: [], env_id: null } }
async function startRun() {
  starting.value = true
  try {
    const body = { trigger: 'manual', env_id: runPayload.value.env_id }
    if (runMode.value === 'suite') {
      if (!runPayload.value.suite_id) { notify('请选择测试集', 'error'); return }
      body.suite_id = runPayload.value.suite_id
    } else if (runMode.value === 'type') {
      body.case_type = runPayload.value.case_type
    } else {
      if (!runPayload.value.case_ids.length) { notify('请至少选择一个用例', 'error'); return }
      body.case_ids = runPayload.value.case_ids
    }
    const run = await api('/api/runs', { method: 'POST', body })
    runDialog.value = false
    notify(`执行完成：通过 ${run.passed}，失败 ${run.failed}`)
    await loadAll()
    viewReport(run)
  } catch (e) { notify('执行失败: '+e.message, 'error') }
  finally { starting.value = false }
}
async function viewReport(r) {
  reportRun.value = r
  reportDetails.value = await api(`/api/runs/${r.id}/details`)
}
function toggleDetail(id) { expanded[id] = !expanded[id] }
async function delRun(r) {
  if (!confirm(`删除执行记录 #${r.id}？`)) return
  await api(`/api/runs/${r.id}`, { method: 'DELETE' }); loadAll()
}
function passRate(r) { return r.total ? Math.round(r.passed/r.total*100) : 0 }
function duration(r) { return r.start_time && r.end_time ? Math.round((new Date(r.end_time)-new Date(r.start_time))/1000)+'s' : '-' }
function statusName(s) { return ({pending:'等待',running:'运行中',done:'完成',passed:'通过',failed:'失败',error:'异常',skipped:'跳过'})[s]||s }
function fmt(t) { return t ? t.replace('T',' ').slice(0,19) : '-' }
function fmtBody(v) { return typeof v === 'string' ? v : JSON.stringify(v, null, 2) }
function fmtVal(v) { return typeof v === 'object' ? JSON.stringify(v) : String(v) }
</script>

<style scoped>
.case-checks { max-height: 180px; overflow: auto; border: 1px solid var(--border); border-radius: 8px; padding: 10px; }
.check { display: block; padding: 5px 0; font-size: 13px; cursor: pointer; }
.check input { margin-right: 8px; }
.adv-tip { font-size: 11px; color: var(--muted); margin-top: 6px; line-height: 1.6; }
.adv-tip code { background: #eef1ff; color: var(--primary); padding: 1px 4px; border-radius: 3px; }
.report-summary { display: flex; gap: 30px; margin-bottom: 18px; }
.report-summary div { display: flex; flex-direction: column; text-align: center; }
.report-summary b { font-size: 28px; }
.report-summary span { font-size: 12px; color: var(--muted); }
.detail { border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; overflow: hidden; }
.detail-head { display: flex; align-items: center; gap: 10px; padding: 11px 14px; cursor: pointer; background: #fafbfc; }
.detail-body { padding: 14px; border-top: 1px solid var(--border); }
.result-error { background: #fdeaea; color: var(--danger); padding: 12px; border-radius: 8px; margin-bottom: 12px; }
.assert-result { display: flex; gap: 8px; padding: 6px 10px; border-radius: 6px; font-size: 12px; margin-bottom: 5px; }
.assert-result.ok { background: #e4f7ee; color: var(--success); }
.assert-result.no { background: #fdeaea; color: var(--danger); }
</style>
