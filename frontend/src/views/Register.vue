<template>
  <div class="auth-page">
    <div class="auth-card wide">
      <router-link to="/" class="back">← 返回首页</router-link>
      <div class="auth-logo"><span class="mark">⚡</span> 测试提效平台</div>
      <h2>注册账号</h2>
      <p class="auth-sub">创建账号后即可使用平台全部功能</p>

      <form @submit.prevent="submit">
        <div class="field">
          <label>用户名</label>
          <input class="input" v-model="form.username" autocomplete="username" placeholder="3-20 位字母、数字或下划线" />
        </div>
        <div class="field">
          <label>密码</label>
          <div class="input-wrap">
            <input class="input has-eye" :type="showPwd ? 'text' : 'password'" v-model="form.password" autocomplete="new-password" placeholder="8-32 位，需包含大小写字母和数字" />
            <button type="button" class="eye" @click="showPwd = !showPwd" :title="showPwd ? '隐藏密码' : '显示密码'">{{ showPwd ? '🙈' : '👁' }}</button>
          </div>
        </div>
        <div class="field">
          <label>确认密码</label>
          <div class="input-wrap">
            <input class="input has-eye" :type="showConfirm ? 'text' : 'password'" v-model="form.confirm" autocomplete="new-password" placeholder="再次输入密码" />
            <button type="button" class="eye" @click="showConfirm = !showConfirm" :title="showConfirm ? '隐藏密码' : '显示密码'">{{ showConfirm ? '🙈' : '👁' }}</button>
          </div>
        </div>
        <div class="rules">
          <div :class="ruleCls(usernameOk)">✓ 用户名 3-20 位字母、数字或下划线</div>
          <div :class="ruleCls(lenOk)">✓ 密码 8-32 位</div>
          <div :class="ruleCls(caseOk)">✓ 包含大写和小写字母</div>
          <div :class="ruleCls(digitOk)">✓ 包含数字</div>
        </div>
        <div v-if="error" class="err">{{ error }}</div>
        <button class="submit" type="submit" :disabled="loading">{{ loading ? '注册中...' : '注册并登录' }}</button>
      </form>

      <div class="auth-foot">已有账号？<router-link to="/login">去登录</router-link></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api, notify } from '../api'
import { setSession } from '../auth'

const router = useRouter()
const form = ref({ username: '', password: '', confirm: '' })
const error = ref('')
const loading = ref(false)
const showPwd = ref(false)
const showConfirm = ref(false)

const usernameOk = computed(() => /^[A-Za-z0-9_]{3,20}$/.test(form.value.username))
const lenOk = computed(() => form.value.password.length >= 8 && form.value.password.length <= 32)
const caseOk = computed(() => /[a-z]/.test(form.value.password) && /[A-Z]/.test(form.value.password))
const digitOk = computed(() => /\d/.test(form.value.password))
const ruleCls = (ok) => ok ? 'rule ok' : 'rule'

async function submit() {
  error.value = ''
  if (!usernameOk.value) { error.value = '用户名需为 3-20 位字母、数字或下划线'; return }
  if (!lenOk.value || !caseOk.value || !digitOk.value) { error.value = '密码不满足规则（8-32 位，含大小写字母和数字）'; return }
  if (form.value.password !== form.value.confirm) { error.value = '两次输入的密码不一致'; return }
  loading.value = true
  try {
    const r = await api('/api/auth/register', { method: 'POST', body: { username: form.value.username, password: form.value.password } })
    setSession(r.token, r.user, r.idle_timeout)
    notify(`注册成功，欢迎 ${r.user.username}`)
    router.push('/dashboard')
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh; display: grid; place-items: center; overflow: hidden;
  background: #f7f8fb; background-image: none;
  padding: 20px; position: relative;
}
.auth-card {
  width: 100%; max-width: 420px; background: #fff;
  border: 1px solid #e6e9ef; border-radius: 10px; padding: 36px 34px;
  box-shadow: 0 1px 3px rgba(15, 20, 32, .06); position: relative; z-index: 2;
}
.back { position: absolute; top: 18px; right: 22px; font-size: 12.5px; color: #7d8598; text-decoration: none; transition: color .18s; }
.back:hover { color: #0f1420; }
.auth-logo {
  font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 9px;
  margin-bottom: 28px; letter-spacing: .01em; color: #0f1420;
}
.auth-logo .mark {
  width: 26px; height: 26px; border-radius: 6px;
  background: #4f5fe0; color: #fff; display: grid; place-items: center; font-size: 14px;
}
.auth-card h2 { font-size: 22px; font-weight: 700; margin-bottom: 6px; letter-spacing: -.02em; color: #0f1420; }
.auth-sub { color: #7d8598; font-size: 13.5px; margin-bottom: 24px; }
.field { margin-bottom: 15px; }
.field label { display: block; font-size: 12.5px; color: #57606f; margin-bottom: 7px; font-weight: 500; }
.input {
  width: 100%; padding: 10px 12px; border: 1px solid #dfe3ea; border-radius: 6px;
  font-size: 14px; background: #fff; color: #0f1420; transition: border-color .18s, box-shadow .18s;
}
.input:focus { outline: none; border-color: #4f5fe0; box-shadow: 0 0 0 3px rgba(79,95,224,.1); }
.input-wrap { position: relative; }
.input.has-eye { padding-right: 40px; }
.eye {
  position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
  width: 30px; height: 30px; border: none; background: transparent; border-radius: 6px;
  font-size: 15px; cursor: pointer; line-height: 1;
  display: grid; place-items: center;
  transition: background .15s, transform .15s;
}
.eye:hover { background: rgba(79, 95, 224, .08); transform: translateY(-50%) scale(1.08); }
.eye:active { transform: translateY(-50%) scale(.95); }
.rules {
  background: #fafbfc; border: 1px solid #eef0f4; border-radius: 6px;
  padding: 11px 13px; margin-bottom: 18px;
}
.rule { font-size: 12px; color: #98a0b0; line-height: 2; transition: color .18s; }
.rule.ok { color: #128a5d; }
.err {
  background: #fdf0f1; color: #d13b4f; padding: 10px 12px; border-radius: 6px;
  font-size: 12.5px; margin-bottom: 15px;
}
.submit {
  width: 100%; padding: 11px; border: none; border-radius: 6px;
  background: #4f5fe0; color: #fff; font-size: 14.5px; font-weight: 500;
  transition: background .18s;
}
.submit:hover:not(:disabled) { background: #3f4ecb; }
.submit:disabled { opacity: .6; }
.auth-foot { text-align: center; margin-top: 20px; font-size: 13px; color: #7d8598; }
.auth-foot a { color: #4f5fe0; font-weight: 500; }
</style>
