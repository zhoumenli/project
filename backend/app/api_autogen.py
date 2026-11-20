"""Generate a runnable pytest+requests automation project from API test cases,
following the user's template structure:

    config.py / pytest.ini / main.py / API/demo1.py / Tools/*
    caseData/data.yaml  (数据驱动: title/kw/method/path/headers/json/asserts/extract)
    testcase/<模块>/test_xxx.py (parametrize + allure)

Framework files are copied verbatim from the template dir (env API_TEMPLATE_DIR,
default C:\\project\\initial_api_framework); only the case layer is generated.
"""
import io
import json
import os
import re
import zipfile
from typing import List, Dict, Tuple

TEMPLATE_DIR = os.getenv("API_TEMPLATE_DIR", r"C:\project\initial_api_framework")

# 模板里原样保留的框架文件（只取框架，不带业务用例）
FRAMEWORK_FILES = [
    "pytest.ini",
    "main.py",
    os.path.join("API", "demo1.py"),
    os.path.join("Tools", "logger.py"),
    os.path.join("Tools", "read_data.py"),
]

def _safe_name(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch not in '\\/:*?"<>| ').strip() or "module"


CONTEST_PY = '''import pytest
from API.demo1 import BaseAPI


@pytest.fixture(scope="session")
def api():
    """BaseAPI 实例：统一请求入口 api.my_request(method, url, **kwargs)"""
    return BaseAPI()


@pytest.fixture(scope="session")
def context():
    """跨用例共享变量上下文：extract 提取的变量写入这里，
    供后续用例的 {{var}} 占位符渲染（如登录提取 token）"""
    return {}
'''

RENDER_PY = '''"""{{var}} 占位符渲染工具"""
import re

from Tools.logger import logger


def render(text, context):
    """把字符串里的 {{var}} 替换为 context 中的值；缺失时保留原样并告警"""
    if not isinstance(text, str):
        return text

    def _rep(m):
        key = m.group(1).strip()
        if key in context:
            return str(context[key])
        logger.warning("变量 {} 未在上下文中找到，保留原样".format(key))
        return m.group(0)

    return re.sub(r"\\{\\{\\s*(\\w+)\\s*\\}\\}", _rep, text)


def render_obj(obj, context):
    """递归渲染 dict / list / str 结构中的 {{var}}"""
    if isinstance(obj, str):
        return render(obj, context)
    if isinstance(obj, dict):
        return {k: render_obj(v, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render_obj(v, context) for v in obj]
    return obj
'''

ASSERT_UTIL_PY = '''"""通用断言 / 变量提取执行器（规则来自 caseData/data.yaml）"""
from Tools.logger import logger


def _dig(obj, key):
    """按 'data.token' / 'data.0.list' 路径取值"""
    cur = obj
    for part in key.split("."):
        if isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            raise KeyError(key)
    return cur


def _num_eq(a, b):
    """数字宽松相等：'0' == 0 视为相等（YAML 值均为字符串）"""
    if a == b:
        return True
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return False


def _cmp(actual, op, expected):
    op = (op or "eq").lower()
    if op == "eq":
        assert _num_eq(actual, expected), "断言失败: 期望 {}，实际 {}".format(expected, actual)
    elif op == "ne":
        assert not _num_eq(actual, expected), "断言失败: 不应等于 {}（实际恰好相等）".format(expected)
    elif op == "contains":
        assert str(expected) in str(actual), "断言失败: 响应值不含 {} (实际 {})".format(expected, actual)
    elif op == "gt":
        assert float(actual) > float(expected), "断言失败: {} 应大于 {}".format(actual, expected)
    elif op == "gte":
        assert float(actual) >= float(expected), "断言失败: {} 应大于等于 {}".format(actual, expected)
    elif op == "lt":
        assert float(actual) < float(expected), "断言失败: {} 应小于 {}".format(actual, expected)
    elif op == "lte":
        assert float(actual) <= float(expected), "断言失败: {} 应小于等于 {}".format(actual, expected)
    elif op == "exists":
        assert actual is not None, "断言失败: 字段不存在"
    elif op == "regex":
        assert re_search(str(expected), str(actual)), "断言失败: {} 不匹配正则 {}".format(actual, expected)
    else:
        assert False, "未知的断言操作符: {}".format(op)


def re_search(pattern, text):
    import re as _re
    return _re.search(pattern, text)


def check(resp, a):
    """执行一条断言规则 {type, op, key, value}，失败抛 AssertionError"""
    t = (a.get("type") or "status").lower()
    op = a.get("op") or "eq"
    key = a.get("key") or ""
    val = a.get("value")
    try:
        if t == "status":
            _cmp(resp.status_code, op, int(val) if str(val).lstrip("-").isdigit() else val)
        elif t == "json":
            _cmp(_dig(resp.json(), key), op, val)
        elif t == "header":
            _cmp(resp.headers.get(key), op, val)
        elif t == "body":
            if op == "contains":
                assert str(val) in resp.text, "断言失败: 响应体不含 {}".format(val)
            else:
                assert resp.text.strip() != "", "断言失败: 响应体不应为空"
        else:
            assert False, "未知断言类型: {}".format(t)
    except (KeyError, ValueError) as e:
        raise AssertionError("断言取值失败: type={} key={} ({})".format(t, key, e))


def apply_extract(e, resp, context):
    """执行一条变量提取规则 {name, source, key}，写入 context"""
    name = e.get("name") or ""
    src = (e.get("source") or "json").lower()
    key = e.get("key") or ""
    if not name:
        return
    try:
        if src == "json":
            context[name] = _dig(resp.json(), key)
        elif src == "header":
            context[name] = resp.headers.get(key)
        else:
            context[name] = resp.text
        logger.info("提取变量 {}={}".format(name, context[name]))
    except Exception:
        logger.warning("提取变量 {} 失败（响应不含 {}）".format(name, key))
'''


def _test_module_py(module_disp: str, module_id: str, project_name: str) -> str:
    cls = "Test" + re.sub(r"\W", "", str(module_id))
    return f'''import os

import allure
import pytest

from Tools.read_data import read
from Tools.render import render, render_obj
from Tools.assert_util import check, apply_extract
from Tools.logger import logger
from config import BASE_URL
from main import obj_path

data_file = os.path.join(obj_path, "caseData/data.yaml")
datas = read(data_file, kw={module_disp!r})


@allure.epic({project_name!r})
@allure.feature({module_disp!r})
class {cls}:

    @allure.story({module_disp!r})
    @pytest.mark.parametrize("data", datas)
    @allure.title("{{data[title]}}")
    def test_case(self, api, context, data):
        logger.info("接口用例开始执行：{{}}......".format(data["title"]))
        path = render(data["path"], context)
        url = path if path.startswith("http") else BASE_URL + path
        kwargs = {{}}
        headers = render_obj(data.get("headers") or {{}}, context)
        if headers:
            kwargs["headers"] = headers
        if data.get("method", "GET").upper() != "GET" and data.get("json") is not None:
            kwargs["json"] = render_obj(data["json"], context)
        elif data.get("body"):
            kwargs["data"] = str(render(data["body"], context)).encode("utf-8")
        api.my_request(method=data["method"], url=url, **kwargs)
        resp = api.response
        # 通用断言执行（规则来自 caseData/data.yaml）
        for a in data.get("asserts") or []:
            check(resp, a)
        # 通用变量提取（写入 context，供后续用例 {{{{var}}}} 渲染）
        for e in data.get("extract") or []:
            apply_extract(e, resp, context)
'''


def _yaml_block(case: dict) -> List[str]:
    """One case -> yaml entry (title/kw/method/path/headers/json/body/asserts/extract)."""
    q = lambda s: json.dumps(str(s if s is not None else ""), ensure_ascii=False)
    lines = ["- title: " + q(case.get("title", "")),
             "  kw: " + q(case.get("kw", "")),
             f"  method: {case.get('method', 'GET')}",
             "  path: " + q(case.get("path", ""))]
    headers = case.get("headers") or {}
    if headers:
        lines.append("  headers:")
        for k, v in headers.items():
            lines.append(f"    {q(k)}: {q(v)}")
    if case.get("json") is not None:
        lines.append("  json:")
        for k, v in (case["json"] or {}).items():
            lines.append(f"    {q(k)}: {json.dumps(v, ensure_ascii=False)}")
    elif case.get("body"):
        lines.append("  body: " + q(case["body"]))
    if case.get("asserts"):
        lines.append("  asserts:")
        for a in case["asserts"]:
            lines.append(f"    - {{type: {q(a.get('type') or 'status')}, op: {q(a.get('op') or 'eq')}, "
                         f"key: {q(a.get('key') or '')}, value: {json.dumps(a.get('value'), ensure_ascii=False)}}}")
    if case.get("extract"):
        lines.append("  extract:")
        for e in case["extract"]:
            lines.append(f"    - {{name: {q(e.get('name') or '')}, source: {q(e.get('source') or 'json')}, "
                         f"key: {q(e.get('key') or '')}}}")
    return lines


def generate_project(cases: List[dict], base_url: str, project_name: str) -> Tuple[bytes, str]:
    """Build the zip. cases: case-center dicts (case_type=api only).
    Returns (zip_bytes, top_dir_name)."""
    base_url = (base_url or "").rstrip("/") or "http://127.0.0.1"
    project_name = project_name or "接口自动化"
    top = _safe_name(project_name) + "_api_autotest"

    # 按目录分组：kw = 目录名（数据驱动分组标识）
    groups: Dict[str, List[dict]] = {}
    for c in cases:
        kw = c.get("kw") or "未分组"
        groups.setdefault(kw, []).append(c)

    buf = io.BytesIO()
    zf = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)

    def write(name: str, content: str):
        zf.writestr(top + "/" + name, content)

    # 1. 框架文件原样拷贝（只取框架，不带业务用例）
    for name in FRAMEWORK_FILES:
        with open(os.path.join(TEMPLATE_DIR, name), "r", encoding="utf-8") as f:
            write(name, f.read())

    # 2. config.py：重新生成（BASE_URL 来自平台环境，不保留模板业务 URL/凭证）
    write("config.py", f"# Auto-generated by 测试提效平台\nBASE_URL = {base_url!r}\n")

    # 3. 新增的公共工具 + requirements
    write(os.path.join("Tools", "render.py"), RENDER_PY)
    write(os.path.join("Tools", "assert_util.py"), ASSERT_UTIL_PY)
    write("requirements.txt", "pytest\nrequests\nPyYAML\nallure-pytest\n")

    # 4. testcase/conftest.py（共用 fixture）
    write(os.path.join("testcase", "conftest.py"), CONTEST_PY)

    # 5. caseData/data.yaml：全部用例的数据驱动块
    yaml_lines = []
    for kw, group_cases in groups.items():
        for c in group_cases:
            c = dict(c)
            c["kw"] = kw
            yaml_lines.extend(_yaml_block(c))
            yaml_lines.append("")
    write(os.path.join("caseData", "data.yaml"), "\n".join(yaml_lines) or "# 暂无用例\n")

    # 6. testcase/<module>/test_<module>.py（每目录一个模块）
    used_names = set()
    for kw, group_cases in groups.items():
        mid = f"m{abs(hash(kw)) % 100000}"
        fname = f"module_{mid}"
        while fname in used_names:
            mid += "_x"
            fname = f"module_{mid}"
        used_names.add(fname)
        write(os.path.join("testcase", fname, f"test_{fname}.py"),
              _test_module_py(kw, fname, project_name))

    zf.close()
    return buf.getvalue(), top
