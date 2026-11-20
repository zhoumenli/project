import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from './auth'

const routes = [
  { path: '/', component: () => import('./views/Landing.vue'), meta: { title: '平台大纲', public: true } },
  { path: '/login', component: () => import('./views/Login.vue'), meta: { title: '登录', public: true } },
  { path: '/register', component: () => import('./views/Register.vue'), meta: { title: '注册', public: true } },
  { path: '/dashboard', component: () => import('./views/Dashboard.vue'), meta: { title: '工作台' } },
  { path: '/cases', component: () => import('./views/CaseCenter.vue'), meta: { title: '用例中心' } },
  { path: '/gen-cases', component: () => import('./views/RequirementGenerate.vue'), meta: { title: '需求生成用例' } },
  { path: '/api-test', component: () => import('./views/ApiTest.vue'), meta: { title: '接口测试' } },
  { path: '/ui-test', component: () => import('./views/UiTest.vue'), meta: { title: 'Web UI 自动化' } },
  { path: '/locator', component: () => import('./views/LocatorExtractor.vue'), meta: { title: '元素定位' } },
  { path: '/runs', component: () => import('./views/Runs.vue'), meta: { title: '执行报告' } },
  { path: '/environments', component: () => import('./views/Environments.vue'), meta: { title: '环境管理' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (!to.meta.public && !isLoggedIn.value) {
    next({ path: '/login', query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : {} })
  } else if ((to.path === '/login' || to.path === '/register') && isLoggedIn.value) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
