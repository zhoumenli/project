<template>
  <div class="auth-page">
    <div class="auth-card">
      <router-link to="/" class="back">← 返回首页</router-link>
      <div class="auth-logo"><span class="mark">⚡</span> 测试提效平台</div>
      <h2>登录账号</h2>
      <p class="auth-sub">登录后即可访问平台全部功能</p>

      <form @submit.prevent="submit">
        <div class="field">
          <label>用户名</label>
          <input class="input" v-model="form.username" autocomplete="username" />
        </div>
        <div class="field">
          <label>密码</label>
          <input class="input" type="password" v-model="form.password" autocomplete="current-password" />
        </div>
        <div v-if="error" class="err">{{ error }}</div>
        <button class="submit" type="submit" :disabled="loading">{{ loading ? '登录中...' : '登录' }}</button>
      </form>

      <div class="auth-foot">还没有账号？<router-link to="/register">立即注册</router-link></div>
      <div class="demo-tip">演示账号：<code>testuser</code> / <code>Test@1234</code></div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api, notify } from '../api'
import { setSession } from '../auth'

const router = useRouter()
const route = useRoute()
const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  if (!form.value.username || !form.value.password) { error.value = '请填写用户名和密码'; return }
  loading.value = true
  try {
    const r = await api('/api/auth/login', { method: 'POST', body: form.value })
    setSession(r.token, r.user)
    notify(`欢迎回来，${r.user.username}`)
    router.push(route.query.redirect || '/dashboard')
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
  width: 100%; max-width: 400px; background: #fff;
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
.auth-sub { color: #7d8598; font-size: 13.5px; margin-bottom: 26px; }
.field { margin-bottom: 17px; }
.field label { display: block; font-size: 12.5px; color: #57606f; margin-bottom: 7px; font-weight: 500; }
.input {
  width: 100%; padding: 10px 12px; border: 1px solid #dfe3ea; border-radius: 6px;
  font-size: 14px; background: #fff; color: #0f1420; transition: border-color .18s, box-shadow .18s;
}
.input:focus { outline: none; border-color: #4f5fe0; box-shadow: 0 0 0 3px rgba(79,95,224,.1); }
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
.demo-tip {
  margin-top: 16px; text-align: center; font-size: 12px; color: #98a0b0;
  border-top: 1px solid #eef0f4; padding-top: 14px;
}
.demo-tip code { color: #4f5fe0; font-weight: 500; }
</style>
