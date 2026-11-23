<template>
  <div class="row" style="align-items:flex-start">
    <div class="col">
      <div class="panel">
        <div class="panel-head"><h2>🌐 UI 自动化 · 流程编排</h2><button class="btn btn-sm" @click="addFlow">＋ 新建流程</button></div>
        <div class="panel-body">
          <div class="framework-pick">
            <span class="pick-label">目标框架</span>
            <div class="pick-options">
              <button v-for="opt in FRAMEWORKS" :key="opt.value" class="pick-chip"
                :class="{ active: framework === opt.value }" @click="framework = opt.value">
                <span class="pick-icon">{{ opt.icon }}</span>
                <span>{{ opt.label }}</span>
              </button>
            </div>
          </div>

          <div v-for="(f, fi) in flows" :key="fi" class="flow-card">
            <div class="flow-head">
              <span class="flow-no">流程 {{ fi + 1 }}</span>
              <input class="input flow-title" v-model="f.title" placeholder="流程标题，如：登录后跳转工作台" />
              <div class="flow-ops">
                <button class="icon-btn" @click="moveFlow(fi, -1)" :disabled="fi === 0" title="上移（提前执行）">↑</button>
                <button class="icon-btn" @click="moveFlow(fi, 1)" :disabled="fi === flows.length - 1" title="下移（延后执行）">↓</button>
                <button class="icon-btn danger" @click="flows.splice(fi, 1)" title="删除流程">×</button>
              </div>
            </div>

            <div v-for="(s, si) in f.steps" :key="si" class="step-row">
              <span class="step-no">{{ si + 1 }}</span>
              <select class="select act-sel" v-model="s.action">
                <option v-for="(meta, key) in ACTIONS" :key="key" :value="key">{{ meta.label }}</option>
              </select>
              <input class="input target-in" v-if="needsTarget(s.action)" v-model="s.target" :placeholder="targetHint(s.action)" />
              <input class="input value-in" v-if="needsValue(s.action)" v-model="s.value" :placeholder="valueHint(s.action)" />
              <div class="step-ops">
                <button class="icon-btn" @click="moveStep(f, si, -1)" :disabled="si === 0" title="上移">↑</button>
                <button class="icon-btn" @click="moveStep(f, si, 1)" :disabled="si === f.steps.length - 1" title="下移">↓</button>
                <button class="icon-btn danger" @click="f.steps.splice(si, 1)" title="删除步骤">×</button>
              </div>
            </div>
            <div v-if="!f.steps.length" class="empty" style="padding:14px">还没有步骤，点击下方添加</div>

            <div style="margin-top:10px;display:flex;gap:8px">
              <button class="btn btn-sm" @click="addStep(f)">＋ 添加步骤</button>
            </div>
          </div>

          <div v-if="!flows.length" class="empty"><div class="big">🧩</div>点击右上角「新建流程」开始编排</div>

          <div style="margin-top:14px;display:flex;gap:10px;align-items:center">
            <button class="btn btn-primary" @click="generate" :disabled="generating || !flows.length">
              {{ generating ? '生成中...' : '🤖 生成并下载' }}
            </button>
            <span class="muted" style="font-size:12.5px">共 {{ flows.length }} 个流程 / {{ totalSteps }} 个步骤，生成 {{ currentFramework.label }} 可运行项目（zip）</span>
          </div>
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel">
        <div class="panel-head"><h2>编排说明</h2></div>
        <div class="panel-body">
          <div class="tip-card">
            <b>支持的动作</b>
            <table class="mini-table">
              <thead><tr><th>动作</th><th>填写说明</th></tr></thead>
              <tbody>
                <tr v-for="(meta, key) in ACTIONS" :key="key"><td><code>{{ meta.label }}</code></td><td>{{ meta.hint }}</td></tr>
              </tbody>
            </table>
          </div>
          <div class="tip-card">
            <b>目标定位写法</b>（点击 / 输入的 target）
            <ul class="tips">
              <li>CSS 选择器：<code>button.submit</code>、<code>input[type="password"]</code></li>
              <li>XPath：<code>//button[@class='login']</code></li>
              <li>按文本：<code>text=登 录</code>，或直接填页面上的文字如 <code>提交</code></li>
            </ul>
          </div>
          <div class="tip-card">
            <b>统一能力（三个框架都包含）</b>
            <ul class="tips">
              <li><b>执行顺序</b>：用流程卡上的 ↑↓ 排序，生成时按此顺序标记</li>
              <li><b>失败重试</b>：默认失败自动重跑 2 次，可改配置</li>
              <li><b>失败截图</b>：失败时自动截图附到报告</li>
              <li><b>录屏</b>：全程录制（Playwright webm / Selenium·Robot GIF）</li>
            </ul>
          </div>
          <div class="tip-card">
            <b>当前框架：{{ currentFramework.label }}</b>
            <div style="color:var(--text-secondary,#6b7280);margin-top:4px">{{ currentFramework.desc }}</div>
          </div>
          <div class="tip-card" v-if="framework === 'playwright_pytest'">
            <b>生成的项目结构</b>（沿用你的框架模板）
            <pre class="tree" v-pre>config.py            # 目标URL / Basic认证 / headless 开关
pytest.ini / main.py  # 框架原样（allure 报告入口）
conftest.py           # 框架原样（接管 page/browser fixture）
Tools/*               # 日志 / YAML 读取（框架原样）
Pages/flow_N_page.py  # 每个流程一个 Page 类（元素定位+步骤方法）
testcase/flow_Ncase/  # 测试用例（parametrize 数据驱动）
testdata/flow_N.yaml  # 流程标题与可变值，改值无需改代码</pre>
          </div>
          <div class="tip-card" v-else-if="framework === 'selenium_pytest'">
            <b>生成的项目结构</b>（标准 Selenium 4）
            <pre class="tree" v-pre>config.py            # 目标URL / headless / 等待配置
conftest.py           # driver fixture + 失败截图 + Allure
pytest.ini / main.py  # pytest 配置 + allure 报告入口
Pages/base_page.py    # 通用操作与断言封装
Pages/flow_N_page.py  # 每个流程一个 Page 类
testcase/flow_Ncase/  # 测试用例（parametrize 数据驱动）
testdata/flow_N.yaml  # 可变值，改值无需改代码</pre>
          </div>
          <div class="tip-card" v-else>
            <b>生成的项目结构</b>（Robot Framework）
            <pre class="tree" v-pre>common.resource       # SeleniumLibrary + 浏览器开关关键字
testcases/flow_N.robot        # 每个流程一个测试套件
testcases/flow_N_data.resource # 该流程的可变值
requirements.txt      # robotframework + SeleniumLibrary</pre>
          </div>
          <div class="tip-card">
            <b>如何运行</b>
            <pre class="tree">{{ currentFramework.run }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { api, notify } from '../api'
import { token } from '../auth'
import { useRoute } from 'vue-router'

const ACTIONS = {
  goto: { label: '打开网页', hint: 'value 填目标 URL' },
  click: { label: '点击元素', hint: 'target 填选择器（CSS/XPath/text=）' },
  input: { label: '输入内容', hint: 'target 填选择器，value 填输入值' },
  assert_text: { label: '断言页面文本', hint: 'target 填期望出现的文本' },
  assert_url_contains: { label: '断言地址包含', hint: 'value 填地址片段' },
  assert_title: { label: '断言页面标题', hint: 'value 填标题片段' },
  wait: { label: '等待', hint: 'value 填秒数' },
}

const FRAMEWORKS = [
  {
    value: 'playwright_pytest', label: 'Python + Playwright', icon: '⚡',
    desc: '沿用你的框架模板，Page Object + allure，已稳定使用。',
    run: 'pip install -r requirements.txt\nplaywright install chromium\npytest testcase                # 有头执行\nUI_HEADLESS=true pytest        # 无头执行\npython main.py                 # allure 报告',
  },
  {
    value: 'selenium_pytest', label: 'Python + Selenium', icon: '🐍',
    desc: '标准 Selenium 4 + pytest，Selenium Manager 自动匹配驱动。',
    run: 'pip install -r requirements.txt\npytest testcase                    # 默认无头\nUI_HEADLESS=false pytest testcase  # 有头观察\nCHROMEDRIVER_PATH=/path/to/chromedriver pytest  # 离线指定驱动',
  },
  {
    value: 'robot_framework', label: 'Robot Framework', icon: '🤖',
    desc: '关键字驱动，步骤直接映射 SeleniumLibrary 关键字。',
    run: 'pip install -r requirements.txt\nrobot testcases/                              # 默认无头\nrobot --variable HEADLESS:false testcases/    # 有头观察',
  },
]

const route = useRoute()
const flows = ref([])
const generating = ref(false)
const framework = ref(FRAMEWORKS[0].value)
const currentFramework = computed(() => FRAMEWORKS.find(f => f.value === framework.value) || FRAMEWORKS[0])

const totalSteps = computed(() => flows.value.reduce((n, f) => n + f.steps.length, 0))

function blankStep() { return { action: 'goto', target: '', value: '' } }
function addFlow() {
  flows.value.push({ title: '', steps: [blankStep()] })
}
function moveFlow(fi, dir) {
  const j = fi + dir
  if (j < 0 || j >= flows.value.length) return
  const [f] = flows.value.splice(fi, 1)
  flows.value.splice(j, 0, f)
}
function addStep(f) { f.steps.push({ action: 'click', target: '', value: '' }) }
function moveStep(f, si, dir) {
  const j = si + dir
  if (j < 0 || j >= f.steps.length) return
  const [s] = f.steps.splice(si, 1)
  f.steps.splice(j, 0, s)
}
function needsTarget(a) { return ['click', 'input', 'assert_text'].includes(a) }
function needsValue(a) { return ['goto', 'input', 'assert_url_contains', 'assert_title', 'wait'].includes(a) }
function targetHint(a) {
  return ({ click: '目标定位，如 button.submit 或 text=登录', input: '输入框定位，如 input[type="password"]', assert_text: '期望出现的文本' })[a] || ''
}
function valueHint(a) {
  return ({ goto: 'https://example.com', input: '要输入的内容', assert_url_contains: '地址片段，如 dashboard', assert_title: '标题片段', wait: '秒数，如 2' })[a] || ''
}

function validate() {
  for (let i = 0; i < flows.value.length; i++) {
    const f = flows.value[i]
    if (!f.title.trim()) { notify(`第 ${i + 1} 个流程缺少标题`, 'error'); return false }
    if (!f.steps.length) { notify(`流程「${f.title}」没有步骤`, 'error'); return false }
    for (let j = 0; j < f.steps.length; j++) {
      const s = f.steps[j]
      const t = (s.target || '').trim(), v = (s.value || '').trim()
      if (s.action === 'goto' && !v) { notify(`流程${i + 1} 步骤${j + 1}：请填写 URL`, 'error'); return false }
      if (s.action === 'click' && !t) { notify(`流程${i + 1} 步骤${j + 1}：请填写目标定位`, 'error'); return false }
      if (s.action === 'input' && (!t || !v)) { notify(`流程${i + 1} 步骤${j + 1}：请填写定位和输入值`, 'error'); return false }
      if (s.action === 'assert_text' && !t) { notify(`流程${i + 1} 步骤${j + 1}：请填写期望文本`, 'error'); return false }
      if ((s.action === 'assert_url_contains' || s.action === 'assert_title') && !v) { notify(`流程${i + 1} 步骤${j + 1}：请填写期望值`, 'error'); return false }
      if (s.action === 'wait' && (isNaN(Number(v)) || v === '')) { notify(`流程${i + 1} 步骤${j + 1}：等待秒数必须是数字`, 'error'); return false }
    }
  }
  return true
}

async function generate() {
  if (!validate()) return
  generating.value = true
  try {
    const headers = { 'Content-Type': 'application/json' }
    if (token.value) headers['Authorization'] = `Bearer ${token.value}`
    const resp = await fetch('/api/ui/autogen', {
      method: 'POST', headers,
      body: JSON.stringify({ flows: flows.value, framework: framework.value }),
    })
    if (!resp.ok) { let m = resp.statusText; try { m = (await resp.json()).detail || m } catch (e) {} throw new Error(m) }
    const blob = await resp.blob()
    const cd = resp.headers.get('Content-Disposition') || ''
    let name = 'ui_flow_autotest.zip'
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
  finally { generating.value = false }
}

// 初始：默认给一个空流程；支持 ?flow_title= 预填标题
addFlow()
const preTitle = route.query.flow_title
if (preTitle && flows.value[0]) flows.value[0].title = String(preTitle)
</script>

<style scoped>
.framework-pick { margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid var(--border); }
.pick-label { display: block; font-size: 12.5px; font-weight: 500; color: var(--text-secondary, var(--muted)); margin-bottom: 9px; }
.pick-options { display: flex; gap: 10px; flex-wrap: wrap; }
.pick-chip {
  display: flex; align-items: center; gap: 8px; padding: 9px 14px;
  border: 1.5px solid var(--border); border-radius: 10px; background: var(--panel);
  font-size: 13px; color: var(--text-primary, var(--text)); cursor: pointer;
  transition: all .18s;
}
.pick-chip:hover { border-color: var(--primary); }
.pick-chip.active { border-color: var(--primary); background: var(--primary-light, var(--primary-light)); box-shadow: 0 0 0 3px rgba(91,107,245,.1); }
.pick-icon { font-size: 15px; }
.flow-card { border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; margin-bottom: 14px; background: var(--panel-2); }
.flow-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.flow-no { font-size: 12.5px; font-weight: 600; color: var(--primary); background: var(--primary-light); padding: 4px 10px; border-radius: 6px; flex-shrink: 0; }
.flow-title { flex: 1; font-weight: 500; }
.flow-ops { display: flex; gap: 4px; flex-shrink: 0; }
.step-row { display: flex; align-items: center; gap: 8px; padding: 7px 0; }
.step-no { width: 24px; height: 24px; border-radius: 50%; background: var(--primary-light); color: var(--primary); display: grid; place-items: center; font-size: 11.5px; flex-shrink: 0; }
.act-sel { width: 128px; flex-shrink: 0; }
.target-in { flex: 1.4; min-width: 0; }
.value-in { flex: 1; min-width: 0; }
.step-ops { display: flex; gap: 4px; flex-shrink: 0; }
.icon-btn {
  width: 26px; height: 26px; border: 1px solid var(--border); background: var(--panel); border-radius: 6px;
  cursor: pointer; font-size: 13px; color: var(--muted); display: grid; place-items: center; line-height: 1;
  transition: all .15s;
}
.icon-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.icon-btn:disabled { opacity: .35; cursor: not-allowed; }
.icon-btn.danger:hover { border-color: var(--danger); color: var(--danger); }
.tip-card { background: var(--panel-2); border: 1px solid var(--border); border-radius: 10px; padding: 13px 15px; margin-bottom: 12px; font-size: 12.5px; line-height: 1.7; }
.tip-card b { display: block; margin-bottom: 7px; color: var(--text); }
.tips { margin: 0; padding-left: 18px; }
.tip-card code { background: rgba(79,95,224,.08); color: var(--primary); padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.mini-table { width: 100%; border-collapse: collapse; }
.mini-table th, .mini-table td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--border); font-weight: 400; }
.mini-table th { font-size: 11.5px; color: var(--ink-tertiary); }
.tree { background: var(--text); color: #c9d4f2; padding: 12px 14px; border-radius: 8px; font-size: 11.5px; line-height: 1.75; overflow-x: auto; }
</style>
