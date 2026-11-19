# 测试提效平台 · 可运行原型

面向**专职测试团队**、聚焦 **Web / 接口测试** 的提效平台 MVP。

| 模块 | 说明 |
|---|---|
| 🔐 登录注册 | MySQL 存储用户，密码 PBKDF2 加盐加密，全 API Bearer Token 鉴权 |
| 📋 用例中心 | 项目 → 目录树 → 用例，统一管理接口 / UI / 手工用例，支持测试集编排 |
| ✨ **需求生成用例** | 上传需求文档（多格式），自动全方位生成测试用例，含历史记录与一键导入 |
| 🔌 接口测试引擎 | 单接口调试、断言校验、变量提取、接口关联、环境切换、批量执行 |
| 🌐 Web UI 自动化 | 步骤化用例编排、模拟执行引擎、失败日志与截图标记 |
| 🎯 元素定位提取 | 输入网址 + 元素关键词，真实浏览器打开页面，按 角色 → CSS → XPath 优先级提取并验证唯一性 |

附带：工作台看板、执行报告中心、环境管理。

---

## 技术栈

- 后端：Python FastAPI + SQLAlchemy + MySQL 8.0（pymysql 驱动；可回退 SQLite）
- 认证：PBKDF2-HMAC-SHA256 密码哈希 + Bearer Token（持久化在 MySQL）
- 前端：Vue3 + Vite + vue-router（含登录守卫）
- 视觉：自建设计系统（靛蓝→紫渐变主色、毛玻璃卡片、多层阴影、微动效），全局样式集中在 `frontend/src/style.css`；公开页（大纲 / 登录 / 注册）刻意走克制路线——纯色、下划线强调、细线分隔、小圆角，不使用 emoji 与装饰光斑
- 执行引擎：httpx（接口）、可插拔步骤引擎（UI，预留 Playwright 接入点）
- 演示依赖：一个轻量 Mock Server（模拟被测系统接口）

---

## 快速开始（克隆后 3 步跑起来）

```bash
# 1. 克隆
git clone https://github.com/<你的用户名>/test-efficiency-platform.git
cd test-efficiency-platform

# 2. 建库（命令行一键，或用 Navicat 导入 db/test_efficiency_platform.sql）
mysql -uroot -proot < db/test_efficiency_platform.sql

# 3. 启动（开两个终端）
cd backend
python mock_server.py                                       # 终端 A：被测系统，端口 9001
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000   # 终端 B：平台，端口 8000
```

浏览器打开 **http://127.0.0.1:8000** ，用 `testuser` / `Test@1234` 登录。

> 前端 `frontend/dist` 已随仓库提交，**无需 `npm install` / `npm run build`** 即可直接运行。
> 需要改前端源码时再执行：`cd frontend && npm install && npm run build`

---

## 启动方式

### 1. 环境要求（重要）
- Python 3.10+，且必须包含 fastapi / uvicorn / sqlalchemy / httpx / playwright / **pymysql**
- MySQL 8.0（本机 127.0.0.1:3306，默认账号 root / root），数据库 `test_efficiency_platform` 已创建；可用 Navicat 连接查看
- 本机需安装 Chrome 或 Edge（provider 已优先使用系统浏览器，无需 `playwright install`）
- 本机已验证可用的解释器是 `C:\python\python.exe`；直接用 `python` 可能指向没有依赖的版本，启动前可先执行 `python -c "import fastapi, playwright"` 确认
- Node.js 18+（前端已构建好，无需重新构建也能运行）

### 2. 数据库配置（MySQL）
平台默认使用 MySQL 存储所有业务数据 + 用户账号，连接参数通过环境变量配置（默认值如下）：

| 环境变量 | 默认值 |
|---|---|
| `DB_BACKEND` | `mysql`（设为 `sqlite` 可回退到本地 SQLite） |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` |
| `DB_NAME` | `test_efficiency_platform` |
| `DB_USER` / `DB_PASSWORD` | `root` / `root` |

表结构在首次启动时由 SQLAlchemy 自动创建（`users`、`auth_tokens` 及所有业务表）。如需改密码，用环境变量覆盖即可，例如 `set DB_PASSWORD=你的密码`。

**手动建库（Navicat 导入）**：仓库内已提供一份现成的初始化脚本 [`db/test_efficiency_platform.sql`](db/test_efficiency_platform.sql)，包含建库语句、10 张表的完整 DDL、演示账号与示例项目种子数据。

- Navicat：新建 MySQL 连接（`127.0.0.1` / `3306` / `root` / `root`）→ 右键连接 → **运行 SQL 文件** → 选择该文件 → 开始
- 命令行：`mysql -uroot -proot < db/test_efficiency_platform.sql`
- 脚本使用 `DROP TABLE IF EXISTS`，可重复执行；导入后用 `testuser` / `Test@1234` 登录
- `auth_tokens` 只建表不写入数据（登录令牌运行时签发，不固化在脚本里）

### 3. 启动 Mock Server（被测系统，端口 9001）
```bash
cd backend
python mock_server.py
```

### 4. 启动平台后端（端口 8000）
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

首次启动会自动建表并灌入演示数据（电商系统项目、7 条用例、1 个测试集、1 个环境）。

### 5. 打开平台
浏览器访问：**http://127.0.0.1:8000**

前端 `frontend/dist` 已构建并由后端直接托管，无需单独启动前端服务。

---

## 🔐 登录与注册

打开平台首先看到的是**平台大纲页**（介绍 6 大模块能力），右上角有「登录 / 免费注册」入口。未登录时访问任何业务页面都会被引导到登录页；登录成功后回到平台才能看到具体功能。

- **注册**：用户名 3-20 位字母/数字/下划线；密码 8-32 位，需同时包含大写字母、小写字母和数字；注册页有实时规则提示与二次确认。注册成功即自动登录
- **登录**：校验用户名密码，成功后签发 Bearer Token（有效期 30 天）存入浏览器 localStorage
- **密码安全**：使用 PBKDF2-HMAC-SHA256 + 每人随机盐（21 万次迭代）哈希存储，**数据库无明文密码**；校验用恒定时间比较
- **全 API 鉴权**：除 `/api/auth/*` 外，所有业务接口都必须带 `Authorization: Bearer <token>`，否则返回 401；前端遇到 401 自动清除会话并跳转登录页
- **登出**：右上角用户头像菜单 → 退出登录，服务端销毁 Token

演示账号：`testuser` / `Test@1234`（已预置在 MySQL 中）。

鉴权实现：`backend/app/auth.py`（哈希/校验/Token）、`backend/app/main.py`（接口与全局中间件）、`frontend/src/auth.js`（会话状态）、`frontend/src/router.js`（路由守卫）。

---

## ✨ 需求生成用例（新功能）

在「用例中心」页面顶部切换到「需求生成用例」Tab：

1. **上传需求文档**：支持 PDF / Word / Excel / PPT / TXT / Markdown / CSV / JSON / HTML / 图片等，点击或拖拽上传，最大 20MB
2. **选择生成引擎**：
   - `local`（默认）：本地智能规则引擎，离线免费开箱即用，按需求点 × 测试设计维度批量生成
   - `llm`：大模型引擎（设置环境变量 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`，兼容 OpenAI 格式；未配置自动回退本地）
3. **勾选生成维度**：功能正确性、边界值、异常输入、数据校验、权限与安全、状态流转、性能与并发、UI与兼容性、易用性与提示
4. **输出语言**：中文 / English（影响用例正文——标题、前置条件、步骤、预期结果、标签；本地引擎内置中英双语文案，大模型引擎通过提示词指定语言）
5. **输出模板（自定义格式）**：用占位符自定义每条用例的输出格式，例如
   - 中文：`【{编号}】{标题}\n维度：{维度} ｜ 优先级：{优先级}\n步骤：\n{步骤}\n预期结果：{预期结果}`
   - 英文：`[{no}] {title}\nDimension: {dimension} | Priority: {priority}\nSteps:\n{steps}\nExpected: {expected}`
   - 可用占位符：`{编号}/{no}`、`{标题}/{title}`、`{维度}/{dimension}`、`{优先级}/{priority}`、`{类型}/{case_type}`、`{前置条件}/{precondition}`、`{步骤}/{steps}`、`{预期结果}/{expected}`、`{标签}/{tags}`、`{风险}/{risk}`，中英文别名通用；留空则按语言使用默认模板
6. **查看结果**：每条用例默认按模板渲染展示，可一键复制；展开「结构化字段」查看导入所需字段；支持按维度/优先级筛选
7. **历史记录**：所有生成记录持久化，可查看、重新导入、删除
8. **一键导入**：将生成的用例批量导入到指定目录，自动打上「AI生成」标签（导入使用结构化字段，不受模板影响）
9. **多格式导出**：生成结果（或历史记录）可按需选择文件格式导出——Excel(.xlsx) / Word(.docx) / Markdown(.md) / CSV(.csv) / JSON(.json) / TXT(.txt) / HTML(.html)。导出内容按当前语言与模板渲染，文件名自动沿用文档名

导出接口：`GET /api/generations/{id}/export?format=xlsx`，实现在 `backend/app/exporter.py`。

每条用例覆盖 9 大测试设计维度，例如一份登录需求可生成 60+ 条用例。

### 文档解析依赖
- PDF：PyMuPDF (`fitz`)
- Word：python-docx ｜ Excel：openpyxl ｜ PPT：python-pptx
- HTML：beautifulsoup4 ｜ 图片 OCR：pytesseract（可选，需安装 tesseract）
- 纯文本类（TXT/MD/CSV/JSON/XML/SQL...）：内置多编码自动识别

### LLM 模式配置（可选）
```bash
set LLM_API_KEY=your-key
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
set GEN_BACKEND=llm
```

---

## 🎯 元素定位提取（新功能）

左侧导航「元素定位」进入。输入网址 + 页面上的元素文字/占位符/名称，平台用真实浏览器打开页面并提取定位：

1. **角色定位优先**：`get_by_role(...)` / `get_by_label(...)` / `get_by_placeholder(...)` / `get_by_text(...)`（基于 ARIA 语义，最稳定）
2. **CSS 兜底**：`#id` → `[data-testid]` → 属性 → class 组合 → 结构路径
3. **XPath 兜底**：`//*[@id=...]` → 文本匹配 → 属性匹配 → 相对/绝对路径

每个候选定位都会在真实页面上验证唯一性，命中的元素按优先级给出 **⭐ 推荐使用** 的定位表达式，并提供 Python / JavaScript 两种写法、备选定位、元素截图和红框标注的页面截图。

- 支持「包含 / 精确」两种匹配模式，可调节页面加载等待时间
- 高级选项可填前置操作步骤（JSON），先登录/先点击再定位，例如：
  ```json
  [{"action":"fill","target":"#username","value":"admin"},{"action":"click","target":"#login-btn"}]
  ```
  支持 `fill` / `click` / `check` / `wait` / `goto`
- 命中多个元素时可切换查看；结果可一键复制，历史记录保存在浏览器本地

**页面结构：先填 URL，再选定位方式**

① **URL 区**：填 `url`；若目标站用 HTTP Basic Auth，可再填 `username` / `password`（都可选）——填了才拼成 `http://username:password@host` 访问，不填就直接访问 url。下方「实际访问」实时预览（密码打码）。

② **获取元素定位方式（二选一）**：
- **直接定位**：输入元素关键词，平台自动打开拼好的 URL，按 角色 → CSS → XPath 提取并验证唯一性。可配匹配模式、等待时间、高级前置操作步骤。
- **交互浏览器（适合需登录/验证码的页面）**：点「打开浏览器」，平台弹出一个**你能亲自操作的真实浏览器窗口**；在里面完成登录、跳转、滚动到目标页后，回来输入元素关键词点「在当前页面定位」，平台对**当前页面**提取定位。可反复换页面、换关键词多次定位，浏览器一直保持打开，用完点「关闭浏览器」。请在同一个标签页里操作（新开标签页不会被定位）。

如需在直接定位里先登录再提取，用「高级：前置操作步骤」自动完成登录流程。

**场景 A：网站是表单登录（最常见，登录页填账号密码点按钮）**
1. 定位方式选「直接定位」，URL 区填登录页地址（如 `http://host/login`）
2. 展开「高级：前置操作步骤」，填入登录动作（target 为 CSS 选择器）：
```json
[
  {"action":"fill","target":"#username","value":"admin"},
  {"action":"fill","target":"#password","value":"123456"},
  {"action":"click","target":"#login-btn"},
  {"action":"wait","value":"1500"}
]
```
3. 元素关键词填**登录后才可见**的目标元素（如「欢迎回来」），点提取
4. 平台会在同一浏览器会话里按步骤登录、跳转到登录后页面，再定位元素（登录 Cookie 全程保留在同一个 context 中）

**场景 B：知道目标页地址、且无需真实登录态也能访问**
直接用前置步骤 `goto` 跳到目标页再定位：
```json
[{"action":"goto","target":"http://host/demo/dashboard"}]
```

**说明**：
- 前置步骤支持 `fill` / `click` / `check` / `wait` / `goto`，按顺序执行，`wait` 的 value 是毫秒
- 如果登录有**图形验证码 / 短信验证码 / 扫码**，自动步骤过不去，这种情况只能用登录态复用（本平台当前已移除该能力）或手动在浏览器完成验证后再抓取
- 演示服务 `mock_server.py` 提供 `/demo/login` 登录页和 `/demo/dashboard` 控制台（登录后页面），可用 `admin`/`123456` 配合上述步骤 A 验证完整流程

后端接口：`POST /api/locator/extract`（一次性提取），引擎实现在 `backend/app/locator_extractor.py`。

交互浏览器会话接口（实现在 `backend/app/interactive_session.py`）：
- `POST /api/locator/interactive/start` 打开可见浏览器
- `GET /api/locator/interactive/{sid}/status` 查询会话状态
- `POST /api/locator/interactive/{sid}/locate` 对当前页面定位
- `POST /api/locator/interactive/{sid}/close` 关闭浏览器

说明：交互浏览器默认有头可见；服务端无桌面环境时可设环境变量 `INTERACTIVE_HEADLESS=1` 以无头运行。会话 30 分钟无操作会自动过期。

---

## 快速体验路径

1. **工作台**：查看项目 / 用例 / 执行统计与趋势
2. **接口测试**：进入 Postman 风格工作台 → 点默认请求 `Login` 的 **Send** → 看响应与提取的 token → 点集合的 **▶ Run Collection** 体验整链；也可「＋请求」自行调试（见下方「接口测试（Postman 风格工作台）」章节）
3. **用例中心**：浏览目录树 → 新建 / 编辑用例（接口用例可配断言与提取规则）
4. **执行报告**：新建执行 → 选「测试集」→ 开始 → 查看每条用例的请求 / 响应 / 断言详情；接口用例提取的变量会显示在「提取并传递的变量」中
5. **环境管理**：新增环境，配置 Base URL 与变量（用例中可用 `{{变量名}}` 引用）
6. **Web UI 自动化**：选择 UI 用例 → 编辑步骤（goto / click / fill / assert_visible 等）→ 运行

---

## 🔌 接口测试（Postman 风格工作台）

左侧导航「接口测试」进入，是一个类似 Postman 的 API 调试工作台，布局为**左侧集合树 + 上方请求栏 + 中部请求配置 + 下方响应区**。

### 界面结构
- **左侧栏**：`Collections`（集合树）/ `History`（最近 50 条请求）两个标签；底部是环境选择器与变量池快速查看（👁 展开，点「编辑」管理本地变量）
- **请求栏**：Method 下拉（GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS）+ URL 输入（支持 `{{变量}}`）+ **Send** / **Save** / **Run Collection**
- **请求配置标签页**：
  - `Params`：查询参数表格，与 URL 中的 query 双向同步；支持 Bulk Edit（每行 `Key: Value`）
  - `Authorization`：No Auth / Basic Auth / Bearer Token / API Key（可放 Header 或 Query Params）
  - `Headers`：请求头表格，支持 Bulk Edit
  - `Body`：none / raw（JSON/Text/XML/HTML/JavaScript，带 Beautify）/ form-data / x-www-form-urlencoded
  - `Tests`：断言规则（状态码 / JSON 字段 / Header / Body，支持 eq/ne/contains/gt/gte/lt/lte/exists/regex）+ 变量提取规则
- **响应区**：`Body`（Pretty 自动格式化 / Raw 原文 / Preview 用 iframe 渲染 HTML，带 Copy）/ `Headers` / `Cookies` / `Test Results`；顶部显示状态码、耗时、响应大小

### 集合与请求管理
- 点「＋集合」新建集合，「＋请求」在当前集合新建请求；每个请求独立保存 method / URL / Params / Auth / Headers / Body / 断言 / 提取规则
- 集合/请求都支持重命名（✎）和删除（×）；集合下的「＋ 新建请求」可直接添加
- 点请求名加载到工作台编辑，改动即时更新；点 **Save** 明确保存到当前集合
- 所有集合、请求、历史、变量池都存浏览器 localStorage，跨刷新保留

### ⇩⇧ 集合导入 / 导出（Postman 格式）
左侧栏顶部的「⇩ 导入 Postman 集合」和「⇧ 导出」支持与 Postman 互通，格式为标准 **Postman Collection v2.1**：

- **导出**：选「当前集合」下载单个 `.postman_collection.json`，或选「全部集合」分别下载多个文件；弹窗内可预览生成的 JSON。导出内容包含 `info.name` / `info.schema` / `item[]`，每项的 `request.method` / `header` / `url`（含 protocol/host/port/path/query）/ `body`（raw / formdata / urlencoded）/ `auth`（bearer / basic / apikey）均为 Postman 标准字段
- **平台特有字段**（断言规则、变量提取、表单模式细节、Params 描述等）保存在每项的标准 `x-tef` 私有扩展里，Postman 会忽略它，导回本平台时自动还原，round-trip 不丢数据
- **导入**：选择 Postman 集合 JSON 文件，自动转换为平台集合 + 请求——支持字符串 / 对象两种 URL、raw / formdata / urlencoded 三种 Body、四种 Auth、禁用的 header / 表单字段，以及嵌套 Folder（文件夹内的请求会被平铺导入）；导入后追加到集合树并选中第一个请求

### 单接口调试与接口关联
1. 选一个请求（或「＋请求」新建），配好 Method / URL / Body / Headers
2. 在 `Tests` 标签的「变量提取」里配置，如 `token` ← JSON 字段 `data.token`
3. 点 **Send**，响应区显示结果；提取的值自动写入变量池
4. 在后续请求的 URL / Headers / Body 中用 `{{token}}` 引用，例如 `Authorization: Bearer {{token}}`
5. 顶部环境选择器选「本地 Mock」时，环境自带变量也会合并进渲染上下文（本地变量优先）

演示：默认集合 `Demo API` 预置两步——`Login`（POST /api/login，提取 `data.token`）和 `Get User Info`（GET /api/user/info，带 `Bearer {{token}}`）。

### ⛓️ 运行整个集合（接口链）
点集合右侧的 **▶**（或请求栏的 **Run Collection**），集合内所有请求按列表顺序一次跑完：前一步提取的变量自动传给后续请求。结果区展示每步状态码、实际请求（变量已替换）、响应体、提取变量，可展开查看。这就是原来的「接口链」能力，现在以集合为单位组织。

后端接口：`POST /api/debug/run`（单请求）、`POST /api/debug/run-chain`（集合顺序执行）；实现见 `backend/app/engine.py` 的 `execute_api`（支持 raw / form-data / x-www-form-urlencoded 三种 Body 模式）。

### 批量关联（用例中心多用例顺序执行）

---

## 演示数据说明

- 环境「本地 Mock」Base URL = `http://127.0.0.1:9001`，变量 `token`、`page`
- 测试集「接口冒烟测试集」包含 5 条接口用例
- Mock Server 提供：`POST /api/login`、`GET /api/user/info`、`GET /api/products`、`POST /api/echo`（回显请求 method / headers / query / body，用于验证各种 Body 模式和变量渲染）
- 用例中的 URL 写相对路径（如 `/api/login`），执行时自动拼接环境 Base URL

---

## 目录结构

```
test-efficiency-platform/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 路由与演示数据
│   │   ├── models.py        # ORM 数据模型
│   │   ├── schemas.py       # Pydantic 校验模型
│   │   ├── engine.py        # 执行引擎（变量/断言/HTTP/UI步骤）
│   │   ├── doc_parser.py    # 多格式文档解析（PDF/Word/Excel/PPT/TXT/图片）
│   │   ├── case_generator.py# 用例智能生成引擎（本地规则 + LLM 双模式）
│   │   ├── database.py      # 数据库配置
│   │   ├── uploads/         # 上传的需求文档存储
│   │   └── platform.db      # SQLite（DB_BACKEND=sqlite 时的回退库）
│   ├── mock_server.py       # 演示用被测系统
│   └── demo_requirement.md  # 演示用需求文档
├── db/
│   └── test_efficiency_platform.sql  # Navicat 可导入的建库建表脚本（含演示数据）
├── frontend/
│   ├── dist/                # 已构建的前端产物
│   └── src/
│       ├── views/           # 各模块页面（RequirementGenerate.vue = 需求生成用例）
│       ├── App.vue / router.js / api.js / style.css
│       └── main.js
└── README.md
```

---

## 生产化接入建议

当前 UI 自动化使用**模拟执行引擎**，生产环境建议接入真实 Playwright：

1. 后端新增 `ui_runner.py`，用 `playwright.sync_api` 执行 `steps` 步骤
2. 将 UI 用例改为异步任务（Celery / 线程池）执行，避免阻塞 HTTP 请求
3. 截图上传 MinIO / 本地静态目录，报告中展示真实截图
4. 断言引擎扩展支持 JSONPath（如 `$.data.token`）
5. 接入 CI：流水线调用 `/api/runs` 触发测试，回调通知结果

接口自动化可直接扩展：数据驱动（CSV/Excel 参数化）、前后置脚本、Mock 服务管理。

---

## 已知边界（原型阶段）

- UI 用例执行为模拟（不启动真实浏览器）
- 无用户权限体系（单租户演示）
- 执行为同步阻塞（生产应改为异步任务队列）
- 目录重命名暂未实现（可删除重建）

---

## 自动同步到 GitHub（改动即推送）

本项目内置 `scripts/auto_sync.py`，监听本地代码改动并自动 `commit` + `push` 到 GitHub，实现「改完代码，仓库实时更新」。

### 快速使用

```bash
# 前台运行（Ctrl+C 停止）
python scripts/auto_sync.py

# 后台常驻（Windows 双击）
scripts\start_auto_sync.bat     # 启动
scripts\stop_auto_sync.bat      # 停止

# 单次同步（适合挂到计划任务）
python scripts/auto_sync.py --once
```

### 核心机制

| 机制 | 说明 |
|---|---|
| 变更检测 | 走 `git status --porcelain`，**自动遵循 `.gitignore`**，日志/截图/上传文件不会被提交 |
| 防抖静默期 | 最后一次改动后再等 `--debounce` 秒（默认 8s）才提交，避免连续保存产生碎片提交 |
| 单实例锁 | `logs/auto_sync.lock` 记录 PID，防止多进程并发提交互相踩踏；进程已退出时自动清理僵尸锁 |
| 推送重试 | 网络故障指数退避重试（默认 3 次）；**认证失败不重试**并提示先手动登录 |
| 断点补推 | 推送失败时本地提交保留，网络恢复后自动补推（`--retry-interval`，默认 60s） |
| 安全兜底 | 额外排除 `logs/`、`node_modules/`、`.idea/`、`*.log`、`backend/app/uploads/` 等 |

### 常用参数

```bash
python scripts/auto_sync.py --interval 3        # 轮询间隔（默认 5 秒）
python scripts/auto_sync.py --debounce 15       # 静默期（默认 8 秒）
python scripts/auto_sync.py --dry-run           # 演练，只打印不提交
python scripts/auto_sync.py --no-push           # 只本地提交，不推送
python scripts/auto_sync.py --once              # 同步一次就退出
python scripts/auto_sync.py --exclude "path/"   # 额外排除路径
```

提交信息模板默认 `chore: 自动同步 {files} ({time})`，可用占位符：`{files}` `{count}` `{time}` `{date}`。

### 首次使用前先完成一次 GitHub 登录

凭据缓存在 Windows 凭据管理器后，守护进程才能无人值守推送：

```bash
git push -u origin main      # 首次会弹出浏览器授权，之后凭据自动复用
```

### IDE 原生方案（不想开后台进程时）

| IDE | 配置 |
|---|---|
| **IntelliJ IDEA** | `Settings → Version Control → Commit` 勾选 `Commit changes automatically`（延迟 30s）；用 `Ctrl+K`（Commit and Push）手动推送 |
| **VS Code** | `settings.json` 加 `"git.autoCommit": "afterDelay"` 与 `"git.postCommitCommand": "push"` |

---

## 开源许可

本项目采用 [MIT License](LICENSE) 开源许可协议，Copyright © 2026 Zdesp。

你可以自由地使用、复制、修改、合并、发布、分发、再授权和销售本软件的副本，唯一的条件是在所有副本或实质性部分中保留版权声明和许可声明。

> 免责声明：本软件按「原样」提供，不附带任何形式的担保，包括对适销性、特定用途适用性和非侵权性的担保。详见 LICENSE 全文。


<!-- auto-sync test marker -->
