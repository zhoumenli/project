<template>
  <div class="auth-page">
    <!-- ============ 动态场景层 ============ -->
    <div class="bg-layer" aria-hidden="true">
      <div class="deep-sky"></div>
      <div class="aurora a1"></div>
      <div class="aurora a2"></div>
      <div class="aurora a3"></div>
      <div class="aurora a4"></div>

      <!-- 雷达圆环（卡片背后透出） -->
      <svg class="radar" viewBox="0 0 800 800" xmlns="http://www.w3.org/2000/svg">
        <g fill="none" stroke="rgba(130,150,255,.13)">
          <circle cx="400" cy="400" r="350" stroke-width="1" stroke-dasharray="3 9" />
          <circle cx="400" cy="400" r="285" stroke-width="1" />
          <circle cx="400" cy="400" r="215" stroke-width="1" stroke-dasharray="2 7" />
          <circle cx="400" cy="400" r="140" stroke-width="1" />
          <path d="M400 20 V780 M20 400 H780" stroke-width="1" stroke-dasharray="2 12" />
          <path d="M400 60 L400 110 M400 690 L400 740 M60 400 L110 400 M690 400 L740 400" stroke-width="2" />
        </g>
        <g class="radar-nodes">
          <circle cx="400" cy="115" r="5" fill="#7c8cff" class="node n1" />
          <circle cx="615" cy="400" r="4" fill="#22d3ee" class="node n2" />
          <circle cx="400" cy="685" r="4" fill="#c084fc" class="node n3" />
          <circle cx="185" cy="400" r="5" fill="#7c8cff" class="node n4" />
          <circle cx="545" cy="255" r="3" fill="#22d3ee" class="node n5" />
          <circle cx="245" cy="555" r="3" fill="#c084fc" class="node n6" />
        </g>
        <path class="sweep-arm" d="M400 400 L400 50 A350 350 0 0 1 640 160 Z" fill="url(#sweepGrad)" />
        <defs>
          <linearGradient id="sweepGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="rgba(124,140,255,.18)" />
            <stop offset="100%" stop-color="rgba(124,140,255,0)" />
          </linearGradient>
        </defs>
      </svg>

      <!-- 星尘粒子 -->
      <div class="stars">
        <span v-for="(p, i) in particles" :key="i" class="star" :style="p"></span>
      </div>

      <!-- 透视网格地平线 -->
      <div class="horizon"><div class="hgrid"></div></div>

      <div class="scanline"></div>
      <div class="vignette"></div>
    </div>

    <!-- ============ 登录卡片 ============ -->
    <div class="auth-card">
      <div class="card-border"></div>
      <router-link to="/" class="back">← 返回首页</router-link>

      <div class="auth-logo"><span class="mark">⚡</span> 测试提效平台</div>
      <div class="title-row">
        <h2>登录账号</h2>
        <span class="title-line"></span>
      </div>
      <p class="auth-sub">登录后即可访问平台全部功能</p>

      <div v-if="notice" class="notice" :class="{ warn: noticeType === 'warn' }">{{ notice }}</div>

      <form @submit.prevent="submit">
        <div class="field">
          <label>用户名</label>
          <div class="input-wrap">
            <span class="field-icon">👤</span>
            <input class="input has-icon" v-model="form.username" autocomplete="username" placeholder="请输入用户名" />
          </div>
        </div>
        <div class="field">
          <label>密码</label>
          <div class="input-wrap">
            <span class="field-icon">🔒</span>
            <input class="input has-icon has-eye" :type="showPwd ? 'text' : 'password'" v-model="form.password" autocomplete="current-password" placeholder="请输入密码" />
            <button type="button" class="eye" @click="showPwd = !showPwd" :title="showPwd ? '隐藏密码' : '显示密码'" :aria-label="showPwd ? '隐藏密码' : '显示密码'">{{ showPwd ? '🙈' : '👁' }}</button>
          </div>
        </div>
        <div v-if="error" class="err">{{ error }}</div>
        <button class="submit" type="submit" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '登录中...' : '登 录' }}
          <span class="btn-arrow">→</span>
        </button>
      </form>

      <div class="auth-foot">还没有账号？<router-link to="/register">立即注册</router-link></div>
      <div class="demo-tip">演示账号：<code>testuser</code> / <code>Test@1234</code></div>
    </div>

    <div class="corner-tag">TEST EFFICIENCY PLATFORM · v1.0</div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api, notify } from '../api'
import { setSession } from '../auth'

const router = useRouter()
const route = useRoute()
const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)
const showPwd = ref(false)

// 星尘粒子：位置/大小/动画错开，营造景深
const particles = Array.from({ length: 26 }, (_, i) => ({
  left: (i * 37 + 7) % 100 + '%',
  top: (i * 53 + 13) % 100 + '%',
  width: (i % 4 === 0 ? 3 : i % 3 === 0 ? 2 : 1.5) + 'px',
  height: (i % 4 === 0 ? 3 : i % 3 === 0 ? 2 : 1.5) + 'px',
  animationDelay: (i % 9) * 0.7 + 's',
  animationDuration: (4 + (i % 6) * 1.3) + 's',
  opacity: 0.25 + (i % 5) * 0.12,
}))

// 被自动登出后跳转回登录页时，说明原因
const notice = computed(() => {
  if (route.query.reason === 'idle') return '长时间未操作（超过 30 分钟），已自动退出登录，请重新登录'
  if (route.query.reason === 'expired') return '登录已过期，请重新登录'
  return ''
})
const noticeType = computed(() => (route.query.reason === 'idle' || route.query.reason === 'expired') ? 'warn' : 'info')

async function submit() {
  error.value = ''
  if (!form.value.username || !form.value.password) { error.value = '请填写用户名和密码'; return }
  loading.value = true
  try {
    const r = await api('/api/auth/login', { method: 'POST', body: form.value })
    setSession(r.token, r.user, r.idle_timeout)
    notify(`欢迎回来，${r.user.username}`)
    router.push(route.query.redirect || '/dashboard')
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh; display: grid; place-items: center; overflow: hidden;
  background: #070a18; padding: 20px; position: relative;
}

/* ============ 深空场景 ============ */
.bg-layer { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }

.deep-sky {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 90% 70% at 50% 110%, rgba(30, 64, 175, .45), transparent 70%),
    radial-gradient(ellipse 70% 60% at 10% 0%, rgba(76, 29, 149, .35), transparent 70%),
    radial-gradient(ellipse 60% 50% at 95% 15%, rgba(8, 145, 178, .22), transparent 70%),
    linear-gradient(165deg, #070a1c 0%, #0d1030 42%, #101a3a 72%, #07101f 100%);
}

/* 极光光带：screen 混合叠加，各自不同轨迹 */
.aurora { position: absolute; border-radius: 50%; filter: blur(85px); mix-blend-mode: screen; will-change: transform; }
.a1 { width: 55vw; height: 42vw; left: -14vw; top: -14vw; background: radial-gradient(ellipse at center, rgba(99,102,241,.75), transparent 66%); animation: au1 19s ease-in-out infinite alternate; }
.a2 { width: 48vw; height: 38vw; right: -12vw; top: 8vh;  background: radial-gradient(ellipse at center, rgba(168,85,247,.55), transparent 66%); animation: au2 24s ease-in-out infinite alternate; }
.a3 { width: 52vw; height: 34vw; left: 20vw; bottom: -12vw; background: radial-gradient(ellipse at center, rgba(6,182,212,.5), transparent 66%); animation: au3 21s ease-in-out infinite alternate; }
.a4 { width: 30vw; height: 30vw; right: 12vw; bottom: 6vh; background: radial-gradient(ellipse at center, rgba(236,72,153,.32), transparent 66%); animation: au4 27s ease-in-out infinite alternate; }
@keyframes au1 { from { transform: translate(0,0) scale(1); } to { transform: translate(11vw,8vh) scale(1.18); } }
@keyframes au2 { from { transform: translate(0,0) scale(1); } to { transform: translate(-9vw,10vh) scale(.85); } }
@keyframes au3 { from { transform: translate(0,0) scale(1); } to { transform: translate(-7vw,-7vh) scale(1.12); } }
@keyframes au4 { from { transform: translate(0,0) scale(1); } to { transform: translate(6vw,-11vh) scale(1.2); } }

/* 雷达圆环 */
.radar {
  position: absolute; width: min(850px, 95vh); height: min(850px, 95vh);
  left: 50%; top: 50%; transform: translate(-50%, -50%);
  opacity: .85; animation: radarSpin 60s linear infinite;
}
@keyframes radarSpin { to { transform: translate(-50%, -50%) rotate(360deg); } }
.sweep-arm { transform-origin: 400px 400px; animation: armSpin 8s linear infinite; }
@keyframes armSpin { to { transform: rotate(360deg); } }
.node { filter: drop-shadow(0 0 6px currentColor); }
.node.n1 { animation: nodePulse 3s ease-in-out infinite; }
.node.n2 { animation: nodePulse 3.6s ease-in-out .6s infinite; }
.node.n3 { animation: nodePulse 4.2s ease-in-out 1.2s infinite; }
.node.n4 { animation: nodePulse 3.3s ease-in-out 1.8s infinite; }
.node.n5 { animation: nodePulse 2.8s ease-in-out .3s infinite; }
.node.n6 { animation: nodePulse 3.9s ease-in-out .9s infinite; }
@keyframes nodePulse { 0%,100% { opacity: .35; r: 3; } 50% { opacity: 1; r: 5.5; } }

/* 星尘 */
.stars { position: absolute; inset: 0; }
.star {
  position: absolute; background: #c7d2fe; border-radius: 50%;
  box-shadow: 0 0 6px rgba(199,210,254,.9);
  animation: twinkle ease-in-out infinite alternate;
}
@keyframes twinkle { from { transform: translateY(0) scale(.7); } to { transform: translateY(-14px) scale(1.35); } }

/* 透视网格地面 */
.horizon {
  position: absolute; left: -30%; right: -30%; bottom: -12%; height: 58%;
  -webkit-mask-image: linear-gradient(to bottom, transparent, #000 55%, transparent);
          mask-image: linear-gradient(to bottom, transparent, #000 55%, transparent);
  opacity: .5;
}
.hgrid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(99,130,255,.42) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,130,255,.35) 1px, transparent 1px);
  background-size: 72px 72px;
  transform: perspective(320px) rotateX(66deg);
  transform-origin: center bottom;
  animation: gridFlow 3.2s linear infinite;
}
@keyframes gridFlow { to { background-position: 0 72px, 0 0; } }

/* 扫描线 + 暗角 */
.scanline {
  position: absolute; inset: 0;
  background: repeating-linear-gradient(to bottom, rgba(255,255,255,.018) 0 1px, transparent 1px 4px);
  animation: scanMove 12s linear infinite;
}
@keyframes scanMove { to { background-position: 0 400px; } }
.vignette { position: absolute; inset: 0; background: radial-gradient(ellipse 75% 70% at 50% 50%, transparent 30%, rgba(3,5,15,.72) 100%); }

/* ============ 深色玻璃登录卡 ============ */
.auth-card {
  width: 100%; max-width: 420px; position: relative; z-index: 2;
  background: linear-gradient(160deg, rgba(24,28,60,.82), rgba(14,18,42,.88));
  -webkit-backdrop-filter: blur(26px) saturate(140%); backdrop-filter: blur(26px) saturate(140%);
  border: 1px solid rgba(140,155,255,.22);
  border-radius: 20px; padding: 40px 38px 28px;
  box-shadow: 0 30px 80px -20px rgba(0,0,0,.65), 0 0 0 1px rgba(255,255,255,.03) inset,
              0 0 60px -20px rgba(99,102,241,.35);
  animation: cardIn .65s cubic-bezier(.22,1,.36,1) both;
}
@keyframes cardIn { from { opacity: 0; transform: translateY(26px) scale(.96); } to { opacity: 1; transform: none; } }

/* 渐变描边（顶部亮、两侧渐隐） */
.card-border {
  position: absolute; inset: -1px; border-radius: 20px; padding: 1px;
  background: linear-gradient(140deg, rgba(129,140,248,.85), rgba(34,211,238,.25) 35%, transparent 60%, rgba(192,132,252,.5));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  pointer-events: none;
}

.back { position: absolute; top: 18px; right: 22px; font-size: 12.5px; color: #8b96bd; text-decoration: none; transition: color .18s, transform .18s; }
.back:hover { color: #c7d2fe; transform: translateX(-2px); }

.auth-logo {
  font-size: 14.5px; font-weight: 600; display: flex; align-items: center; gap: 10px;
  margin-bottom: 26px; letter-spacing: .03em; color: #e6ebff;
}
.auth-logo .mark {
  width: 32px; height: 32px; border-radius: 9px;
  background: linear-gradient(135deg, #6366f1, #a855f7 60%, #06b6d4);
  color: #fff; display: grid; place-items: center; font-size: 16px;
  box-shadow: 0 0 20px rgba(124,92,255,.55);
}

.title-row { display: flex; align-items: center; gap: 14px; }
.auth-card h2 { font-size: 25px; font-weight: 700; margin-bottom: 8px; letter-spacing: -.01em; color: #f2f5ff; }
.title-line { flex: 1; height: 1px; margin-bottom: 8px; background: linear-gradient(90deg, rgba(129,140,248,.6), transparent); }
.auth-sub { color: #8e99c2; font-size: 13px; margin-bottom: 26px; }

.field { margin-bottom: 17px; }
.field label { display: block; font-size: 12px; color: #aab4d8; margin-bottom: 8px; font-weight: 500; letter-spacing: .03em; }
.input-wrap { position: relative; }
.field-icon {
  position: absolute; left: 13px; top: 50%; transform: translateY(-50%);
  font-size: 14px; opacity: .6; transition: opacity .18s, transform .18s; pointer-events: none;
}
.input-wrap:focus-within .field-icon { opacity: 1; transform: translateY(-50%) scale(1.14); }

.input {
  width: 100%; padding: 12px 14px; border: 1px solid rgba(140,155,255,.2); border-radius: 11px;
  font-size: 14px; background: rgba(8,12,32,.55); color: #eef2ff;
  transition: border-color .2s, box-shadow .2s, background .2s;
}
.input.has-icon { padding-left: 39px; }
.input.has-eye { padding-right: 42px; }
.input::placeholder { color: #5f6a91; }
.input:hover { border-color: rgba(140,155,255,.4); }
.input:focus {
  outline: none; border-color: #7c8cff; background: rgba(10,14,38,.8);
  box-shadow: 0 0 0 4px rgba(124,140,255,.14), 0 0 22px -6px rgba(124,140,255,.5);
}
.eye {
  position: absolute; right: 7px; top: 50%; transform: translateY(-50%);
  width: 30px; height: 30px; border: none; background: transparent; border-radius: 7px;
  font-size: 15px; cursor: pointer; line-height: 1; display: grid; place-items: center;
  transition: background .15s, transform .15s;
}
.eye:hover { background: rgba(124,140,255,.14); transform: translateY(-50%) scale(1.08); }
.eye:active { transform: translateY(-50%) scale(.95); }

.err {
  background: rgba(190,40,70,.18); color: #ff9db1; padding: 10px 12px; border-radius: 9px;
  border: 1px solid rgba(255,120,150,.25); font-size: 12.5px; margin-bottom: 15px;
  animation: shake .35s ease;
}
@keyframes shake {
  0%,100% { transform: translateX(0); }
  25% { transform: translateX(-5px); } 50% { transform: translateX(5px); } 75% { transform: translateX(-3px); }
}

.notice {
  padding: 10px 12px; border-radius: 9px; font-size: 12.5px; margin-bottom: 15px;
  background: rgba(234,179,8,.12); color: #fcd34d; border: 1px solid rgba(234,179,8,.28);
}
.notice.info { background: rgba(99,102,241,.14); color: #a5b4fc; border-color: rgba(129,140,248,.3); }

.submit {
  width: 100%; padding: 13px; border: none; border-radius: 11px; cursor: pointer;
  background: linear-gradient(110deg, #4f46e5, #8b5cf6 45%, #06b6d4);
  background-size: 200% 100%; color: #fff; font-size: 14.5px; font-weight: 600; letter-spacing: .16em;
  display: flex; align-items: center; justify-content: center; gap: 9px;
  box-shadow: 0 10px 28px -8px rgba(99,102,241,.75), 0 0 0 1px rgba(255,255,255,.1) inset;
  transition: transform .18s, box-shadow .18s, background-position .4s;
}
.btn-arrow { font-size: 17px; font-weight: 400; transition: transform .2s; }
.submit:hover:not(:disabled) { transform: translateY(-2px); background-position: 100% 0; box-shadow: 0 16px 34px -8px rgba(124,92,255,.9); }
.submit:hover:not(:disabled) .btn-arrow { transform: translateX(4px); }
.submit:active:not(:disabled) { transform: translateY(0); }
.submit:disabled { opacity: .6; cursor: wait; }

.spinner {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid rgba(255,255,255,.4); border-top-color: #fff;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.auth-foot { text-align: center; margin-top: 22px; font-size: 12.5px; color: #8e99c2; }
.auth-foot a { color: #a5b4fc; font-weight: 500; }
.auth-foot a:hover { color: #c7d2fe; }

.demo-tip {
  margin-top: 18px; text-align: center; font-size: 11.5px; color: #6d78a0;
  border-top: 1px solid rgba(140,155,255,.14); padding-top: 15px;
}
.demo-tip code { color: #a5b4fc; font-weight: 500; background: rgba(124,140,255,.12); padding: 2px 6px; border-radius: 5px; }

.corner-tag {
  position: absolute; bottom: 18px; right: 24px; z-index: 2;
  font-size: 10px; letter-spacing: .18em; color: rgba(160,175,230,.35);
}

@media (prefers-reduced-motion: reduce) {
  .aurora, .radar, .sweep-arm, .node, .star, .hgrid, .scanline, .auth-card { animation: none !important; }
}
</style>
