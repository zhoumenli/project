"""UI 自动化多框架生成器的公共工具：步骤校验、文本转义、定位表达式。

步骤编排是与语言无关的中间表示，两种新框架（Selenium+pytest / Robot Framework）
共用这里的校验和定位逻辑，保证三者对同一份编排的语义一致。
"""

ACTIONS = {
    "goto": ("打开网页", "value 填目标 URL"),
    "click": ("点击元素", "target 填选择器（CSS/XPath/text=）"),
    "input": ("输入内容", "target 填选择器，value 填输入值"),
    "assert_text": ("断言页面文本", "target 填期望出现的文本"),
    "assert_url_contains": ("断言地址包含", "value 填地址片段"),
    "assert_title": ("断言页面标题", "value 填标题片段"),
    "wait": ("等待", "value 填秒数"),
}


def _t(v) -> str:
    return (v or "").strip() if isinstance(v, str) else ""


def validate_flow(flow, idx):
    if not _t(flow.get("title")):
        raise ValueError(f"第 {idx + 1} 个流程缺少标题")
    steps = flow.get("steps") or []
    if not steps:
        raise ValueError(f"流程「{flow.get('title')}」没有步骤")
    for j, s in enumerate(steps):
        action = _t(s.get("action"))
        if action not in ACTIONS:
            raise ValueError(f"流程「{flow.get('title')}」步骤 {j + 1} 使用了不支持的动作: {action}")
        target, value = _t(s.get("target")), _t(s.get("value"))
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


def validate_all(flows):
    if not flows:
        raise ValueError("至少需要一个流程编排")
    for idx, f in enumerate(flows):
        validate_flow(f, idx)


def safe(s: str) -> str:
    """把动态文本安全嵌入生成的 Python 双引号字符串字面量。"""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def locator_for_selenium(target: str) -> tuple[str, str]:
    """把目标定位翻译成 Selenium 的 (By, value)，返回 (生成器代码表达式, 值repr)。

    优先识别 XPath/CSS/text=；纯文本按 XPath contains(text()) 匹配。
    """
    t = target.strip()
    if t.startswith(("//", "./", "(")):
        return "By.XPATH", repr(t)
    if t.startswith("text="):
        txt = t[5:].strip().replace("'", "\\'")
        return "By.XPATH", repr(f"//*[contains(text(), '{txt}')]")
    if "=" in t or t.startswith(("/", ".", "#", "[", ":")) or any(ch in t for ch in ".#>:@[]"):
        return "By.CSS_SELECTOR", repr(t)
    txt = t.replace("'", "\\'")
    return "By.XPATH", repr(f"//*[contains(text(), '{txt}')]")


def locator_for_robot(target: str) -> str:
    """把目标定位翻译成 SeleniumLibrary 认可的定位字符串。"""
    t = target.strip()
    if t.startswith(("//", "./", "(")):
        return "xpath=" + t
    if t.startswith("text="):
        txt = t[5:].strip().replace("'", "\\'")
        return f"xpath=//*[contains(text(), '{txt}')]"
    if "=" in t or t.startswith(("/", ".", "#", "[", ":")) or any(ch in t for ch in ".#>:@[]"):
        return "css=" + t
    txt = t.replace("'", "\\'")
    return f"xpath=//*[contains(text(), '{txt}')]"


def robot_escape(value: str) -> str:
    """Robot Framework 数据段的转义：反斜杠、# 注释、= 赋值符、变量符号。"""
    v = value.replace("\\", "\\\\")
    v = v.replace("${", "$\\{")
    if v.startswith("#"):
        v = "\\" + v
    v = v.replace(" = ", " \\= ").replace("=", "\\=")
    return v
