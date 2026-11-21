"""Python + Selenium + pytest 生成器（标准 Selenium 4 最佳实践，不依赖用户模板）。

沿用与 Playwright 版相同的编排语义：每条流程一个 Page 类 + 一个 pytest 用例，
可变值集中在 YAML，用 pytest.mark.parametrize 数据驱动。
"""
import io
import time
import zipfile
import yaml as pyyaml

from .ui_gen_common import safe, locator_for_selenium, validate_all

ROOT = "selenium_ui_autotest"

CONFTEST = '''# -*- coding: utf-8 -*-
"""pytest 夹具：每个用例独占一个浏览器实例，失败时自动截图附到 Allure。"""
import os
import time

import allure
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

import config

RESULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def _make_options():
    opts = ChromeOptions()
    if config.headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    return opts


@pytest.fixture
def driver():
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
    yield drv
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


def _test_py(flow, slug, cls):
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
@pytest.mark.parametrize("data", datas)
def test_SLUG(data, driver) -> None:
    flow_page = CLS(driver)
BODY
'''
    return (tpl.replace("TITLE", safe(flow["title"].strip()))
               .replace("SLUG", slug).replace("CLS", cls)
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
allure-pytest>=2.13
PyYAML>=6.0
'''

README = '''# Selenium + pytest UI 自动化项目

由测试提效平台根据流程编排生成，标准 Selenium 4 结构。

## 运行

```bash
pip install -r requirements.txt
pytest testcase                    # 默认无头
UI_HEADLESS=false pytest testcase  # 有头观察
python main.py                     # allure 报告
```

Selenium 4 自带 Selenium Manager，会自动匹配下载 ChromeDriver（需本机有 Chrome）。
若自动匹配失败（如离线环境），可手动指定驱动：
```bash
CHROMEDRIVER_PATH=/path/to/chromedriver pytest testcase
```
驱动版本需与本机 Chrome 版本对应。

## 结构

```
config.py                 # 目标地址 / headless / 等待配置
conftest.py               # driver fixture + 失败截图 + Allure 附件
Pages/base_page.py        # 通用操作与断言封装
Pages/flow_N_page.py      # 每个流程一个 Page 类
testcase/flow_Ncase/      # 测试用例（parametrize 数据驱动）
testdata/flow_N_data.yaml # 可变值（改数据不用改代码）
Tools/read_data.py        # YAML 读取
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
addopts = -v -s
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
            zf.writestr(f"{ROOT}/testcase/{slug}case/test_{slug}.py", _test_py(flow, slug, cls))
            zf.writestr(f"{ROOT}/testcase/{slug}case/__init__.py", "")
            zf.writestr(f"{ROOT}/testdata/{slug}_data.yaml", _data_yaml(flow, slug))
    return buf.getvalue(), f"selenium_ui_autotest_{time.strftime('%Y%m%d_%H%M%S')}.zip"
