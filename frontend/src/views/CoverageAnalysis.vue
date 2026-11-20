<template>
  <div>
    <div class="panel">
      <div class="panel-head"><h2>需求覆盖率分析</h2><span class="muted" style="font-size:12px">量化"用例够不够"，未覆盖需求点标红</span></div>
      <div class="toolbar" style="padding:14px 18px 0;margin:0">
        <select class="select" v-model="genId" style="width:260px" @change="loadGenText">
          <option value="">从历史生成记录加载需求…</option>
          <option v-for="g in generations" :key="g.id" :value="g.id">#{{ g.id }} {{ g.doc_name }}（{{ g.cases_count }} 条）</option>
        </select>
        <button class="btn btn-primary" @click="analyze" :disabled="loading">{{ loading ? '分析中...' : '🔍 开始分析' }}</button>
        <span class="muted" style="font-size:12px;align-self:center">分析范围：当前项目「{{ currentProject?.name }}」下的全部用例</span>
      </div>
      <div style="padding:12px 18px 18px">
        <textarea class="textarea" v-model="reqText" style="min-height:120px" placeholder="粘贴需求文档文本，或从上方选择历史生成记录…"></textarea>
      </div>
    </div>

    <template v-if="result">
      <div class="stat-row">
        <div class="stat-card"><div class="stat-num">{{ result.summary.points }}</div><div class="stat-label">需求点</div></div>
        <div class="stat-card ok"><div class="stat-num">{{ result.summary.covered }}</div><div class="stat-label">已覆盖</div></div>
        <div class="stat-card" :class="result.summary.coverage >= 80 ? 'ok' : (result.summary.coverage >= 50 ? 'warn' : 'bad')">
          <div class="stat-num">{{ result.summary.coverage }}%</div><div class="stat-label">需求覆盖率</div>
        </div>
        <div class="stat-card" :class="uncoveredCount ? 'bad' : 'ok'">
          <div class="stat-num">{{ uncoveredCount }}</div><div class="stat-label">未覆盖需求点</div>
        </div>
        <div class="stat-card warn"><div class="stat-num">{{ result.summary.orphan_cases.length }}</div><div class="stat-label">游离用例</div></div>
      </div>

      <div class="panel">
        <div class="panel-head"><h2>需求点 → 用例映射矩阵</h2></div>
        <div style="padding:0 18px 18px">
          <table>
            <thead><tr><th style="width:60px">状态</th><th style="width:40%">需求点</th><th style="width:80px">关联用例</th><th>匹配用例（按相似度排序）</th></tr></thead>
            <tbody>
              <tr v-for="p in result.requirement_points" :key="p.index" :class="p.covered ? '' : 'row-miss'">
                <td><span class="badge" :class="p.covered ? 'P0' : 'P3'">{{ p.covered ? '✓ 覆盖' : '✗ 缺口' }}</span></td>
                <td><div class="pt-text">{{ p.text }}</div></td>
                <td><b :class="p.covered ? 'c-ok' : 'c-bad'">{{ p.case_count }}</b></td>
                <td>
                  <span v-for="m in p.matched" :key="m.id" class="match-chip" :title="`相似度 ${m.score}`">
                    #{{ m.id }} {{ m.title.slice(0, 22) }}<i>{{ m.score }}</i>
                  </span>
                  <span v-if="!p.covered" class="muted" style="font-size:12px">— 无用例命中，建议补充用例</span>
                </td>
              </tr>
              <tr v-if="!result.requirement_points.length"><td colspan="4"><div class="empty">未提取到需求点</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="panel" v-if="result.summary.orphan_cases.length">
        <div class="panel-head"><h2>游离用例（未命中任何需求点）</h2></div>
        <div style="padding:0 18px 18px">
          <div class="orphan-list">
            <span v-for="c in result.summary.orphan_cases" :key="c.id" class="match-chip" :title="c.case_type">#{{ c.id }} {{ c.title }}</span>
          </div>
          <div class="muted" style="font-size:12px;margin-top:8px">这些用例与当前需求无关联——可能是历史遗留、探索性用例或需求已变更，建议人工确认。</div>
        </div>
      </div>
    </template>
    <div v-else class="panel" style="margin-top:16px"><div class="panel-body"><div class="empty" style="padding:40px 0">粘贴需求文本或选择生成记录，点「开始分析」查看覆盖情况</div></div></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, currentProject, notify, loadProjects } from '../api'

const generations = ref([])
const genId = ref('')
const reqText = ref('')
const loading = ref(false)
const result = ref(null)

const uncoveredCount = computed(() => result.value ? result.value.requirement_points.filter(p => !p.covered).length : 0)

async function loadGenerations() {
  try { generations.value = await api('/api/generations') } catch (e) {}
}
async function loadGenText() {
  if (!genId.value) return
  try {
    const g = await api(`/api/generations/${genId.value}`)
    reqText.value = g.requirement_text || ''
    if (!reqText.value) notify('该记录未保存需求原文，请手动粘贴', 'error')
  } catch (e) { notify('加载失败：' + e.message, 'error') }
}

async function analyze() {
  if (!currentProject.value) await loadProjects()
  if (!currentProject.value) { notify('请先创建项目', 'error'); return }
  if (!reqText.value.trim()) { notify('请先粘贴需求文本或选择生成记录', 'error'); return }
  loading.value = true
  try {
    result.value = await api('/api/coverage/analyze', { method: 'POST', body: {
      project_id: currentProject.value.id,
      requirement_text: reqText.value,
      generation_id: genId.value ? Number(genId.value) : null,
    }})
    const s = result.value.summary
    notify(`分析完成：${s.covered}/${s.points} 个需求点已覆盖（${s.coverage}%）`, s.coverage >= 80 ? 'success' : 'error')
  } catch (e) { notify('分析失败：' + e.message, 'error') }
  finally { loading.value = false }
}
onMounted(() => { loadGenerations(); if (!currentProject.value) loadProjects() })
</script>

<style scoped>
.stat-row { display: flex; gap: 14px; margin: 16px 0; }
.stat-card { flex: 1; background: var(--surface, #fff); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; text-align: center; }
.stat-card .stat-num { font-size: 26px; font-weight: 700; }
.stat-card .stat-label { font-size: 12px; color: var(--muted); margin-top: 4px; }
.stat-card.ok .stat-num { color: #2e9e5b; }
.stat-card.warn .stat-num { color: #d9a013; }
.stat-card.bad .stat-num { color: #d64545; }
.row-miss { background: rgba(214, 69, 69, 0.06); }
.pt-text { font-size: 13px; line-height: 1.5; word-break: break-all; }
.match-chip { display: inline-block; background: var(--surface-2, #f4f5f7); border: 1px solid var(--border); border-radius: 6px; padding: 2px 8px; margin: 2px 6px 2px 0; font-size: 12px; }
.match-chip i { font-style: normal; color: var(--muted); margin-left: 4px; }
.orphan-list { display: flex; flex-wrap: wrap; gap: 6px; }
.c-ok { color: #2e9e5b; }
.c-bad { color: #d64545; }
</style>
