"""Test execution engine: variable substitution, assertions, HTTP & simulated UI steps."""
import re
import time
from typing import Any

import httpx


VAR_PATTERN = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def render(text: str, variables: dict) -> str:
    """Replace {{var}} placeholders with values from variables."""
    if text is None:
        return ""
    if not isinstance(text, str):
        return text

    def repl(match):
        key = match.group(1)
        value = variables
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return match.group(0)
        if isinstance(value, (dict, list)):
            import json
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return VAR_PATTERN.sub(repl, text)


def extract_from(data: Any, source: str, key: str) -> Any:
    """Extract a value from response by source (json/header/body) and key (dot path or jsonpath-like)."""
    if source == "header":
        if isinstance(data, dict):
            return data.get(key.lower()) or data.get(key)
        return None
    if source == "status":
        return data
    # json / body
    value = data
    for part in key.split("."):
        if part == "length" and isinstance(value, (list, dict, str)):
            return len(value)
        if isinstance(value, dict):
            if part in value:
                value = value[part]
            elif part.isdigit() and int(part) < len(value):
                value = list(value.values())[int(part)]
            else:
                return None
        elif isinstance(value, list):
            m = re.match(r"(\w+)\[(\d+)\]", part)
            if m:
                k, idx = m.group(1), int(m.group(2))
                if k and isinstance(value[0] if value else None, dict):
                    value = [x.get(k) for x in value]
                value = value[idx] if idx < len(value) else None
            elif part.isdigit() and int(part) < len(value):
                value = value[int(part)]
            else:
                return None
        else:
            return None
    return value


def run_assertions(assertions: list, context: dict) -> list:
    """Each assertion: {type, key, op, value}. Returns detailed results."""
    results = []
    for a in assertions or []:
        typ = a.get("type", "status")  # status|header|json|body|contains
        op = a.get("op", "eq")
        expected = a.get("value")
        key = a.get("key", "")
        if typ == "status":
            actual = context.get("status_code")
        elif typ == "header":
            actual = (context.get("headers") or {}).get(key.lower(), (context.get("headers") or {}).get(key))
        elif typ == "body":
            actual = context.get("body_text", "")
        elif typ == "contains":
            actual = context.get("body_text", "")
        else:  # json
            actual = extract_from(context.get("json"), "json", key)

        passed = False
        try:
            if op == "eq":
                passed = str(actual) == str(expected)
            elif op == "ne":
                passed = str(actual) != str(expected)
            elif op == "contains":
                passed = expected in (actual if isinstance(actual, (str, list, dict)) else str(actual))
            elif op == "gt":
                passed = float(actual) > float(expected)
            elif op == "gte":
                passed = float(actual) >= float(expected)
            elif op == "lt":
                passed = float(actual) < float(expected)
            elif op == "lte":
                passed = float(actual) <= float(expected)
            elif op == "exists":
                passed = actual is not None
            elif op == "regex":
                passed = bool(re.search(str(expected), str(actual)))
        except Exception:
            passed = False
        results.append({
            "type": typ, "key": key, "op": op,
            "expected": expected, "actual": actual, "passed": passed,
        })
    return results


def run_extractors(extractors: list, context: dict) -> dict:
    out = {}
    for e in extractors or []:
        name = e.get("name")
        source = e.get("source", "json")
        key = e.get("key", "")
        if not name:
            continue
        if source == "status":
            out[name] = context.get("status_code")
        elif source == "header":
            out[name] = (context.get("headers") or {}).get(key.lower())
        elif source == "body":
            out[name] = context.get("body_text", "")
        else:
            out[name] = extract_from(context.get("json"), "json", key)
    return out


def execute_api(case: dict, env: dict | None, base_variables: dict | None = None) -> dict:
    """Execute one API case. Returns a result dict (no DB writes)."""
    result = {
        "status": "passed", "error_msg": "", "duration_ms": 0,
        "request_info": {}, "response_info": {}, "assertions_result": [], "logs": "",
    }
    variables = dict(base_variables or {})
    if env:
        variables.update(env.get("variables") or {})
    base_url = (env or {}).get("base_url", "")

    url = render(case.get("url", ""), variables)
    if base_url and url.startswith("/"):
        url = base_url.rstrip("/") + url
    elif base_url and not url.startswith("http"):
        url = base_url.rstrip("/") + "/" + url

    method = (case.get("method") or "GET").upper()
    headers = {}
    for k, v in (case.get("headers") or {}).items():
        if str(k).lower() in ("content-type", "content-length") and case.get("body_mode") in ("form-data", "x-www-form-urlencoded"):
            continue  # let httpx set the correct header for form bodies
        headers[render(str(k), variables)] = render(str(v), variables)
    body = render(case.get("body", ""), variables)

    result["request_info"] = {
        "method": method, "url": url, "headers": headers, "body": body,
    }

    try:
        start = time.time()
        with httpx.Client(timeout=15, verify=False, follow_redirects=True) as client:
            kwargs = {"headers": headers}
            mode = case.get("body_mode") or "raw"
            if mode == "form-data":
                fields = {}
                for f in case.get("form_data") or []:
                    if not f.get("enabled", True) or not f.get("key"):
                        continue
                    fields[render(str(f["key"]), variables)] = (
                        None, render(str(f.get("value", "")), variables)
                    )
                if fields:
                    kwargs["files"] = fields
            elif mode == "x-www-form-urlencoded":
                fields = {}
                for f in case.get("form_data") or []:
                    if not f.get("enabled", True) or not f.get("key"):
                        continue
                    fields[render(str(f["key"]), variables)] = render(str(f.get("value", "")), variables)
                if fields:
                    kwargs["data"] = fields
            elif body and method in ("POST", "PUT", "PATCH", "DELETE"):
                # try JSON first, fall back to raw
                import json
                try:
                    kwargs["json"] = json.loads(body)
                except Exception:
                    kwargs["content"] = body
            resp = client.request(method, url, **kwargs)
        duration = int((time.time() - start) * 1000)
        result["duration_ms"] = duration

        try:
            json_body = resp.json()
        except Exception:
            json_body = None

        context = {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "json": json_body,
            "body_text": resp.text,
        }
        result["response_info"] = {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": json_body if json_body is not None else resp.text[:5000],
            "size": len(resp.content),
            "cookies": dict(resp.cookies),
        }
        results = run_assertions(case.get("assertions") or [], context)
        result["assertions_result"] = results
        extracted = run_extractors(case.get("extractors") or [], context)
        result["logs"] = f"Status: {resp.status_code} | Duration: {duration}ms"

        if any(not r["passed"] for r in results):
            result["status"] = "failed"
            failed = [r for r in results if not r["passed"]]
            result["error_msg"] = "断言失败: " + "; ".join(
                f"{r['type']}.{r['key']} 期望={r['expected']} 实际={r['actual']}" for r in failed
            )
        result["_extracted"] = extracted
    except Exception as e:
        result["status"] = "error"
        result["error_msg"] = f"{type(e).__name__}: {e}"
        result["logs"] = str(e)
    return result


def execute_ui_steps(case: dict, variables: dict | None = None) -> dict:
    """Execute UI automation case.

    Real mode: when ui_config.use_real_browser=true and Playwright is installed,
    the runner service (separate script) performs the steps. Here we support a
    simulated engine that validates step structure and produces deterministic
    results for demonstration, plus a hook for real Playwright results pushed
    back via /api/ui/callback.
    """
    result = {
        "status": "passed", "error_msg": "", "duration_ms": 0,
        "request_info": {}, "response_info": {}, "assertions_result": [], "logs": "",
    }
    variables = dict(variables or {})
    steps_raw = case.get("steps", "")
    steps = []
    if isinstance(steps_raw, str) and steps_raw.strip():
        import json
        try:
            parsed = json.loads(steps_raw)
            if isinstance(parsed, list):
                steps = parsed
        except Exception:
            steps = [{"action": "raw", "value": steps_raw}]
    elif isinstance(steps_raw, list):
        steps = steps_raw

    if not steps:
        steps = case.get("ui_config", {}).get("steps", [])

    logs = []
    start = time.time()
    screenshots = []
    for i, step in enumerate(steps, 1):
        action = step.get("action", "")
        target = render(str(step.get("target", "")), variables)
        value = render(str(step.get("value", "")), variables)
        if step.get("screenshot"):
            screenshots.append({"step": i, "target": target})
        logs.append(f"[{i}] {action} target={target} value={value}")
        # simulated locator healing: mark if target looks like a css selector
        if action in ("click", "fill", "assert_visible") and not target:
            result["status"] = "failed"
            result["error_msg"] = f"步骤 {i}: {action} 缺少定位目标"
            break
    result["duration_ms"] = int((time.time() - start) * 1000)
    result["logs"] = "\n".join(logs)
    result["request_info"] = {"steps": steps, "screenshots": screenshots}
    result["response_info"] = {"note": "UI 步骤模拟执行；真实浏览器结果可通过回调写入"}
    return result
