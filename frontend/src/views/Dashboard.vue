<template>
  <div>
    <div class="welcome-banner">
      <div class="welcome-text">
        <div class="welcome-eyebrow">✦ 工作台概览</div>
        <h2>开启高效测试之旅</h2>
        <p>这里是你的测试指挥中心，随时掌握项目、用例与执行情况。</p>
      </div>
      <div class="welcome-art">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="art-emoji">🚀</div>
      </div>
    </div>
    <div class="stat-grid">
      <div class="stat-card" v-for="(s,i) in stats" :key="s.label" :style="{animationDelay: (i*0.06)+'s'}">
        <div class="ico" :style="{background: s.bg, color: s.color}">{{ s.icon }}</div>
        <div class="num">{{ s.value }}</div>
        <div class="label">{{ s.label }}</div>
      </div>
    </div>
    <div class="row">
      <div class="col">
        <div class="panel">
          <div class="panel-head"><h2>最近执行趋势</h2><router-link to="/runs" class="btn btn-sm">查看全部 →</router-link></div>
          <div class="panel-body">
            <div v-if="trend.length" class="chart">
              <div v-for="(t,i) in trend" :key="i" class="chart-row">
                <span class="chart-label">#{{ t.id }}</span>
                <div class="chart-bars">
                  <div class="bar pass" :style="{width: barW(t.passed)}" :title="`通过 ${t.passed}`"></div>
                  <div class="bar fail" :style="{width: barW(t.failed)}" :title="`失败 ${t.failed}`"></div>
                </div>
                <span class="chart-num">{{ t.passed }}/{{ t.total }}</span>
              </div>
            </div>
            <div v-else class="empty"><div class="big">📈</div>暂无执行记录，去接口测试跑一次吧</div>
          </div>
        </div>
      </div>
      <div class="col">
        <div class="panel">
          <div class="panel-head"><h2>快速开始</h2></div>
          <div class="panel-body">
            <div class="quick-grid">
              <router-link to="/cases" class="quick"><span>📝</span><b>新建用例</b><small>管理接口/UI/手工用例</small></router-link>
              <router-link to="/api-test" class="quick"><span>🔌</span><b>接口调试</b><small>单接口请求与断言</small></router-link>
              <router-link to="/ui-test" class="quick"><span>🌐</span><b>UI 用例</b><small>编排 Web 自动化步骤</small></router-link>
              <router-link to="/runs" class="quick"><span>▶️</span><b>执行测试</b><small>运行测试集并看报告</small></router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const stats = ref([])
const trend = ref([])
onMounted(async () => {
  const d = await api('/api/dashboard')
  stats.value = [
    { label: '项目数', value: d.project_count, icon: '📁', bg: 'var(--primary-light)', color: '#aab2ff' },
    { label: '用例总数', value: d.case_count, icon: '📋', bg: 'rgba(39,166,68,.14)', color: '#5fd18a' },
    { label: '接口用例', value: d.api_count, icon: '🔌', bg: 'rgba(226,163,60,.14)', color: '#e8bd6b' },
    { label: 'UI 用例', value: d.ui_count, icon: '🌐', bg: 'var(--primary-light)', color: '#aab2ff' },
    { label: '执行次数', value: d.run_count, icon: '▶️', bg: 'rgba(235,87,87,.14)', color: '#f0858f' },
  ]
  trend.value = d.trend
})
function barW(n) {
  const max = Math.max(1, ...trend.value.map(t => t.total))
  return Math.round((n / max) * 100) + '%'
}
</script>

<style scoped>
.welcome-banner {
  position: relative; overflow: hidden;
  background: var(--panel); border: 1px solid var(--border);
  border-left: 3px solid var(--primary);
  border-radius: 12px; padding: 26px 30px; margin-bottom: 22px;
  color: var(--text);
}
.welcome-text { position: relative; z-index: 2; }
.welcome-eyebrow {
  font-size: 11px; font-weight: 500; letter-spacing: .4px; text-transform: uppercase;
  color: var(--primary-hover); margin-bottom: 8px;
}
.welcome-banner h2 { font-size: 24px; font-weight: 600; letter-spacing: -.6px; margin-bottom: 6px; }
.welcome-banner p { font-size: 13px; color: var(--muted); }
.welcome-art { position: absolute; right: 30px; top: 50%; transform: translateY(-50%); width: 150px; height: 110px; }
.orb { position: absolute; border-radius: 50%; }
.orb-1 { width: 90px; height: 90px; right: 0; top: 0; background: radial-gradient(circle, rgba(94,106,210,.16), transparent 70%); }
.orb-2 { width: 70px; height: 70px; right: 60px; bottom: 0; background: radial-gradient(circle, rgba(122,127,173,.12), transparent 70%); }
.art-emoji { position: absolute; right: 22px; top: 50%; transform: translateY(-50%); font-size: 46px; opacity: .85; animation: floaty 3.5s ease-in-out infinite; }

.stat-card { animation: riseIn .45s ease both; }

.chart-row { display: flex; align-items: center; gap: 12px; margin: 11px 0; transition: transform .2s; }
.chart-row:hover { transform: translateX(3px); }
.chart-label {
  width: 38px; color: var(--muted); font-size: 11.5px; font-weight: 700;
  background: var(--panel-2); border-radius: 6px; padding: 3px 0; text-align: center;
}
.chart-bars {
  flex: 1; display: flex; height: 16px; background: var(--panel-2); border-radius: 6px;
  overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,.05);
}
.bar { height: 100%; transition: width .5s cubic-bezier(.4,0,.2,1); }
.bar.pass { background: linear-gradient(90deg, #16b981, #34d399); }
.bar.fail { background: linear-gradient(90deg, #f2566b, #fb7185); }
.chart-num { width: 52px; text-align: right; font-size: 12px; color: var(--muted); font-weight: 600; }

.quick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.quick {
  border: 1px solid var(--border); border-radius: 13px; padding: 18px;
  display: flex; flex-direction: column; gap: 4px;
  transition: all .25s cubic-bezier(.4,0,.2,1); position: relative; overflow: hidden;
}
.quick::before {
  content: ''; position: absolute; inset: 0; opacity: 0;
  background: linear-gradient(135deg, rgba(91,107,245,.07), rgba(139,92,246,.07));
  transition: opacity .25s;
}
.quick:hover { border-color: var(--primary); transform: translateY(-3px); box-shadow: var(--shadow-hover); }
.quick:hover::before { opacity: 1; }
.quick span { font-size: 26px; transition: transform .25s; }
.quick:hover span { transform: scale(1.15) rotate(-6deg); }
.quick b { font-size: 14px; margin-top: 6px; position: relative; }
.quick small { color: var(--muted); font-size: 12px; position: relative; }
</style>
