"""Intelligent test case generator from requirement text.

Default: local rule-based engine (offline, no API key) applying multiple test-design
dimensions. Optional: LLM backend via env vars LLM_API_KEY / LLM_BASE_URL / LLM_MODEL.

Supports:
  - language: 'zh' (default) or 'en' — language of the generated case content
  - template: an output template with {placeholders}; each case carries a rendered
    `formatted` field. Chinese and English placeholder aliases are both accepted.
"""
import os
import re
import json
from typing import List, Dict

from .doc_parser import extract_requirement_points

DIMENSIONS = [
    ("功能正确性", "正向流程"),
    ("边界值", "边界"),
    ("异常输入", "异常"),
    ("数据校验", "校验"),
    ("权限与安全", "安全"),
    ("状态流转", "状态"),
    ("性能与并发", "性能"),
    ("UI与兼容性", "兼容"),
    ("易用性与提示", "体验"),
]

DEFAULT_TEMPLATES = {
    "zh": "【{编号}】{标题}\n维度：{维度} ｜ 优先级：{优先级} ｜ 类型：{类型}\n前置条件：{前置条件}\n步骤：\n{步骤}\n预期结果：{预期结果}",
    "en": "[{no}] {title}\nDimension: {dimension} | Priority: {priority} | Type: {case_type}\nPrecondition: {precondition}\nSteps:\n{steps}\nExpected: {expected}",
}

DIMS_EN = {
    "功能正确性": "Functional Correctness",
    "边界值": "Boundary Value",
    "异常输入": "Invalid Input",
    "数据校验": "Data Validation",
    "权限与安全": "Security & Permission",
    "状态流转": "State Transition",
    "性能与并发": "Performance & Concurrency",
    "UI与兼容性": "UI & Compatibility",
    "易用性与提示": "Usability & Tips",
}
CTYPE_EN = {"api": "API", "ui": "UI", "manual": "Manual"}
TAGS_EN = {
    "正向": "Positive", "冒烟": "Smoke", "异常": "Negative", "校验": "Validation",
    "边界": "Boundary", "安全": "Security", "权限": "Permission", "状态": "State",
    "性能": "Performance", "兼容": "Compatibility", "响应式": "Responsive",
    "体验": "UX", "端到端": "E2E",
}


def _render(template: str, case: dict, lang: str) -> str:
    """Replace {placeholder} tokens (Chinese and English aliases supported)."""
    sep = "、" if lang == "zh" else ", "
    tags = case.get("tags_disp") or case.get("tags") or []
    mapping = {
        "编号": case["no"], "no": case["no"], "No": case["no"], "NO": case["no"],
        "标题": case["title"], "title": case["title"], "Title": case["title"],
        "维度": case.get("dimension_disp", case["dimension"]),
        "dimension": case.get("dimension_disp", case["dimension"]),
        "Dimension": case.get("dimension_disp", case["dimension"]),
        "优先级": case["priority"], "priority": case["priority"], "Priority": case["priority"],
        "类型": case.get("case_type_disp", case["case_type"]),
        "case_type": case.get("case_type_disp", case["case_type"]),
        "CaseType": case.get("case_type_disp", case["case_type"]),
        "前置条件": case["precondition"], "precondition": case["precondition"],
        "Precondition": case["precondition"],
        "步骤": case["steps"], "steps": case["steps"], "Steps": case["steps"],
        "预期结果": case["expected"], "expected": case["expected"],
        "Expected": case["expected"], "预期": case["expected"],
        "标签": sep.join(str(t) for t in tags), "tags": sep.join(str(t) for t in tags),
        "Tags": sep.join(str(t) for t in tags),
        "风险": case.get("risk", ""), "risk": case.get("risk", ""), "Risk": case.get("risk", ""),
    }
    out = template
    for key, val in mapping.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def _finalize(cases: List[dict], lang: str, template: str | None) -> List[dict]:
    """Fill display fields and render each case's formatted output."""
    tpl = (template or "").strip() or DEFAULT_TEMPLATES.get(lang, DEFAULT_TEMPLATES["zh"])
    for c in cases:
        if lang == "en":
            c.setdefault("dimension_disp", DIMS_EN.get(c.get("dimension"), c.get("dimension", "")))
            c.setdefault("case_type_disp", CTYPE_EN.get(c.get("case_type"), c.get("case_type", "")))
            c.setdefault("tags_disp", [TAGS_EN.get(t, t) for t in c.get("tags", [])])
        else:
            c.setdefault("dimension_disp", c.get("dimension", ""))
            c.setdefault("case_type_disp", c.get("case_type", ""))
            c.setdefault("tags_disp", c.get("tags", []))
        c["language"] = lang
        c["template"] = tpl
        c["formatted"] = _render(tpl, c, lang)
    return cases


def generate_cases(requirement_text: str, doc_name: str, options: dict | None = None) -> List[dict]:
    """Generate a comprehensive case set. Returns list of case dicts (not persisted)."""
    options = options or {}
    points = extract_requirement_points(requirement_text)
    if not points:
        points = ["系统核心功能流程"]

    backend = (options.get("backend") or os.getenv("GEN_BACKEND", "local")).lower()
    lang = "en" if str(options.get("language", "zh")).lower() in ("en", "english", "英文") else "zh"
    template = options.get("template")
    selected = options.get("dimensions")

    def finalize(cs):
        return _finalize(cs, lang, template)

    if backend == "llm" and os.getenv("LLM_API_KEY"):
        try:
            return finalize(_generate_llm(requirement_text, doc_name, points, options, lang))
        except Exception:
            pass  # fall back to local
    return finalize(_generate_local(requirement_text, doc_name, points, options, lang, selected))


def _generate_local(requirement_text: str, doc_name: str, points: List[str],
                    options: dict, lang: str, selected: List[str] | None = None) -> List[dict]:
    cases = []
    n = 0

    def add(dim, kind_zh, kind_en, title_zh, title_en, pre_zh, pre_en,
            steps_zh, steps_en, exp_zh, exp_en, priority, case_type="manual",
            tags_zh=None, tags_en=None, risk_zh="", risk_en=""):
        nonlocal n
        if selected and dim not in selected:
            return
        n += 1
        if lang == "en":
            title, pre, steps, expected = title_en, pre_en, steps_en, exp_en
            kind, tags, risk = kind_en, (tags_en or []), risk_en
        else:
            title, pre, steps, expected = title_zh, pre_zh, steps_zh, exp_zh
            kind, tags, risk = kind_zh, (tags_zh or []), risk_zh
        cases.append({
            "no": n,
            "dimension": dim,
            "kind": kind,
            "title": f"{doc_name[:12]}-{title}",
            "case_type": case_type,
            "priority": priority,
            "tags": tags or [dim],
            "precondition": pre,
            "steps": steps,
            "expected": expected,
            "risk": risk,
        })

    use_points = points[:12]
    for idx, pt in enumerate(use_points, 1):
        short = _short(pt)
        add("功能正确性", "正向", "Positive",
            f"功能点{idx}正向流程-{short}", f"Feature {idx} Positive Flow - {short}",
            "系统正常运行，测试数据准备就绪", "System running normally; test data ready",
            f"1. 进入相关功能页面\n2. 按需求「{short}」执行标准操作\n3. 提交并观察结果",
            f'1. Navigate to the relevant feature page\n2. Perform standard operations per requirement "{short}"\n3. Submit and observe results',
            "操作成功，结果与需求描述一致，无报错，数据落库正确",
            "Operation succeeds; result matches the requirement; no errors; data persisted correctly",
            "P0", "api", ["正向", "冒烟"], ["Positive", "Smoke"], f"覆盖需求点：{pt[:80]}", f"Covers requirement: {pt[:80]}")

        add("数据校验", "必填", "Required",
            f"功能点{idx}必填项为空-{short}", f"Feature {idx} Required Field Empty - {short}",
            "进入功能页面", "Navigate to the feature page",
            f"1. 将「{short}」相关必填字段置空\n2. 提交表单",
            f'1. Clear required fields related to "{short}"\n2. Submit the form',
            "提交被拦截，明确提示必填字段，不产生脏数据",
            "Submission blocked; required fields clearly indicated; no dirty data created",
            "P1", "api", ["异常", "校验"], ["Negative", "Validation"])

        add("边界值", "边界", "Boundary",
            f"功能点{idx}边界值-{short}", f"Feature {idx} Boundary Value - {short}",
            "准备边界数据（最小值/最大值/临界值/超长字符）",
            "Prepare boundary data (min / max / threshold / overly long text)",
            f"1. 输入「{short}」字段的最小值并提交\n2. 输入最大值并提交\n3. 输入超长文本（如200字符）并提交",
            f'1. Enter the minimum value for "{short}" and submit\n2. Enter the maximum value and submit\n3. Enter overly long text (e.g. 200 chars) and submit',
            "边界内正常处理；超出范围给出合理提示，不崩溃、不截断异常",
            "In-range values handled normally; out-of-range values get clear hints; no crash or abnormal truncation",
            "P1", "api", ["边界"], ["Boundary"])

        add("异常输入", "异常", "Negative",
            f"功能点{idx}非法输入-{short}", f"Feature {idx} Invalid Input - {short}",
            "进入功能页面", "Navigate to the feature page",
            f"1. 对「{short}」输入特殊字符、SQL片段、HTML标签、超长串\n2. 逐一提交",
            f'1. Input special characters, SQL fragments, HTML tags and long strings into "{short}"\n2. Submit each one',
            "系统校验或转义处理，无脚本执行、无SQL注入、无页面错乱",
            "Input validated or escaped; no script execution, no SQL injection, no broken layout",
            "P1", "api", ["异常", "安全"], ["Negative", "Security"])

        if idx <= 6:
            add("状态流转", "状态", "State",
                f"功能点{idx}状态流转-{short}", f"Feature {idx} State Transition - {short}",
                "对象处于可操作状态", "Object is in an actionable state",
                f"1. 触发「{short}」使状态变更\n2. 重复触发/逆操作\n3. 从不同初始状态触发",
                f'1. Trigger "{short}" to change state\n2. Repeat / reverse the operation\n3. Trigger from different initial states',
                "状态按预期流转，非法流转被拒绝，状态展示同步更新",
                "States transition as expected; illegal transitions rejected; UI state updated in sync",
                "P1", "manual", ["状态"], ["State"])

        if idx <= 4:
            add("权限与安全", "安全", "Security",
                f"功能点{idx}越权访问-{short}", f"Feature {idx} Unauthorized Access - {short}",
                "准备普通用户、未登录、管理员三类账号", "Prepare normal user, anonymous and admin accounts",
                f"1. 未登录访问「{short}」相关接口/页面\n2. 普通用户尝试管理员操作\n3. 篡改请求参数中的用户标识",
                f'1. Access "{short}" related APIs/pages anonymously\n2. Normal user attempts admin operations\n3. Tamper with user ID in request parameters',
                "未登录跳转登录；越权被拒绝（403），无数据泄露",
                "Anonymous users redirected to login; unauthorized access rejected (403); no data leakage",
                "P0", "api", ["安全", "权限"], ["Security", "Permission"])

    add("性能与并发", "性能", "Performance", "关键接口并发压测", "Concurrent Load Test on Key APIs",
        "接口可访问，准备压测工具", "APIs accessible; load test tool ready",
        "1. 对核心接口以 50/100 并发持续请求 5 分钟\n2. 观察响应时间、错误率、资源占用",
        "1. Send sustained requests to core APIs at 50/100 concurrency for 5 minutes\n2. Observe response time, error rate and resource usage",
        "平均响应时间达标（如<2s），错误率<1%，服务不崩溃",
        "Average response time within target (e.g. <2s), error rate <1%, service stable",
        "P1", "api", ["性能"], ["Performance"])
    add("性能与并发", "性能", "Performance", "大数据量查询响应", "Large Dataset Query Response",
        "数据库准备万级数据", "Prepare tens of thousands of records in the database",
        "1. 查询最大分页数据\n2. 执行复杂条件组合查询",
        "1. Query the largest page of data\n2. Run complex combined-condition queries",
        "响应及时，无超时，分页正确", "Responsive, no timeout, pagination correct",
        "P2", "api", ["性能"], ["Performance"])
    add("UI与兼容性", "兼容", "Compatibility", "页面多浏览器兼容", "Cross-browser Compatibility",
        "准备 Chrome/Edge/Firefox 及移动端视口", "Prepare Chrome/Edge/Firefox and mobile viewports",
        "1. 在主流浏览器打开功能页面\n2. 检查布局、样式、交互一致性",
        "1. Open the feature page in major browsers\n2. Check layout, styling and interaction consistency",
        "各浏览器显示正常，无错位/遮挡/按钮失效",
        "Renders correctly in all browsers; no misalignment, overlap or broken buttons",
        "P2", "ui", ["兼容"], ["Compatibility"])
    add("UI与兼容性", "兼容", "Compatibility", "响应式与移动端适配", "Responsive & Mobile Adaptation",
        "准备不同分辨率设备/模拟器", "Prepare devices/emulators with different resolutions",
        "1. 在桌面/平板/手机尺寸访问\n2. 检查布局自适应与滚动",
        "1. Access at desktop/tablet/mobile sizes\n2. Check responsive layout and scrolling",
        "布局自适应，关键操作可完成", "Layout adapts; key operations can be completed",
        "P2", "ui", ["兼容", "响应式"], ["Compatibility", "Responsive"])
    add("易用性与提示", "体验", "UX", "异常场景提示友好性", "Friendly Error Scenario Messages",
        "进入各功能页面", "Navigate to the feature pages",
        "1. 触发网络超时、服务异常、加载失败等场景\n2. 检查提示信息",
        "1. Trigger network timeout, service error and load failure scenarios\n2. Check the messages shown",
        "有清晰、友好的错误提示与引导，不暴露堆栈/技术细节",
        "Clear and friendly error messages and guidance; no stack traces or technical details exposed",
        "P2", "manual", ["体验"], ["UX"])
    add("易用性与提示", "体验", "UX", "操作确认与防重复提交", "Operation Confirmation & Duplicate Prevention",
        "进入提交类功能页面", "Navigate to a submission feature page",
        "1. 快速连续点击提交按钮\n2. 检查是否重复提交",
        "1. Click the submit button rapidly several times\n2. Check for duplicate submissions",
        "按钮防抖/置灰，无重复数据产生", "Button debounced/disabled; no duplicate data created",
        "P2", "manual", ["体验"], ["UX"])
    add("数据校验", "校验", "Validation", "数据精度与格式", "Data Precision & Format",
        "准备各类格式数据", "Prepare data in various formats",
        "1. 输入日期、金额、手机号、邮箱等特殊格式\n2. 检查存储与回显",
        "1. Input special formats: date, amount, phone number, email\n2. Check storage and display",
        "格式校验正确，存储精度无丢失，回显一致",
        "Format validated correctly; no precision loss in storage; display consistent",
        "P1", "api", ["校验"], ["Validation"])
    add("功能正确性", "正向", "Positive", "全流程端到端冒烟", "End-to-end Smoke Test",
        "系统可访问，测试账号就绪", "System accessible; test account ready",
        "1. 从入口到核心业务闭环完整走一遍主流程",
        "1. Walk through the full main flow from entry to core business closure",
        "主流程畅通，各步骤数据衔接正确", "Main flow smooth; data consistent across steps",
        "P0", "manual", ["冒烟", "端到端"], ["Smoke", "E2E"])

    return cases


def _generate_llm(requirement_text: str, doc_name: str, points: List[str],
                  options: dict, lang: str) -> List[dict]:
    """Optional LLM backend. Uses OpenAI-compatible chat completions API."""
    import urllib.request
    api_key = os.getenv("LLM_API_KEY")
    base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    lang_rule = ("所有用例内容（标题、前置条件、步骤、预期结果、标签）必须使用中文。"
                 if lang == "zh" else
                 "All case content (title, precondition, steps, expected, tags) MUST be written in English.")
    dim_note = ("维度请使用中文，如：功能正确性、边界值、异常输入、数据校验、权限与安全、状态流转、性能与并发、UI与兼容性、易用性与提示。"
                if lang == "zh" else
                "Use English dimension names, e.g. Functional Correctness, Boundary Value, Invalid Input, Data Validation, Security & Permission, State Transition, Performance & Concurrency, UI & Compatibility, Usability & Tips.")
    prompt = f"""你是一位资深测试工程师。请根据以下需求文档内容，设计全方位的测试用例。
要求覆盖：功能正向、边界值、异常输入、数据校验、权限安全、状态流转、性能并发、UI兼容、易用性提示。
{lang_rule}
{dim_note}
以 JSON 数组返回，每个用例包含字段：dimension(维度)、title(标题)、priority(P0/P1/P2)、case_type(api/ui/manual)、precondition、steps、expected、tags(数组)。
只返回 JSON，不要其他文字。

需求文档：{doc_name}
内容：
{requirement_text[:12000]}"""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    content = re.sub(r"```json|```", "", content).strip()
    raw = json.loads(content)
    cases = []
    for i, c in enumerate(raw, 1):
        dim = c.get("dimension", "功能正确性" if lang == "zh" else "Functional Correctness")
        steps = c.get("steps", "")
        if isinstance(steps, list):
            steps = "\n".join(f"{j+1}. {s}" for j, s in enumerate(steps))
        cases.append({
            "no": i,
            "dimension": dim,
            "kind": dim,
            "title": f"{doc_name[:12]}-{c.get('title', ('用例'+str(i)) if lang=='zh' else ('Case '+str(i)))}",
            "case_type": c.get("case_type", "manual"),
            "priority": c.get("priority", "P1"),
            "tags": c.get("tags", [dim]),
            "precondition": c.get("precondition", ""),
            "steps": steps,
            "expected": c.get("expected", ""),
            "risk": "LLM生成" if lang == "zh" else "LLM generated",
        })
    return cases


def _short(text: str, limit: int = 22) -> str:
    s = re.sub(r"^[\d\.\、\)\s\-•*]+", "", text).strip()
    s = re.sub(r"[「」【】\[\]（）()：:，,。；;]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit] if len(s) > limit else s
