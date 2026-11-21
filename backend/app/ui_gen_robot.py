"""Robot Framework + SeleniumLibrary 生成器（标准 RF 最佳实践）。

每条流程生成一个 .robot 文件：步骤编排 -> SeleniumLibrary 关键字序列，
可变值集中在同目录的 resource 变量文件；公共 setup/teardown 放在 common.resource。
"""
import io
import time
import zipfile

from .ui_gen_common import locator_for_robot, robot_escape, safe, validate_all

ROOT = "robot_ui_autotest"

COMMON_RESOURCE = '''*** Settings ***
Library    SeleniumLibrary
Library    Collections

*** Variables ***
${BROWSER}    chrome
${HEADLESS}    true

*** Keywords ***
打开目标网页
    [Arguments]    ${url}
    Open Browser    ${url}    ${BROWSER}    options=${BROWSER_OPTIONS}
    Set Browser Implicit Wait    5s

创建无头选项
    ${options}=    Evaluate    selenium.webdriver.ChromeOptions()    modules=selenium.webdriver
    IF    '${HEADLESS}' == 'true'
        Call Method    ${options}    add_argument    --headless=new
    END
    Call Method    ${options}    add_argument    --window-size=1440,900
    Call Method    ${options}    add_argument    --no-sandbox
    RETURN    ${options}

关闭浏览器
    Close All Browsers
'''


def _flow_resource(flow, idx):
    """每个流程的变量文件（YAML 风格 .resource 的 *** Variables *** 段）。"""
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
        "Suite Setup    创建无头选项",
        "Suite Teardown    关闭浏览器",
        "",
        "*** Test Cases ***",
        safe(flow["title"].strip()),
        "    [Tags]    autogen    flow",
    ]

    first_goto = True
    for i, s in enumerate(steps, start=1):
        action = s.get("action", "")
        target = (s.get("target") or "").strip() if isinstance(s.get("target"), str) else ""
        if action == "goto":
            if first_goto:
                # 首个 goto 用 Open Browser（带 options），后续用 Go To
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
            # SeleniumLibrary 没有 Title Should Contain，用 Get Title + Should Contain 组合
            lines.append(f"    ${{_title}}=    Get Title")
            lines.append(f"    Should Contain    ${{_title}}    ${{EXPECT_{i}}}")
        elif action == "wait":
            lines.append(f"    Sleep    ${{WAIT_{i}}}s")
    return "\n".join(lines) + "\n"


REQS = '''robotframework>=6.0
robotframework-seleniumlibrary>=6.0
selenium>=4.10
'''

README = '''# Robot Framework UI 自动化项目

由测试提效平台根据流程编排生成，使用 SeleniumLibrary。

## 运行

```bash
pip install -r requirements.txt
robot testcases/                              # 默认无头（common.resource 里 HEADLESS=true）
robot --variable HEADLESS:false testcases/    # 有头观察
```

本机需安装 Chrome。Selenium 4 会自动匹配下载 ChromeDriver。

## 结构

```
common.resource              # SeleniumLibrary 导入 + 浏览器开关/关闭关键字
testcases/flow_N.robot       # 每个流程一个测试套件（步骤 -> 关键字）
testcases/flow_N_data.resource # 该流程的可变值（改数据不用改用例）
```

## 关键字映射

| 编排动作 | Robot 关键字 |
|---|---|
| 打开网页 | Open Browser / Go To |
| 点击元素 | Click Element |
| 输入内容 | Input Text |
| 断言页面文本 | Wait Until Page Contains |
| 断言地址包含 | Location Should Contain |
| 断言页面标题 | Title Should Contain |
| 等待 | Sleep |
'''


def generate_robot(flows) -> tuple[bytes, str]:
    validate_all(flows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{ROOT}/requirements.txt", REQS)
        zf.writestr(f"{ROOT}/README.md", README)
        zf.writestr(f"{ROOT}/common.resource", COMMON_RESOURCE)
        zf.writestr(f"{ROOT}/testcases/.gitkeep", "")
        for idx, flow in enumerate(flows, start=1):
            zf.writestr(f"{ROOT}/testcases/flow_{idx}.robot", _flow_robot(flow, idx))
            zf.writestr(f"{ROOT}/testcases/flow_{idx}_data.resource", _flow_resource(flow, idx))
    return buf.getvalue(), f"robot_ui_autotest_{time.strftime('%Y%m%d_%H%M%S')}.zip"
