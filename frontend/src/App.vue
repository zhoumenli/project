<template>
  <!-- 公开页面（大纲/登录/注册）：独立外壳 -->
  <router-view v-if="$route.meta.public" />
  <!-- 登录后的平台外壳 -->
  <div v-else class="app">
    <aside class="sidebar">
      <div class="logo"><span class="mark">⚡</span> <span class="logo-text">测试提效平台<small>TEST EFFICIENCY</small></span></div>
      <nav class="nav">
        <div class="nav-group-label">工作空间</div>
        <router-link v-for="n in navItems.slice(0, 4)" :key="n.path" :to="n.path" class="nav-item" active-class="active">
          <span class="icon">{{ n.icon }}</span>{{ n.title }}
        </router-link>
        <div class="nav-group-label">效率工具</div>
        <router-link v-for="n in navItems.slice(4)" :key="n.path" :to="n.path" class="nav-item" active-class="active">
          <span class="icon">{{ n.icon }}</span>{{ n.title }}
        </router-link>
      </nav>
      <div class="sidebar-foot"><span class="foot-dot"></span> Test Efficiency Platform <b>v1.0</b></div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div class="page-title">
          <div class="title-icon">✦</div>
          <div>
            <h1>{{ $route.meta.title }}</h1>
            <div class="title-sub">专注测试提效，让质量更简单</div>
          </div>
        </div>
        <div class="topbar-right">
          <div class="greeting">你好，<b>{{ user?.username }}</b> 👋</div>
          <select class="project-select" v-model="projectId" @change="onProjectChange">
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
          <div class="user-menu">
            <button class="user-btn" @click="menuOpen = !menuOpen">
              <span class="avatar">{{ (user?.username || 'U')[0].toUpperCase() }}</span>
              <span class="uname">{{ user?.username }}</span>
              <span class="caret">▾</span>
            </button>
            <div v-if="menuOpen" class="user-dropdown">
              <div class="dropdown-head">当前用户<br><b>{{ user?.username }}</b></div>
              <button @click="logout">退出登录</button>
            </div>
          </div>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
    <div v-if="toast" class="toast">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { projects, currentProject, toast, loadProjects, api, notify } from './api'
import { user, clearSession, isLoggedIn } from './auth'

const route = useRoute()
const router = useRouter()
const projectId = ref(null)
const menuOpen = ref(false)
const navItems = [
  { path: '/dashboard', icon: '📊', title: '工作台' },
  { path: '/cases', icon: '📋', title: '用例中心' },
  { path: '/api-test', icon: '🔌', title: '接口测试' },
  { path: '/ui-test', icon: '🌐', title: 'Web UI 自动化' },
  { path: '/locator', icon: '🎯', title: '元素定位' },
  { path: '/runs', icon: '📈', title: '执行报告' },
  { path: '/environments', icon: '⚙️', title: '环境管理' },
]

onMounted(async () => {
  if (!isLoggedIn.value) return
  try { await loadProjects() } catch (e) {}
  projectId.value = currentProject.value?.id
})
watch(() => currentProject.value, (p) => { projectId.value = p?.id })
function onProjectChange() {
  currentProject.value = projects.value.find(p => p.id === projectId.value)
}
async function logout() {
  try { await api('/api/auth/logout', { method: 'POST' }) } catch (e) {}
  clearSession()
  menuOpen.value = false
  notify('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.logo-text { display: flex; flex-direction: column; line-height: 1.15; }
.logo-text small { font-size: 8px; font-weight: 600; letter-spacing: 1.5px; color: #8f98c4; margin-top: 3px; }
.nav-group-label {
  font-size: 10px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase;
  color: #6b7396; padding: 12px 14px 6px;
}
.foot-dot {
  display: inline-block; width: 7px; height: 7px; border-radius: 50%;
  background: #34d399; margin-right: 7px; box-shadow: 0 0 8px #34d399;
}
.sidebar-foot b { color: #9aa2c6; font-weight: 600; }

.page-title { display: flex; align-items: center; gap: 13px; }
.title-icon {
  width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center;
  font-size: 18px; color: #fff;
  background: linear-gradient(135deg, #5b6bf5, #8b5cf6);
  box-shadow: 0 4px 14px rgba(91, 107, 245, .35);
}
.page-title h1 { font-size: 17px; font-weight: 800; line-height: 1.2; }
.title-sub { font-size: 11.5px; color: var(--muted); margin-top: 2px; }

.topbar-right { display: flex; align-items: center; gap: 18px; }
.greeting { font-size: 13px; color: var(--muted); }
.greeting b { color: var(--primary); font-weight: 700; }
.user-menu { position: relative; }
.user-btn {
  display: flex; align-items: center; gap: 9px; border: 1.5px solid var(--border);
  background: #fff; border-radius: 24px; padding: 4px 12px 4px 4px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all .22s cubic-bezier(.4,0,.2,1);
}
.user-btn:hover { border-color: var(--primary); box-shadow: 0 4px 14px rgba(91,107,245,.16); transform: translateY(-1px); }
.avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, #7c8bff, #a06bff); color: #fff;
  display: grid; place-items: center; font-weight: 800; font-size: 13px;
  box-shadow: 0 3px 10px rgba(124, 139, 255, .4);
}
.uname { max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.caret { color: var(--muted); font-size: 10px; transition: transform .2s; }
.user-btn:hover .caret { transform: translateY(2px); }
.user-dropdown {
  position: absolute; right: 0; top: 46px; width: 190px; background: #fff;
  border: 1px solid var(--border); border-radius: 13px;
  box-shadow: 0 12px 40px rgba(20, 24, 50, .18); z-index: 50; overflow: hidden;
  animation: popIn .2s cubic-bezier(.34, 1.56, .64, 1);
}
.dropdown-head { padding: 13px 15px; font-size: 11px; color: var(--muted); border-bottom: 1px solid var(--border); line-height: 1.7; }
.dropdown-head b { color: var(--text); font-size: 14px; }
.user-dropdown button {
  display: block; width: 100%; text-align: left; border: none; background: #fff;
  padding: 12px 15px; font-size: 13px; font-weight: 600; color: var(--danger);
  transition: background .18s, padding-left .18s;
}
.user-dropdown button:hover { background: #fdeaee; padding-left: 19px; }

@media (max-width: 900px) { .greeting { display: none; } }
</style>
