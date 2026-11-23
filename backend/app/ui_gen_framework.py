"""UI 自动化生成项目的公共框架能力模块。

从模板框架（initial_ui_framework）提炼的框架级能力，供 Selenium / Robot 生成器
写入生成项目，保证与 Playwright 版功能对等：
- 文件日志 my_logger
- HTTP Basic 认证（siteguard）
- 登录态复用（cookies/storage_state）
- Cookie 弹层处理
- 独立断言工具
- 统一产物目录（screenshots/trace/video/logs）
"""
import re

# ============ 文件日志器（对应 Tools/my_logger.py）============
MY_LOGGER_PY = '''# -*- coding: utf-8 -*-
"""日志封装：控制台 + 文件双输出（对应框架 Tools/my_logger.py）。"""
import logging
import os
import time


class MyLogger:
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        if self.logger.handlers:
            return  # 避免重复添加 handler
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        file_name = "{}.log".format(time.strftime("%Y%m%d"))
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        if not os.path.isdir(file_path):
            os.makedirs(file_path)
        fh = logging.FileHandler(filename=os.path.join(file_path, file_name), encoding="utf-8")
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s|%(lineno)s|%(message)s')
        sh.setFormatter(formatter)
        fh.setFormatter(formatter)
        self.logger.addHandler(sh)
        self.logger.addHandler(fh)


logger = MyLogger().logger
'''


# ============ Cookie 弹层处理（对应 Tools/cookie.py）============
COOKIE_PY = '''# -*- coding: utf-8 -*-
"""Cookie 弹层处理：点掉同意按钮 + 清除残留遮罩。

 Selenium 版：传入 driver（WebDriver），用 find_elements 检测。
"""
from Tools.my_logger import logger

COOKIE_ACCEPT_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button:has-text('Accept')",
    "#acceptCookies",
]
COOKIE_OVERLAY_SELECTORS = [".onetrust-pc-dark-filter", "#onetrust-consent-sdk"]


def dismiss_cookie_overlay(driver, timeout=3, label=""):
    """存在就点掉 Cookie 弹层并清残留遮罩，不存在则直接返回。"""
    dismissed = False
    for sel in COOKIE_ACCEPT_SELECTORS:
        try:
            els = driver.find_elements("css selector", sel)
            if els and els[0].is_displayed():
                els[0].click()
                dismissed = True
                logger.info("{}关闭 Cookie 弹层成功: {}".format(label, sel))
                break
        except Exception:
            pass
    # 清残留遮罩（它们不自行消失，会拦截后续点击）
    for sel in COOKIE_OVERLAY_SELECTORS:
        try:
            driver.execute_script(
                "document.querySelectorAll(arguments[0]).forEach(e => e.remove());", sel)
        except Exception:
            pass
    return dismissed
'''


# ============ 登录态复用工具（对应 login_state/logged_in_page）============
AUTH_PY = '''# -*- coding: utf-8 -*-
"""登录态复用：把登录后的 cookies 存入文件，后续用例直接注入，避免重复登录。

用法（在编排里增加「保存登录态」步骤，或用代码调用）：
    save_login_state(driver, "state.json")
    restore_login_state(driver, "state.json")
"""
import json
import os

from Tools.my_logger import logger


def save_login_state(driver, path="state.json"):
    """保存当前 cookies 到文件。"""
    cookies = driver.get_cookies()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    logger.info("登录态已保存: {} ({} cookies)".format(path, len(cookies)))
    return path


def restore_login_state(driver, path="state.json", url=None):
    """注入已保存的 cookies；文件不存在或过期返回 False。"""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    if url:
        driver.get(url)
    for c in cookies:
        try:
            driver.add_cookie(c)
        except Exception:
            pass
    if url:
        driver.refresh()
    logger.info("已注入登录态: {}".format(path))
    return True
'''


# ============ HTTP Basic 认证（对应 siteguard）============
def basic_auth_options_snippet() -> str:
    """返回 Selenium ChromeOptions 里加 Basic 认证的处理说明（浏览器 Basic 认证用 URL 前缀）。"""
    return '''# HTTP Basic 认证：目标站点若有网关认证，可在 URL 里带凭证：
#   http://username:password@host/path
# 或在 config.py 里配置 siteguard，由 open_target 自动拼接。'''


# ============ 独立断言工具（对应 Tools/assertion.py）============
ASSERTION_PY = '''# -*- coding: utf-8 -*-
"""断言工具：URL / 标题 / 文本等待式断言（对应框架 Tools/assertion.py）。"""
import re

from selenium.webdriver.support.ui import WebDriverWait
from Tools.my_logger import logger


def assert_url_contains(driver, part, timeout=15):
    WebDriverWait(driver, timeout).until(lambda d: part in d.current_url)
    logger.info("URL 断言通过: {}".format(driver.current_url))


def assert_title_contains(driver, title, timeout=15):
    WebDriverWait(driver, timeout).until(lambda d: title in d.title)
    logger.info("标题断言通过: {}".format(driver.title))


def assert_page_contains(driver, text, timeout=15):
    WebDriverWait(driver, timeout).until(
        lambda d: text in d.find_element("tag name", "body").text)
    logger.info("文本断言通过: {}".format(text))
'''


# ============ 产物目录说明（对应 result/）============
OUTPUT_DIRS_NOTE = '''# 产物目录（对应框架 result/）：
#   logs/               运行日志（my_logger）
#   results/image/      失败截图
#   results/trace/      失败追踪（Playwright trace / Selenium 步骤序列）
#   results/video/      全程录屏（GIF）
#   state.json          登录态 cookies（可选）'''
