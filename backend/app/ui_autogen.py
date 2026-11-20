"""
UI 自动化项目生成器：按用户提供的步骤编排（打开网页→点击→输入→断言…）
以本地 UI 框架模板（Page Object + pytest + allure + 录屏/追踪）为骨架，
生成完整可运行的 pytest 项目 zip。

模板路径可通过环境变量 UI_TEMPLATE_DIR 配置，默认 C:\\project\\initial_ui_framework。
只取框架文件（conftest / pytest.ini / main.py / Tools），业务用例层全量生成。
"""
import os
import io
import re
import zipfile
import yaml as pyyaml

FRAMEWORK_DIR = os.getenv("UI_TEMPLATE_DIR", r"C:\project\initial_ui_framework")

# 支持的动作：key -> (前端展示名, 说明)
ACTIONS = {
    "goto": ("打开网页", "value 填目标 URL"),
    "click": ("点击元素", "target 填选择器（CSS/XPath/text=）"),
    "input": ("输入内容", "target 填选择器，value 填输入值"),
    "assert_text": ("断言页面文本", "target 填期望出现的文本"),
    "assert_url_contains": ("断言地址包含", "value 填地址片段"),
    "assert_title": ("断言页面标题", "value 填标题片段"),
    "wait": ("等待", "value 填秒数"),
}

# 拷贝的框架文件（相对路径）——只取框架，不拷业务 Page/用例/数据
FRAMEWORK_FILES = [
    "pytest.ini",
    "main.py",
    "Tools/my_logger.py",
    "Tools/read_data.py",
    "Tools/page_action.py",
    "Tools/assertion.py",
    "Tools/cookie.py",
    "testcase/conftest.py",
    "testcase/preconditions.py",
]

# 生成 config.py 必须覆盖的框架引用属性（testcase/conftest.py + Tools/* 用到）
# headless / ignore_https_errors / image_dir / trace_dir / screen_size / siteguard /
# submit_pause / use_full_screen / video_dir / video_enabled / video_size /
# viewport_mode / viewport_size / PAGE_URL_PATTERN


def _validate_flow(flow, idx):
    if not (flow.get("title") or "").strip():
        raise ValueError(f"第 {idx + 1} 个流程缺少标题")
    steps = flow.get("steps") or []
    if not steps:
        raise ValueError(f"流程「{flow.get('title')}」没有步骤")
    for j, s in enumerate(steps):
        action = (s.get("action") or "").strip()
        if action not in ACTIONS:
            raise ValueError(f"流程「{flow.get('title')}」步骤 {j + 1} 使用了不支持的动作: {action}")
        target = (s.get("target") or "").strip() if s.get("target") else ""
        value = (s.get("value") or "").strip() if s.get("value") is not None else ""
        if action == "goto" and not value:
            raise ValueError(f"步骤 {j + 1} 打开网页需要填写 URL")
        if action == "click" and not target:
            raise ValueError(f"步骤 {j + 1} 点击元素需要填写目标定位")
        if action == "input" and (not target or not value):
            raise ValueError(f"步骤 {j + 1} 输入内容需要填写目标定位和输入值")
        if action == "assert_text" and not target:
            raise ValueError(f"步骤 {j + 1} 断言文本需要填写期望文本")
        if action in ("assert_url_contains", "assert_title") and not value:
            raise ValueError(f"步骤 {j + 1} 断言需要填写期望值")
        if action == "wait":
            try:
                float(value)
            except ValueError:
                raise ValueError(f"步骤 {j + 1} 等待的秒数必须是数字")


def _resolve_locator(target: str) -> str:
    """把用户填的目标翻译成 Playwright 定位表达式（生成代码里的右值）。"""
    t = target.strip()
    # 含选择器特征（. # [ > : = @ 或以 / 开头）按 CSS/XPath/text= 处理；否则按页面文本匹配
    if "=" in t or t.startswith("/") or re.search(r'[.\[#>:@]', t):
        return f"self.page.locator({t!r})"
    return f"self.page.get_by_text({t!r})"


def _safe(s: str) -> str:
    """把动态文本安全嵌入生成的 Python 双引号字符串字面量。"""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _gen_page_py(flow, slug, cls) -> str:
    """生成 Pages/<slug>_page.py：元素定位 + 步骤方法（框架 Page Object 风格）。"""
    elements, methods = [], []
    for i, s in enumerate(flow["steps"], start=1):
        action = s.get("action", "")
        target = (s.get("target") or "").strip()
        safe = _safe(target)
        if action == "click":
            elements.append(f"        self.el_{i} = {_resolve_locator(target)}  # 步骤{i} 点击目标")
            methods.append(f'''
    def click_el_{i}(self):
        with allure.step("点击元素: {safe}"):
            self.el_{i}.first.click()
            logger.info("点击成功: {safe}")''')
        elif action == "input":
            elements.append(f"        self.el_{i} = {_resolve_locator(target)}  # 步骤{i} 输入目标")
            methods.append(f'''
    def fill_el_{i}(self, value):
        with allure.step("输入 [{safe}]: {{}}".format(value)):
            self.el_{i}.first.fill(str(value or ""))
            logger.info("输入完成: {safe}")''')
        elif action == "assert_text":
            methods.append(f'''
    def assert_text_{i}(self, text):
        with allure.step("断言页面出现文本: {{}}".format(text)):
            expect(self.page.get_by_text(str(text)).first).to_be_visible(timeout=10000)
            logger.info("文本可见: {{}}".format(text))''')

    tpl = '''# -*- coding: utf-8 -*-
"""由测试提效平台自动生成 —— 流程编排: __TITLE__

对应用例: testcase/__SLUG__case/test___SLUG__.py
测试数据: testdata/__SLUG___data.yaml
"""
import re

from playwright.sync_api import Page, expect

import allure

from Tools.my_logger import logger


class __CLASS__:
    """__TITLE__（Page Object：组合持有 page，不继承）。"""

    def __init__(self, page: Page):
        # 持有真实的 page 对象（组合，与框架 Pages/* 一致）
        self.page = page
        # 元素定位（按编排步骤顺序自动生成）
__ELEMENTS__

    # ---------- 步骤方法 ----------
__METHODS__

    # ---------- 通用操作 ----------
    def open_target(self, url):
        with allure.step("打开网页: {}".format(url)):
            self.page.goto(url, wait_until="domcontentloaded")
            logger.info("页面打开成功: {}".format(url))

    def assert_url_contains(self, part):
        with allure.step("断言地址包含: {}".format(part)):
            # 轮询等待跳转完成（点击提交后 URL 变化是异步的）
            expect(self.page).to_have_url(re.compile(re.escape(part)), timeout=15000)
            logger.info("地址断言通过: {}".format(self.page.url))

    def assert_title_contains(self, title):
        with allure.step("断言页面标题包含: {}".format(title)):
            expect(self.page).to_have_title(re.compile(re.escape(title), re.IGNORECASE))
            logger.info("标题断言通过: {}".format(self.page.title()))

    def wait_seconds(self, sec):
        with allure.step("等待 {} 秒".format(sec)):
            self.page.wait_for_timeout(int(float(sec) * 1000))
            logger.info("等待结束")
'''
    out = tpl.replace("__TITLE__", _safe(flow["title"].strip())).replace("__SLUG__", slug).replace("__CLASS__", cls)
    out = out.replace("__ELEMENTS__", "\n".join(elements) if elements else "        # （本流程无需元素定位）")
    out = out.replace("__METHODS__", "\n".join(methods))
    return out


def _gen_test_py(flow, slug, cls) -> str:
    """生成 testcase/<slug>case/test_<slug>.py：fresh_page fixture + 显式步骤调用。"""
    body = []
    for i, s in enumerate(flow["steps"], start=1):
        action = s.get("action", "")
        value = (s.get("value") or "").strip()
        if action == "goto":
            body.append(f"    flow_page.open_target({value!r})")
        elif action == "input":
            body.append(f'    flow_page.fill_el_{i}(data["value_{i}"])')
        elif action == "click":
            body.append(f"    flow_page.click_el_{i}()")
        elif action == "assert_text":
            body.append(f'    flow_page.assert_text_{i}(data["value_{i}"])')
        elif action == "assert_url_contains":
            body.append(f'    flow_page.assert_url_contains(data["value_{i}"])')
        elif action == "assert_title":
            body.append(f'    flow_page.assert_title_contains(data["value_{i}"])')
        elif action == "wait":
            body.append(f"    flow_page.wait_seconds({float(value)})")

    tpl = '''# -*- coding: utf-8 -*-
"""由测试提效平台自动生成 —— 流程编排: __TITLE__

每条流程用 fresh_page 独占一个 context，互不影响；
可变值集中在 testdata/__SLUG___data.yaml，改数据不用改代码。
"""
import allure
import pytest
from playwright.sync_api import Page

from Pages.__SLUG___page import __CLASS__
from Tools.my_logger import logger
from Tools.read_data import read
import os

obj_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

datas = read(os.path.join(obj_path, "testdata/__SLUG___data.yaml"), kw=None)

EPIC = "UI 流程编排"
STORY = "__TITLE__"


@allure.epic(EPIC)
@allure.feature("__TITLE__")
@allure.story(STORY)
@allure.title("{data[title]}")
@pytest.mark.parametrize("data", datas)
def test___SLUG__(data, fresh_page: Page) -> None:
    logger.info("开始执行流程编排: {}".format(data["title"]))
    flow_page = __CLASS__(fresh_page)
__BODY__
'''
    out = tpl.replace("__TITLE__", _safe(flow["title"].strip())).replace("__SLUG__", slug).replace("__CLASS__", cls)
    return out.replace("__BODY__", "\n".join(body))


def _gen_data_yaml(flow, slug) -> str:
    """生成 testdata/<slug>_data.yaml：标题行 + 各步骤的可变值。"""
    row = {"title": flow["title"].strip()}
    for i, s in enumerate(flow["steps"], start=1):
        action = s.get("action", "")
        target = (s.get("target") or "").strip() if s.get("target") else ""
        value = (s.get("value") or "").strip() if s.get("value") is not None else ""
        if action in ("input", "assert_text", "assert_url_contains", "assert_title"):
            row[f"value_{i}"] = target if action == "assert_text" else value
    return pyyaml.safe_dump([row], allow_unicode=True, sort_keys=False, default_flow_style=False)


CONFIG_TMPL = '''# -*- coding: utf-8 -*-
"""由测试提效平台自动生成的项目配置。

框架级开关（视口/录屏/停顿）与模板 config.py 保持一致；
业务站点地址/凭证已清空，按目标站点自行填写或用环境变量覆盖。
"""
import os

# ---------- 目标站点 ----------
# 目标站点地址（取自流程编排的第一个"打开网页"步骤，可按需修改）
base_url = os.getenv("UI_BASE_URL", __BASE_URL__)

# SiteGuard 网关：HTTP Basic 认证。目标站点无网关认证时保持为空。
siteguard = {
    "username": os.getenv("SITEGUARD_USER", ""),
    "password": os.getenv("SITEGUARD_PASSWORD", ""),
}

# 业务站点账号（流程用例需要登录态时使用）
account = {
    "userid": os.getenv("UI_ACCOUNT_USER", ""),
    "password": os.getenv("UI_ACCOUNT_PASSWORD", ""),
}

# 页面路径与 URL 断言模式（按需补充；生成用例的 URL 断言不依赖这里）
PAGE_PATH = {}
PAGE_URL_PATTERN = {}

# 浏览器是否无头运行；UI_HEADLESS=true 可切无头
headless = os.getenv("UI_HEADLESS", "false").lower() == "true"

# 测试环境证书异常时放行
ignore_https_errors = os.getenv("UI_IGNORE_HTTPS_ERRORS", "false").lower() == "true"


def _detect_screen_size():
    """读取主显示器的逻辑分辨率；读不到时返回 None。"""
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        size = (root.winfo_screenwidth(), root.winfo_screenheight())
        root.destroy()
        return size
    except Exception:
        return None


_SCREEN_SIZE = _detect_screen_size()

# 浏览器窗口尺寸：max / fullscreen / 宽x高（如 1440x900）
viewport_mode = os.getenv("UI_VIEWPORT", "max").strip().lower()

use_full_screen = viewport_mode in ("max", "fullscreen")
fullscreen_flag = viewport_mode == "fullscreen"

if use_full_screen:
    viewport_size = None
else:
    try:
        _width, _height = viewport_mode.split("x")
        viewport_size = {"width": int(_width), "height": int(_height)}
    except Exception:
        raise ValueError(
            "UI_VIEWPORT 取值无效：{}，应为 max/fullscreen 或 宽x高（如 1440x900）".format(viewport_mode))

screen_size = _SCREEN_SIZE

# ---------- 输出目录 ----------
output_root = os.getenv("UI_OUTPUT_DIR", "results")
image_dir = os.path.join(output_root, "image")
trace_dir = os.path.join(output_root, "trace")

# ---------- 录屏 ----------
video_enabled = os.getenv("UI_VIDEO", "true").lower() != "false"
video_dir = os.getenv("UI_VIDEO_DIR", os.path.join(output_root, "video"))
video_size = None

# ---------- 操作停顿 ----------
# 每次提交前的停留秒数（便于录屏观察），设为 0 可关闭
submit_pause = float(os.getenv("UI_SUBMIT_PAUSE", "2"))

# 滚动到底部后的停留秒数
scroll_stay = float(os.getenv("UI_SCROLL_STAY", "2"))
'''


def _gen_config_py(flows) -> str:
    first_url = ""
    for f in flows:
        for s in f["steps"]:
            if s.get("action") == "goto" and (s.get("value") or "").strip():
                first_url = s["value"].strip()
                break
        if first_url:
            break
    return CONFIG_TMPL.replace("__BASE_URL__", repr(first_url))


REQS = '''playwright>=1.40
pytest>=7.4
pytest-playwright>=0.4
allure-pytest>=2.13
PyYAML>=6.0
'''

README_TMPL = '''# UI 自动化测试项目（由测试提效平台生成）

由流程编排自动生成的 pytest + Playwright 项目，沿用框架模板结构
（Page Object + allure 步骤 + YAML 数据驱动 + 失败截图/追踪/全程录屏）。

## 运行

```bash
pip install -r requirements.txt
playwright install chromium

# 有头模式（默认，窗口最大化，可观察执行过程）
pytest testcase

# 无头模式
UI_HEADLESS=true pytest testcase          # Linux/Mac
set UI_HEADLESS=true && pytest testcase   # Windows

# allure 报告
python main.py     # 生成 reports/html
```

## 结构

```
config.py                 # 目标站点 / Basic 认证 / headless / 视口 / 录屏开关
pytest.ini / main.py      # pytest 配置与 allure 报告入口
Tools/                    # 日志 / YAML 读取 / 操作辅助 / URL 断言 / Cookie 弹层
testcase/conftest.py      # 浏览器与 fresh_page/shared_page fixture、录屏、失败现场
testcase/preconditions.py # 前置状态检查工具
Pages/flow_N_page.py      # 每个流程一个 Page 类（元素定位 + 步骤方法）
testcase/flow_Ncase/      # 测试用例（parametrize 数据驱动）
testdata/flow_N_data.yaml # 流程标题与可变值（改值无需改代码）
```

## 编排步骤对应关系

| 编排动作 | 生成的 Page 方法 |
|---|---|
| 打开网页 | `open_target(url)` |
| 点击元素 | `click_el_N()` |
| 输入内容 | `fill_el_N(value)` |
| 断言页面文本 | `assert_text_N(text)` |
| 断言地址包含 | `assert_url_contains(part)` |
| 断言页面标题 | `assert_title_contains(title)` |
| 等待 | `wait_seconds(sec)` |
'''


def generate_ui_project(flows: list) -> tuple[bytes, str]:
    """按流程编排生成完整项目 zip。返回 (zip_bytes, filename)。"""
    if not flows:
        raise ValueError("至少需要一个流程编排")
    for idx, f in enumerate(flows):
        _validate_flow(f, idx)

    missing = [f for f in FRAMEWORK_FILES if not os.path.isfile(os.path.join(FRAMEWORK_DIR, f))]
    if missing:
        raise FileNotFoundError(f"UI 框架模板缺少文件: {missing}（模板目录: {FRAMEWORK_DIR}，可用 UI_TEMPLATE_DIR 配置）")

    buf = io.BytesIO()
    root = "ui_flow_autotest"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in FRAMEWORK_FILES:
            with open(os.path.join(FRAMEWORK_DIR, rel), "r", encoding="utf-8") as fh:
                zf.writestr(f"{root}/{rel}", fh.read())
        zf.writestr(f"{root}/config.py", _gen_config_py(flows))
        zf.writestr(f"{root}/requirements.txt", REQS)
        zf.writestr(f"{root}/README.md", README_TMPL)
        for idx, flow in enumerate(flows, start=1):
            slug, cls = f"flow_{idx}", f"Flow{idx}Page"
            zf.writestr(f"{root}/Pages/{slug}_page.py", _gen_page_py(flow, slug, cls))
            zf.writestr(f"{root}/testcase/{slug}case/test_{slug}.py", _gen_test_py(flow, slug, cls))
            zf.writestr(f"{root}/testdata/{slug}_data.yaml", _gen_data_yaml(flow, slug))
    import time
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return buf.getvalue(), f"ui_flow_autotest_{stamp}.zip"
