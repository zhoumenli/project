"""Robot Framework + SeleniumLibrary 生成器（标准 RF 最佳实践）。

统一能力：自定义执行顺序（用例名带序号前缀）、失败重试（--retry 参数 +
Robot 官方 Pabot 无关，用 robot.retry 需 RF>=7 内置 retry 关键字）、
失败截图（Test Teardown 失败即 Capture Page Screenshot）、
录屏（listener 每步截图合成 GIF，无 ffmpeg 依赖）。
"""
import io
import time
import zipfile

from .ui_gen_common import locator_for_robot, robot_escape, safe, validate_all

ROOT = "robot_ui_autotest"

COMMON_RESOURCE = '''*** Settings ***
Library    SeleniumLibrary
Library    Collections
Library    OperatingSystem
Library    String

*** Variables ***
${BROWSER}    chrome
${HEADLESS}    true

*** Keywords ***
创建无头选项
    ${options}=    Evaluate    selenium.webdriver.ChromeOptions()    modules=selenium.webdriver
    IF    '${HEADLESS}' == 'true'
        Call Method    ${options}    add_argument    --headless=new
    END
    Call Method    ${options}    add_argument    --window-size=1440,900
    Call Method    ${options}    add_argument    --no-sandbox
    RETURN    ${options}

 Suite 初始化
    ${opts}=    创建无头选项
    Set Suite Variable    ${BROWSER_OPTIONS}    ${opts}
    ${dirs}=    Create List    ${OUTPUT DIR}${/}screenshots    ${OUTPUT DIR}${/}frames
    FOR    ${d}    IN    @{dirs}
        Create Directory    ${d}
    END

全局失败截图
    Run Keyword If Test Failed    保存失败截图

保存失败截图
    ${name}=    Replace String    ${TEST NAME}    ${SPACE}    _
    Capture Page Screenshot    ${OUTPUT DIR}${/}screenshots${/}fail-${name}.png

关闭浏览器
    Close All Browsers
'''

# 录屏监听器：每个关键字结束后抓一帧，套件结束时合成 GIF 附到 log
RECORDER_LISTENER = '''# -*- coding: utf-8 -*-
"""Robot Framework 录屏监听器：每步截图，结束时合成 GIF（PIL，无 ffmpeg 依赖）。"""
import io
import os

from PIL import Image

FRAME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")


class Recorder:
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        self.frames = []

    def _snap(self, drv):
        try:
            png = drv.get_screenshot_as_png()
            self.frames.append(Image.open(io.BytesIO(png)).convert("RGB"))
        except Exception:
            pass

    def end_keyword(self, name, attrs):
        # 从已注册的 SeleniumLibrary 实例取当前 driver（library 名即 SeleniumLibrary）
        try:
            from robot.libraries.BuiltIn import BuiltIn
            lib = BuiltIn().get_library_instance("SeleniumLibrary")
            drv = lib.drivers.current
            if drv:
                self._snap(drv)
        except Exception:
            pass

    def close(self):
        if not self.frames:
            return
        frames = self.frames[-120:]
        frames = [f if f.width <= 960 else f.resize((960, int(f.height * 960 / f.width))) for f in frames]
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recording.gif")
        try:
            frames[0].save(out, save_all=True, append_images=frames[1:], duration=600, loop=0)
        except Exception:
            pass
'''


def _flow_resource(flow, idx):
    lines = ["*** Settings ***", "Resource    ../common.resource", "", "*** Variables ***"]
    for i, s in enumerate(flow["steps"], start=1):
        action = s.get("action", "")
        value = (s.get("value") or "").strip() if isinstance(s.get("value"), str) else ""
        target = (s.get("target") or "").strip() if isinstance(s.get("target"), str) else ""
        if action == "goto":
            lines.append(f"${{URL_{i}}}    {robot_escape(value)}")
        elif action == "input":
            lines.append(f"${{INPUT_{i}}}    {robot_escape(value)}")
        elif action in ("assert_text", "assert_url_contains", "assert_title"):
            val = target if action == "assert_text" else value
            lines.append(f"${{EXPECT_{i}}}    {robot_escape(val)}")
        elif action == "wait":
            lines.append(f"${{WAIT_{i}}}    {value}")
    return "\n".join(lines) + "\n"


def _flow_robot(flow, idx):
    steps = flow["steps"]
    lines = [
        "*** Settings ***",
        "Documentation    由测试提效平台自动生成 —— " + safe(flow["title"].strip()),
        "Resource    ../common.resource",
        f"Resource    flow_{idx}_data.resource",
        "Suite Setup     Suite 初始化",
        "Suite Teardown    关闭浏览器",
        "Test Teardown    全局失败截图",
        "",
        "*** Test Cases ***",
        # 用例名带序号前缀，保证自定义执行顺序（按编排顺序）
        f"{idx:02d}_" + safe(flow["title"].strip()),
        "    [Tags]    autogen    flow    order{}".format(idx),
    ]

    first_goto = True
    for i, s in enumerate(steps, start=1):
        action = s.get("action", "")
        target = (s.get("target") or "").strip() if isinstance(s.get("target"), str) else ""
        if action == "goto":
            if first_goto:
                lines.append(f"    Open Browser    ${{URL_{i}}}    ${{BROWSER}}    options=${{BROWSER_OPTIONS}}")
                lines.append("    Set Browser Implicit Wait    5s")
                first_goto = False
            else:
                lines.append(f"    Go To    ${{URL_{i}}}")
        elif action == "click":
            lines.append(f"    Click Element    {locator_for_robot(target)}")
        elif action == "input":
            lines.append(f"    Input Text    {locator_for_robot(target)}    ${{INPUT_{i}}}")
        elif action == "assert_text":
            lines.append(f"    Wait Until Page Contains    ${{EXPECT_{i}}}    15s")
        elif action == "assert_url_contains":
            lines.append(f"    Wait Until Keyword Succeeds    15s    1s    Location Should Contain    ${{EXPECT_{i}}}")
        elif action == "assert_title":
            lines.append(f"    ${{_title}}=    Get Title")
            lines.append(f"    Should Contain    ${{_title}}    ${{EXPECT_{i}}}")
        elif action == "wait":
            lines.append(f"    Sleep    ${{WAIT_{i}}}s")
    return "\n".join(lines) + "\n"


REQS = '''robotframework>=6.0
robotframework-seleniumlibrary>=6.0
selenium>=4.10
Pillow>=10.0
'''

README = '''# Robot Framework UI 自动化项目

由测试提效平台根据流程编排生成，使用 SeleniumLibrary。
已统一包含：自定义执行顺序、失败重试、失败截图、录屏。

## 运行

```bash
pip install -r requirements.txt
robot --variable HEADLESS:true testcases/                 # 默认无头
robot --variable HEADLESS:false testcases/                # 有头观察
robot --retry 2 testcases/                                # 失败自动重试 2 次
python main.py                                            # 按编排顺序+重试 2 次+录屏执行
```

- **执行顺序**：用例名带 `01_`/`02_` 序号前缀（即页面上的流程排列顺序），RF 按名称排序执行。
- **失败重试**：`robot --retry N`（RF 7+ 支持）；`main.py` 默认 `--retry 2`，可改。
- **失败截图**：`Test Teardown` 里失败即 `Capture Page Screenshot`，存到 screenshots/ 并附到 log.html。
- **录屏**：`main.py` 加载 `recorder.py` listener，每步截图结束合成 recording.gif。

## 结构

```
common.resource                  # SeleniumLibrary + 失败截图关键字 + 浏览器开关
recorder.py                      # 录屏 listener（每步截图 -> GIF）
main.py                          # 顺序+重试+录屏一键运行入口
testcases/flow_N.robot           # 序号前缀保证执行顺序
testcases/flow_N_data.resource   # 该流程的可变值
```
'''

MAIN_PY = '''# -*- coding: utf-8 -*-
"""一键运行：按编排顺序 + 失败重试 2 次 + 录屏 listener 执行。"""
import os
import subprocess
import sys

root = os.path.dirname(os.path.abspath(__file__))
cmd = [
    sys.executable, "-m", "robot",
    "--retry", "2",
    "--listener", os.path.join(root, "recorder.py"),
    os.path.join(root, "testcases"),
]
print("执行:", " ".join(cmd))
sys.exit(subprocess.call(cmd, cwd=root))
'''


def generate_robot(flows) -> tuple[bytes, str]:
    validate_all(flows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{ROOT}/requirements.txt", REQS)
        zf.writestr(f"{ROOT}/README.md", README)
        zf.writestr(f"{ROOT}/common.resource", COMMON_RESOURCE)
        zf.writestr(f"{ROOT}/recorder.py", RECORDER_LISTENER)
        zf.writestr(f"{ROOT}/main.py", MAIN_PY)
        zf.writestr(f"{ROOT}/testcases/.gitkeep", "")
        for idx, flow in enumerate(flows, start=1):
            zf.writestr(f"{ROOT}/testcases/flow_{idx}.robot", _flow_robot(flow, idx))
            zf.writestr(f"{ROOT}/testcases/flow_{idx}_data.resource", _flow_resource(flow, idx))
    return buf.getvalue(), f"robot_ui_autotest_{time.strftime('%Y%m%d_%H%M%S')}.zip"
