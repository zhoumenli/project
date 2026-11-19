<template>
  <div>
    <div class="panel">
      <div class="toolbar" style="padding:16px 18px;margin:0"><button class="btn btn-primary" @click="openDialog()">＋ 新建环境</button></div>
      <table>
        <thead><tr><th>环境名称</th><th>Base URL</th><th>变量</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="e in envs" :key="e.id">
            <td><b>{{ e.name }}</b></td>
            <td class="muted">{{ e.base_url || '-' }}</td>
            <td><pre class="code" style="max-height:80px;margin:0">{{ fmt(e.variables) }}</pre></td>
            <td><button class="btn btn-sm" @click="openDialog(e)">编辑</button> <button class="btn btn-sm btn-danger" @click="delEnv(e)">删除</button></td>
          </tr>
          <tr v-if="!envs.length"><td colspan="4"><div class="empty">暂无环境</div></td></tr>
        </tbody>
      </table>
    </div>
    <div v-if="dialog" class="modal-mask" @click.self="dialog=false">
      <div class="modal">
        <div class="modal-head">{{ editing ? '编辑环境' : '新建环境' }}<button class="close-x" @click="dialog=false">×</button></div>
        <div class="modal-body">
          <div class="field"><label>环境名称</label><input class="input" v-model="form.name" placeholder="如：测试环境" /></div>
          <div class="field"><label>Base URL</label><input class="input" v-model="form.base_url" placeholder="http://127.0.0.1:9001" /></div>
          <div class="field"><label>变量（JSON，用例中可用双花括号变量名引用）</label><textarea class="textarea" v-model="varsStr" style="font-family:Consolas,monospace;font-size:12px"></textarea></div>
        </div>
        <div class="modal-foot"><button class="btn" @click="dialog=false">取消</button><button class="btn btn-primary" @click="save">保存</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api, notify } from '../api'

const envs = ref([])
const dialog = ref(false)
const editing = ref(null)
const form = ref({ name: '', base_url: '', variables: {} })
const varsStr = ref('{}')

onMounted(load)
async function load() { envs.value = await api('/api/environments') }
function openDialog(e) {
  editing.value = e
  form.value = e ? JSON.parse(JSON.stringify(e)) : { name: '', base_url: '', variables: {} }
  varsStr.value = JSON.stringify(form.value.variables || {}, null, 2)
  dialog.value = true
}
async function save() {
  try {
    form.value.variables = JSON.parse(varsStr.value || '{}')
    if (!form.value.name.trim()) { notify('请填写环境名称', 'error'); return }
    if (editing.value) await api(`/api/environments/${editing.value.id}`, { method: 'PUT', body: form.value })
    else await api('/api/environments', { method: 'POST', body: form.value })
    dialog.value = false; notify('已保存'); load()
  } catch (e) { notify('保存失败：'+e.message, 'error') }
}
async function delEnv(e) {
  if (!confirm(`删除环境「${e.name}」？`)) return
  await api(`/api/environments/${e.id}`, { method: 'DELETE' }); load()
}
function fmt(v) { return JSON.stringify(v, null, 2) }
</script>
