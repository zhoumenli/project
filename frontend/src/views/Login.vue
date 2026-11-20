<template>
  <div class="auth-page">
    <!-- 动态背景层 -->
    <div class="bg-layer" aria-hidden="true">
      <div class="blob b1"></div>
      <div class="blob b2"></div>
      <div class="blob b3"></div>
      <div class="grid-mask"></div>
      <div class="float-shapes">
        <span class="fs s1">◆</span>
        <span class="fs s2">●</span>
        <span class="fs s3">▲</span>
        <span class="fs s4">■</span>
        <span class="fs s5">✦</span>
        <span class="fs s6">○</span>
      </div>
      <div class="sweep"></div>
    </div>

    <div class="auth-card">
      <div class="card-glow"></div>
      <router-link to="/" class="back">← 返回首页</router-link>
      <div class="auth-logo"><span class="mark">⚡</span> 测试提效平台</div>
      <h2>登录账号</h2>
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
        </button>
      </form>

      <div class="auth-foot">还没有账号？<router-link to="/register">立即注册</router-link></div>
      <div class="demo-tip">演示账号：<code>testuser</code> / <code>Test@1234</code></div>
    </div>
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
  background: linear-gradient(160deg, #eef1fb 0%, #f6f4fd 45%, #eef6fb 100%);
  padding: 20px; position: relative;
}

/* ============ 动态背景 ============ */
.bg-layer { position: absolute; inset: 0; z-index: 0; pointer-events: none; }

/* 渐变光斑：缓慢漂移 */
.blob { position: absolute; border-radius: 50%; filter: blur(70px); opacity: .5; will-change: transform; }
.b1 { width: 46vw; height: 46vw; left: -10vw; top: -12vw; background: radial-gradient(circle, #8b9bff 0%, transparent 70%); animation: drift1 22s ease-in-out infinite alternate; }
.b2 { width: 40vw; height: 40vw; right: -8vw; top: 18vh; background: radial-gradient(circle, #7fd4c4 0%, transparent 70%); animation: drift2 26s ease-in-out infinite alternate; }
.b3 { width: 38vw; height: 38vw; left: 24vw; bottom: -14vw; background: radial-gradient(circle, #c79bff 0%, transparent 70%); animation: drift3 24s ease-in-out infinite alternate; }
@keyframes drift1 { from { transform: translate(0, 0) scale(1); } to { transform: translate(9vw, 7vh) scale(1.15); } }
@keyframes drift2 { from { transform: translate(0, 0) scale(1); } to { transform: translate(-8vw, -6vh) scale(.9); } }
@keyframes drift3 { from { transform: translate(0, 0) scale(1); } to { transform: translate(6vw, -8vh) scale(1.1); } }

/* 网格底纹 */
.grid-mask {
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(79, 95, 224, .05) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(79, 95, 224, .05) 1px, transparent 1px);
  background-size: 42px 42px;
  -webkit-mask-image: radial-gradient(ellipse 70% 65% at 50% 45%, #000 40%, transparent 100%);
          mask-image: radial-gradient(ellipse 70% 65% at 50% 45%, #000 40%, transparent 100%);
}

/* 浮动几何体 */
.float-shapes { position: absolute; inset: 0; }
.fs { position: absolute; color: rgba(79, 95, 224, .16); font-size: 16px; animation: floaty 9s ease-in-out infinite alternate; will-change: transform; }
.s1 { left: 12%; top: 20%; animation-duration: 8s; }
.s2 { left: 78%; top: 16%; font-size: 12px; color: rgba(46, 173, 154, .2); animation-duration: 11s; }
.s3 { left: 8%;  top: 68%; font-size: 13px; color: rgba(167, 109, 224, .18); animation-duration: 10s; }
.s4 { left: 86%; top: 62%; font-size: 15px; color: rgba(79, 95, 224, .14); animation-duration: 9.5s; }
.s5 { left: 30%; top: 10%; font-size: 11px; color: rgba(167, 109, 224, .22); animation-duration: 12s; }
.s6 { left: 64%; top: 78%; font-size: 17px; color: rgba(46, 173, 154, .15); animation-duration: 10.5s; }
@keyframes floaty {
  from { transform: translateY(-12px) rotate(-8deg); opacity: .55; }
  to   { transform: translateY(14px)  rotate(10deg);  opacity: 1; }
}

/* 高光扫过 */
.sweep {
  position: absolute; inset: -40%;
  background: linear-gradient(115deg, transparent 42%, rgba(255,255,255,.5) 50%, transparent 58%);
  animation: sweep 9s ease-in-out infinite;
}
@keyframes sweep { 0% { transform: translateX(-45%); } 55%, 100% { transform: translateX(45%); } }

/* ============ 登录卡片（玻璃拟态） ============ */
.auth-card {
  width: 100%; max-width: 408px; position: relative; z-index: 2;
  background: rgba(255, 255, 255, .78);
  -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px);
  border: 1px solid rgba(255, 255, 255, .65);
  border-radius: 18px; padding: 38px 36px 30px;
  box-shadow: 0 18px 48px -12px rgba(52, 64, 128, .18), 0 2px 8px rgba(52, 64, 128, .06);
  animation: cardIn .5s cubic-bezier(.22, 1, .36, 1) both;
}
@keyframes cardIn { from { opacity: 0; transform: translateY(22px) scale(.97); } to { opacity: 1; transform: none; } }

/* 顶部渐变饰条 */
.card-glow {
  position: absolute; top: 0; left: 24px; right: 24px; height: 3px; border-radius: 0 0 4px 4px;
  background: linear-gradient(90deg, #4f5fe0, #7fd4c4, #c79bff);
  background-size: 200% 100%; animation: glowShift 6s linear infinite;
}
@keyframes glowShift { to { background-position: 200% 0; } }

.back { position: absolute; top: 18px; right: 22px; font-size: 12.5px; color: #7d8598; text-decoration: none; transition: color .18s, transform .18s; }
.back:hover { color: #0f1420; transform: translateX(-2px); }

.auth-logo {
  font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 9px;
  margin-bottom: 30px; letter-spacing: .01em; color: #0f1420;
}
.auth-logo .mark {
  width: 30px; height: 30px; border-radius: 8px;
  background: linear-gradient(135deg, #4f5fe0, #8b6fe8);
  color: #fff; display: grid; place-items: center; font-size: 15px;
  box-shadow: 0 4px 12px rgba(79, 95, 224, .35);
}
.auth-card h2 { font-size: 23px; font-weight: 700; margin-bottom: 6px; letter-spacing: -.02em; color: #0f1420; }
.auth-sub { color: #7d8598; font-size: 13.5px; margin-bottom: 26px; }

.field { margin-bottom: 17px; }
.field label { display: block; font-size: 12.5px; color: #57606f; margin-bottom: 7px; font-weight: 500; }
.input-wrap { position: relative; }
.field-icon {
  position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
  font-size: 13px; opacity: .55; transition: opacity .18s, transform .18s; pointer-events: none;
}
.input-wrap:focus-within .field-icon { opacity: 1; transform: translateY(-50%) scale(1.12); }

.input {
  width: 100%; padding: 11px 13px; border: 1.5px solid #e2e6ef; border-radius: 10px;
  font-size: 14px; background: rgba(255, 255, 255, .85); color: #0f1420;
  transition: border-color .18s, box-shadow .18s, background .18s;
}
.input.has-icon { padding-left: 36px; }
.input.has-eye { padding-right: 40px; }

.eye {
  position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
  width: 30px; height: 30px; border: none; background: transparent; border-radius: 7px;
  font-size: 15px; cursor: pointer; line-height: 1;
  display: grid; place-items: center;
  transition: background .15s, transform .15s;
}
.eye:hover { background: rgba(79, 95, 224, .08); transform: translateY(-50%) scale(1.08); }
.eye:active { transform: translateY(-50%) scale(.95); }
.input::placeholder { color: #b4bac8; }
.input:hover { border-color: #c9d0e2; }
.input:focus { outline: none; border-color: #4f5fe0; background: #fff; box-shadow: 0 0 0 4px rgba(79,95,224,.12); }

.err {
  background: #fdf0f1; color: #d13b4f; padding: 10px 12px; border-radius: 8px;
  font-size: 12.5px; margin-bottom: 15px; animation: shake .35s ease;
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); } 50% { transform: translateX(5px); } 75% { transform: translateX(-3px); }
}

.notice {
  padding: 10px 12px; border-radius: 8px; font-size: 12.5px; margin-bottom: 15px;
  background: #fff8e8; color: #9a6d1b; border: 1px solid #f0e2c4;
}
.notice.info { background: #eef1ff; color: #4f5fe0; border-color: #dcdff8; }

.submit {
  width: 100%; padding: 12px; border: none; border-radius: 10px; cursor: pointer;
  background: linear-gradient(135deg, #4f5fe0 0%, #7a5ce8 100%);
  background-size: 150% 100%;
  color: #fff; font-size: 14.5px; font-weight: 600; letter-spacing: .12em;
  display: flex; align-items: center; justify-content: center; gap: 9px;
  box-shadow: 0 8px 20px -6px rgba(79, 95, 224, .5);
  transition: transform .18s, box-shadow .18s, background-position .3s;
}
.submit:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 12px 26px -6px rgba(79, 95, 224, .6); background-position: 100% 0; }
.submit:active:not(:disabled) { transform: translateY(0); }
.submit:disabled { opacity: .65; cursor: wait; }

.spinner {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid rgba(255,255,255,.4); border-top-color: #fff;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.auth-foot { text-align: center; margin-top: 22px; font-size: 13px; color: #7d8598; }
.auth-foot a { color: #4f5fe0; font-weight: 500; }

.demo-tip {
  margin-top: 16px; text-align: center; font-size: 12px; color: #98a0b0;
  border-top: 1px dashed #e3e7f0; padding-top: 14px;
}
.demo-tip code { color: #4f5fe0; font-weight: 500; background: rgba(79,95,224,.07); padding: 1px 6px; border-radius: 5px; }

/* 用户偏好减少动效 */
@media (prefers-reduced-motion: reduce) {
  .blob, .fs, .sweep, .card-glow, .auth-card { animation: none !important; }
}
</style>
