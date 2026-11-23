<template>
  <div class="landing">
    <!-- 导航 -->
    <header class="nav">
      <div class="nav-inner">
        <router-link to="/" class="brand">
          <svg class="brand-mark" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="3" width="7.5" height="7.5" rx="1.5" fill="currentColor" />
            <rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5" fill="currentColor" opacity=".4" />
            <rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5" fill="currentColor" opacity=".4" />
            <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5" fill="currentColor" />
          </svg>
          <span>测试提效平台</span>
        </router-link>
        <nav class="nav-links">
          <a href="#features">功能</a>
          <a href="#stack">技术栈</a>
          <router-link to="/login">登录</router-link>
          <router-link to="/register" class="nav-cta">创建账号</router-link>
        </nav>
      </div>
    </header>

    <!-- 主视觉 -->
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">测试提效平台 · v1.0</div>
        <h1>把测试工作<br /><span class="hl">从手工变成流水线</span></h1>
        <p class="lede">
          面向专职测试团队的 Web 与接口测试工作台。用例管理、需求生成、接口调试、
          UI 自动化与元素定位，在同一处完成。
        </p>
        <div class="hero-actions">
          <router-link to="/register" class="cta-primary">创建账号</router-link>
          <a href="#features" class="cta-secondary">查看功能</a>
        </div>
        <p class="hero-note">MySQL 本地存储 · 密码加盐加密 · 支持离线部署</p>
      </div>

      <!-- 界面示意 -->
      <div class="hero-visual">
        <div class="mock">
          <div class="mock-side">
            <div class="mock-brand"><i></i></div>
            <div class="mock-nav" :class="{ on: n === 1 }" v-for="n in 6" :key="n"><i></i></div>
          </div>
          <div class="mock-main">
            <div class="mock-top"><span></span><span class="short"></span></div>
            <div class="mock-stats">
              <div class="mock-stat" v-for="n in 4" :key="n">
                <i></i><b></b><s></s>
              </div>
            </div>
            <div class="mock-table">
              <div class="mock-row head"><span></span><span></span><span></span><span></span></div>
              <div class="mock-row" v-for="n in 5" :key="n">
                <span class="w40"></span><span class="w20"></span><span class="w15"></span><span class="w10"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 核心能力 -->
    <section class="features" id="features">
      <div class="sec-head">
        <h2>核心能力</h2>
        <p>覆盖测试日常的主要环节</p>
      </div>
      <div class="feature-list">
        <div class="feature" v-for="f in features" :key="f.no">
          <div class="feature-head">
            <span class="feature-no">{{ f.no }}</span>
            <h3>{{ f.title }}</h3>
          </div>
          <p>{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 技术与安全 -->
    <section class="stack" id="stack">
      <div class="stack-item">
        <h4>数据存储</h4>
        <p>MySQL 8.0 持久化，SQLAlchemy ORM 建模，业务数据与账号同库管理。</p>
      </div>
      <div class="stack-item">
        <h4>账号安全</h4>
        <p>密码使用 PBKDF2-SHA256 加盐哈希存储，全站接口 Token 鉴权。</p>
      </div>
      <div class="stack-item">
        <h4>离线可用</h4>
        <p>用例生成内置本地规则引擎，无需外部模型服务即可产出测试用例。</p>
      </div>
    </section>

    <!-- 行动号召 -->
    <section class="cta">
      <div>
        <h2>开始使用测试提效平台</h2>
        <p>注册一个账号，几分钟内完成第一个测试集。</p>
      </div>
      <router-link to="/register" class="cta-invert">创建账号</router-link>
    </section>

    <footer class="foot">
      <span>测试提效平台 · 专注测试提效，让质量更简单</span>
    </footer>
  </div>
</template>

<script setup>
const features = [
  { no: '01', title: '用例中心', desc: '项目、目录树、用例统一管理，接口 / UI / 手工用例分类维护，支持测试集编排与批量执行。' },
  { no: '02', title: '需求生成用例', desc: '上传需求文档，按测试设计维度批量产出用例，中英文输出，支持 Excel / Word / Markdown 等格式导出。' },
  { no: '03', title: '接口测试', desc: 'Postman 风格工作台，集合导入导出、变量提取与传递、断言校验，一次跑通整条接口链。' },
  { no: '04', title: 'Web UI 自动化', desc: '以步骤编排浏览器操作，运行后留存失败日志与截图标记，便于定位问题。' },
  { no: '05', title: '元素定位提取', desc: '真实浏览器打开目标页面，按角色、CSS、XPath 的优先级提取定位表达式并验证唯一性。' },
  { no: '06', title: '执行报告', desc: '保留每次执行的状态、耗时、断言明细与变量传递链路，历史结果可追溯。' },
]
</script>

<style scoped>
.landing {
  min-height: 100vh;
  background: #ffffff;
  background-image: none;
  color: #0f1420;
  font-size: 15px;
  line-height: 1.6;
}

/* ---------- 导航 ---------- */
.nav { border-bottom: 1px solid #e6e9ef; background: #fff; position: sticky; top: 0; z-index: 20; }
.nav-inner {
  max-width: 1180px; margin: 0 auto; height: 64px;
  display: flex; align-items: center; justify-content: space-between; padding: 0 24px;
}
.brand { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #0f1420; }
.brand-mark { width: 22px; height: 22px; color: #4f5fe0; }
.nav-links { display: flex; align-items: center; gap: 26px; font-size: 14px; }
.nav-links a { color: #57606f; transition: color .18s; }
.nav-links a:hover { color: #0f1420; }
.nav-cta {
  padding: 7px 15px; border-radius: 6px; background: #0f1420; color: #fff !important;
  font-weight: 500; transition: background .18s;
}
.nav-cta:hover { background: #2a3242 !important; }

/* ---------- 主视觉 ---------- */
.hero {
  max-width: 1180px; margin: 0 auto; padding: 72px 24px 64px;
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 64px; align-items: center;
}
.eyebrow { font-size: 12.5px; font-weight: 500; color: #7d8598; margin-bottom: 18px; letter-spacing: .02em; }
.hero h1 {
  font-size: 46px; font-weight: 700; line-height: 1.18; letter-spacing: -.03em;
  color: #0f1420; margin-bottom: 22px;
}
.hl {
  text-decoration: underline; text-decoration-color: #4f5fe0;
  text-decoration-thickness: 3px; text-underline-offset: 8px;
}
.lede { font-size: 16px; color: #57606f; max-width: 500px; margin-bottom: 30px; line-height: 1.75; }
.hero-actions { display: flex; gap: 12px; margin-bottom: 20px; }
.cta-primary {
  padding: 11px 22px; border-radius: 6px; background: #4f5fe0; color: #fff;
  font-size: 14.5px; font-weight: 500; transition: background .18s;
}
.cta-primary:hover { background: #3f4ecb; }
.cta-secondary {
  padding: 11px 22px; border-radius: 6px; border: 1px solid #d8dce6;
  color: #0f1420; font-size: 14.5px; font-weight: 500; transition: border-color .18s, background .18s;
}
.cta-secondary:hover { border-color: #b9bfcf; background: #fafbfc; }
.hero-note { font-size: 12.5px; color: #98a0b0; }

/* 界面示意 */
.hero-visual { min-width: 0; }
.mock {
  display: flex; border: 1px solid #e6e9ef; border-radius: 8px; overflow: hidden;
  background: #fff; box-shadow: 0 1px 3px rgba(15, 20, 32, .06);
}
.mock-side { width: 108px; flex-shrink: 0; background: #161b28; padding: 12px 10px; }
.mock-brand { padding: 6px 4px 14px; }
.mock-brand i { display: block; width: 18px; height: 18px; border-radius: 4px; background: #4f5fe0; opacity: .85; }
.mock-nav { padding: 7px 4px; display: flex; align-items: center; gap: 7px; border-radius: 4px; }
.mock-nav i { display: block; width: 11px; height: 11px; border-radius: 3px; background: #39415a; }
.mock-nav.on { background: rgba(79, 95, 224, .2); }
.mock-nav.on i { background: #6b78ea; }
.mock-main { flex: 1; padding: 14px; min-width: 0; }
.mock-top { display: flex; gap: 8px; margin-bottom: 14px; }
.mock-top span { display: block; height: 16px; width: 90px; border-radius: 3px; background: #eef0f4; }
.mock-top span.short { width: 46px; }
.mock-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 14px; }
.mock-stat { border: 1px solid #eef0f4; border-radius: 5px; padding: 8px; }
.mock-stat i { display: block; width: 14px; height: 14px; border-radius: 3px; background: #e8ebf2; margin-bottom: 8px; }
.mock-stat b { display: block; height: 7px; width: 60%; border-radius: 2px; background: #dfe3ec; margin-bottom: 5px; }
.mock-stat s { display: block; height: 5px; width: 80%; border-radius: 2px; background: #eef0f4; text-decoration: none; }
.mock-table { border: 1px solid #eef0f4; border-radius: 5px; overflow: hidden; }
.mock-row { display: flex; gap: 10px; padding: 8px 10px; border-bottom: 1px solid #f2f4f7; }
.mock-row:last-child { border-bottom: none; }
.mock-row span { display: block; height: 6px; border-radius: 2px; background: #e8ebf2; }
.mock-row.head { background: #fafbfc; }
.mock-row.head span { background: #dfe3ec; }
.w40 { width: 40%; } .w20 { width: 20%; } .w15 { width: 15%; } .w10 { width: 10%; }

/* ---------- 核心能力 ---------- */
.features { max-width: 1180px; margin: 0 auto; padding: 32px 24px 72px; }
.sec-head { margin-bottom: 32px; }
.sec-head h2 { font-size: 26px; font-weight: 700; letter-spacing: -.02em; margin-bottom: 6px; }
.sec-head p { font-size: 14.5px; color: #7d8598; }
.feature-list {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 56px; border-top: 1px solid #e6e9ef;
}
.feature { padding: 26px 0 28px; border-bottom: 1px solid #e6e9ef; }
.feature-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 8px; }
.feature-no {
  font-size: 12px; font-weight: 600; color: #4f5fe0;
  font-variant-numeric: tabular-nums; letter-spacing: .06em;
}
.feature h3 { font-size: 16.5px; font-weight: 600; color: #0f1420; }
.feature p { font-size: 14px; color: #6b7385; line-height: 1.75; padding-left: 34px; }

/* ---------- 技术与安全 ---------- */
.stack {
  max-width: 1180px; margin: 0 auto; padding: 0 24px 72px;
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 40px;
}
.stack-item h4 { font-size: 14.5px; font-weight: 600; margin-bottom: 8px; color: #0f1420; }
.stack-item p { font-size: 13.5px; color: #7d8598; line-height: 1.75; }

/* ---------- 行动号召 ---------- */
.cta {
  max-width: 1180px; margin: 0 auto 72px; padding: 36px 44px;
  background: #f7f8fb; border: 1px solid #e6e9ef; border-radius: 8px;
  display: flex; align-items: center; justify-content: space-between; gap: 32px; flex-wrap: wrap;
}
.cta h2 { font-size: 22px; font-weight: 700; color: #0f1420; letter-spacing: -.02em; margin-bottom: 6px; }
.cta p { font-size: 14.5px; color: #7d8598; }
.cta-invert {
  padding: 11px 24px; border-radius: 6px; background: #0f1420; color: #fff;
  font-size: 14.5px; font-weight: 500; white-space: nowrap; transition: background .18s;
}
.cta-invert:hover { background: #2a3242; }

/* ---------- 页脚 ---------- */
.foot { border-top: 1px solid #e6e9ef; padding: 26px 24px; text-align: center; font-size: 13px; color: #98a0b0; }

@media (max-width: 980px) {
  .hero { grid-template-columns: 1fr; gap: 40px; padding-top: 48px; }
  .hero h1 { font-size: 36px; }
  .feature-list { grid-template-columns: 1fr; column-gap: 0; }
  .stack { grid-template-columns: 1fr; gap: 24px; }
}
</style>
