"""Python + Selenium + pytest 生成器（标准 Selenium 4 最佳实践，不依赖用户模板）。

统一能力：自定义执行顺序（pytest-order 显式标记）、失败重试（pytest-rerunfailures）、
失败截图（pytest 钩子 + Allure 附件）、录屏（后台截图序列合成 GIF，无 ffmpeg 依赖）。
"""
import io
import time
import zipfile
import yaml as pyyaml

from .ui_gen_common import safe, locator_for_selenium, validate_all

ROOT = "selenium_ui_autotest"

CONFTEST = '''# -*- coding: utf-8 -*-
"""pytest 夹具：每用例独占浏览器；失败截图 + 全程录屏 + 失败重试均附到 Allure。"""
import io
import os
import threading
import time

import allure
import pytest
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

import config

RESULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
SCREEN_DIR = os.path.join(RESULT_DIR, "frames")
VIDEO_DIR = os.path.join(RESULT_DIR, "video")


def _make_options():
    opts = ChromeOptions()
    if config.headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    return opts


class ScreenRecorder:
    """后台定时截图，结束时合成 GIF 附到 Allure（不依赖 ffmpeg）。"""

    def __init__(self, drv, enabled, interval=0.6):
        self.drv, self.enabled, self.interval = drv, enabled, interval
        self.frames = []
        self._stop = threading.Event()
        self._thread = None

    def _loop(self):
        while not self._stop.is_set():
            try:
                png = self.drv.get_screenshot_as_png()
                self.frames.append(Image.open(io.BytesIO(png)).convert("RGB"))
            except Exception:
                pass
            self._stop.wait(self.interval)

    def start(self):
        if self.enabled:
            os.makedirs(SCREEN_DIR, exist_ok=True)
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop_and_attach(self, name):
        if not self.enabled:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        if not self.frames:
            return
        os.makedirs(VIDEO_DIR, exist_ok=True)
        path = os.path.join(VIDEO_DIR, "{}.gif".format(name))
        # 限制 GIF 大小：最多 120 帧，缩放至 960 宽
        frames = self.frames[-120:]
        frames = [f if f.width <= 960 else f.resize((960, int(f.height * 960 / f.width))) for f in frames]
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=600, loop=0)
        allure.attach.file(path, "执行录屏(GIF)", allure.attachment_type.GIF)


@pytest.fixture
def driver(request):
    # 可选：CHROMEDRIVER_PATH 指定本机 chromedriver，跳过 Selenium Manager 自动探测
    driver_path = os.getenv("CHROMEDRIVER_PATH", "")
    if driver_path and os.path.isfile(driver_path):
        from selenium.webdriver.chrome.service import Service
        drv = webdriver.Chrome(service=Service(executable_path=driver_path), options=_make_options())
    else:
        drv = webdriver.Chrome(options=_make_options())
    drv.implicitly_wait(config.implicit_wait)
    if not config.headless:
        drv.maximize_window()
    recorder = ScreenRecorder(drv, config.video_enabled)
    recorder.start()
    request.node._tef_recorder = recorder
    yield drv
    # Allure 附件在用例结束时采集，录屏先停并落盘
    recorder.stop_and_attach("video-{}".format(time.strftime("%Y%m%d-%H%M%S")))
    try:
        drv.quit()
    except Exception:
        pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    drv = item.funcargs.get("driver")
    if drv is None:
        return
    os.makedirs(RESULT_DIR, exist_ok=True)
    name = "fail-{}.png".format(time.strftime("%Y%m%d-%H%M%S"))
    path = os.path.join(RESULT_DIR, name)
    try:
        drv.save_screenshot(path)
        allure.attach.file(path, "执行失败截图", allure.attachment_type.PNG)
    except Exception:
        pass
'''

BASE_PAGE = '''# -*- coding: utf-8 -*-
"""基础页面对象：封装查找/点击/输入/等待/断言，所有流程 Page 继承它。"""
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config


class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, config.explicit_wait)

    # ---------- 操作 ----------
    def open_target(self, url):
        self.driver.get(url)

    def click_el(self, by, locator):
        el = self.wait.until(EC.element_to_be_clickable((by, locator)))
        el.click()

    def fill_el(self, by, locator, value):
        el = self.wait.until(EC.visibility_of_element_located((by, locator)))
        el.clear()
        el.send_keys(str(value or ""))

    def wait_seconds(self, sec):
        time.sleep(float(sec))

    # ---------- 断言 ----------
    def assert_text(self, text):
        self.wait.until(lambda d: text in d.find_element(By.TAG_NAME, "body").text)

    def assert_url_contains(self, part):
        self.wait.until(EC.url_contains(part))

    def assert_title_contains(self, title):
        self.wait.until(lambda d: title in d.title)
'''


def _config_py(first_url):
    return f'''# -*- coding: utf-8 -*-
"""由测试提效平台生成 —— Selenium 自动化项目配置。"""
import os

# 目标站点地址（取自流程第一个"打开网页"步骤）
base_url = os.getenv("UI_BASE_URL", {first_url!r})

# 浏览器是否无头运行：UI_HEADLESS=true
headless = os.getenv("UI_HEADLESS", "true").lower() == "true"

# 等待配置（秒）
implicit_wait = float(os.getenv("UI_IMPLICIT_WAIT", "5"))
explicit_wait = float(os.getenv("UI_EXPLICIT_WAIT", "15"))

# 是否录屏（后台截图合成 GIF 附到 Allure）
video_enabled = os.getenv("UI_VIDEO", "true").lower() != "false"
'''


def _page_py(flow, slug, cls):
    elements, methods = [], []
    for i, s in enumerate(flow["steps"], start=1):
        action = s.get("action", "")
        target = (s.get("target") or "").strip() if isinstance(s.get("target"), str) else ""
        if action in ("click", "input"):
            by, val = locator_for_selenium(target)
            elements.append(f"    # 步骤{i} {action}目标: {target}")
            elements.append(f"    EL_{i} = ({by}, {val})")
            if action == "click":
                methods.append(f'''
    def click_el_{i}(self):
        self.click_el(*self.EL_{i})''')
            else:
                methods.append(f'''
    def fill_el_{i}(self, value):
        self.fill_el(*self.EL_{i}, value)''')
        elif action == "assert_text":
            methods.append(f'''
    def assert_text_{i}(self, text):
        self.assert_text(text)''')

    tpl = '''# -*- coding: utf-8 -*-
"""由测试提效平台自动生成 —— 流程: TITLE

对应用例: testcase/SLUGcase/test_SLUG.py
"""
from selenium.webdriver.common.by import By

from Pages.base_page import BasePage


class CLS(BasePage):
    """TITLE（Page Object，继承 BasePage）。"""

    # 元素定位（按编排步骤顺序生成）
ELEMENTS
METHODS
'''
    return (tpl.replace("TITLE", safe(flow["title"].strip()))
               .replace("SLUG", slug).replace("CLS", cls)
               .replace("ELEMENTS", "\n".join(elements) if elements else "    # （本流程无需元素定位）")
               .replace("METHODS", "\n".join(methods)))


def _test_py(flow, slug, cls, order):
    body = []
    for i, s in enumerate(flow["steps"], start=1):
        action = s.get("action", "")
        value = (s.get("value") or "").strip() if isinstance(s.get("value"), str) else ""
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
"""由测试提效平台自动生成 —— 流程: TITLE

每条用例独占一个浏览器实例；可变值集中在 testdata/SLUG_data.yaml。
显式执行顺序：第 ORDER 条（用 pytest-order 保证，不依赖文件收集顺序）。
"""
import os

import allure
import pytest

from Pages.SLUG_page import CLS
from Tools.read_data import read

obj_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

datas = read(os.path.join(obj_path, "testdata/SLUG_data.yaml"), kw=None)


@allure.epic("UI 流程编排")
@allure.feature("TITLE")
@allure.title("{data[title]}")
@pytest.mark.order(ORDER)
@pytest.mark.parametrize("data", datas)
def test_SLUG(data, driver) -> None:
    flow_page = CLS(driver)
BODY
'''
    return (tpl.replace("TITLE", safe(flow["title"].strip()))
               .replace("SLUG", slug).replace("CLS", cls).replace("ORDER", str(order))
               .replace("BODY", "\n".join(body)))


def _data_yaml(flow, slug):
    row = {"title": flow["title"].strip()}
    for i, s in enumerate(flow["steps"], start=1):
        action = s.get("action", "")
        target = (s.get("target") or "").strip() if isinstance(s.get("target"), str) else ""
        value = (s.get("value") or "").strip() if isinstance(s.get("value"), str) else ""
        if action in ("input", "assert_text", "assert_url_contains", "assert_title"):
            row[f"value_{i}"] = target if action == "assert_text" else value
    return pyyaml.safe_dump([row], allow_unicode=True, sort_keys=False, default_flow_style=False)


REQS = '''selenium>=4.10
pytest>=7.4
pytest-order>=1.2          # 自定义执行顺序 @pytest.mark.order
pytest-rerunfailures>=14    # 失败自动重试 --reruns
allure-pytest>=2.13
PyYAML>=6.0
Pillow>=10.0               # 录屏 GIF 合成
'''

README = '''# Selenium + pytest UI 自动化项目

由测试提效平台根据流程编排生成，标准 Selenium 4 结构。
已统一包含：自定义执行顺序、失败重试、失败截图、录屏。

## 运行

```bash
pip install -r requirements.txt
pytest testcase                    # 默认无头，按编排顺序执行
UI_HEADLESS=false pytest testcase  # 有头观察
python main.py                     # allure 报告（含失败截图与录屏）
```

- **执行顺序**：用例带 `@pytest.mark.order(N)`，N 即页面上流程的排列顺序。
- **失败重试**：`pytest.ini` 里 `--reruns=2`（改数字即可调整；重试间隔 `--reruns-delay`）。
- **失败截图**：失败时自动截图附到 Allure 报告。
- **录屏**：后台每 0.6s 截图，结束合成 GIF 附到报告；`UI_VIDEO=false pytest` 关闭。

Selenium 4 自带 Selenium Manager 自动匹配 ChromeDriver。若自动匹配失败（如离线环境）：
```bash
CHROMEDRIVER_PATH=/path/to/chromedriver pytest testcase
```

## 结构

```
config.py                 # 目标地址 / headless / 等待 / 录屏开关
conftest.py               # driver fixture + 录屏器 + 失败截图 + Allure 附件
pytest.ini                # reruns 重试配置
Pages/base_page.py        # 通用操作与断言封装
Pages/flow_N_page.py      # 每个流程一个 Page 类
testcase/flow_Ncase/      # 测试用例（order + parametrize 数据驱动）
testdata/flow_N_data.yaml # 可变值（改数据不用改代码）
```
'''

MAIN_PY = '''import os
import pytest

if __name__ == "__main__":
    pytest.main(["--alluredir=./reports/json", "--clean-alluredir"])
    os.system("allure generate ./reports/json -o ./reports/html --clean")
'''

READ_DATA = '''import yaml


def read(file, kw=None):
    with open(file, "r", encoding="utf-8") as f:
        datas = yaml.safe_load(f)
    if kw:
        return [d for d in datas if d.get("kw") == kw]
    return datas
'''

PYTEST_INI = '''[pytest]
addopts = -v -s --reruns=2 --reruns-delay=1
testpaths = testcase
python_files = test*.py
python_functions = test*
'''


def generate_selenium(flows) -> tuple[bytes, str]:
    validate_all(flows)
    buf = io.BytesIO()
    first_url = next((s.get("value", "").strip() for f in flows for s in f["steps"]
                      if s.get("action") == "goto" and s.get("value")), "")
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{ROOT}/config.py", _config_py(first_url))
        zf.writestr(f"{ROOT}/conftest.py", CONFTEST)
        zf.writestr(f"{ROOT}/pytest.ini", PYTEST_INI)
        zf.writestr(f"{ROOT}/main.py", MAIN_PY)
        zf.writestr(f"{ROOT}/requirements.txt", REQS)
        zf.writestr(f"{ROOT}/README.md", README)
        zf.writestr(f"{ROOT}/Tools/read_data.py", READ_DATA)
        zf.writestr(f"{ROOT}/Pages/__init__.py", "")
        zf.writestr(f"{ROOT}/Pages/base_page.py", BASE_PAGE)
        zf.writestr(f"{ROOT}/testcase/__init__.py", "")
        for idx, flow in enumerate(flows, start=1):
            slug, cls = f"flow_{idx}", f"Flow{idx}Page"
            zf.writestr(f"{ROOT}/Pages/{slug}_page.py", _page_py(flow, slug, cls))
            zf.writestr(f"{ROOT}/testcase/{slug}case/test_{slug}.py", _test_py(flow, slug, cls, idx))
            zf.writestr(f"{ROOT}/testcase/{slug}case/__init__.py", "")
            zf.writestr(f"{ROOT}/testdata/{slug}_data.yaml", _data_yaml(flow, slug))
    return buf.getvalue(), f"selenium_ui_autotest_{time.strftime('%Y%m%d_%H%M%S')}.zip"
