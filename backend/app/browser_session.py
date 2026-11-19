"""Browser login sessions - save and reuse Playwright storage_state.

For sites behind authentication (username/password, SMS code, QR scan, SSO),
credentials should never be embedded in the URL. Instead the user logs in once
in a visible browser; cookies + localStorage are saved as a storage_state file
and reused by later locator extractions.
"""
import json
import os
import threading
import time
import uuid

from playwright.sync_api import sync_playwright

from .locator_extractor import _launch_browser

BASE_DIR = os.path.join(os.path.dirname(__file__), "storage_states")
os.makedirs(BASE_DIR, exist_ok=True)

_SESSIONS: dict[str, dict] = {}
_LOCK = threading.Lock()
_LOGIN_TIMEOUT_SEC = 300  # 5 minutes to finish an interactive login


def _safe_name(name: str) -> str:
    cleaned = "".join(c for c in (name or "") if c.isalnum() or c in "-_").strip()
    return cleaned[:40] or "default"


def state_path(name: str) -> str:
    return os.path.join(BASE_DIR, _safe_name(name) + ".json")


def meta_path(name: str) -> str:
    return os.path.join(BASE_DIR, _safe_name(name) + ".meta.json")


def list_states() -> list[dict]:
    out = []
    for fn in os.listdir(BASE_DIR):
        if not fn.endswith(".meta.json"):
            continue
        try:
            with open(os.path.join(BASE_DIR, fn), encoding="utf-8") as f:
                out.append(json.load(f))
        except Exception:
            pass
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return out


def delete_state(name: str) -> bool:
    removed = False
    for p in (state_path(name), meta_path(name)):
        if os.path.exists(p):
            os.remove(p)
            removed = True
    return removed


def start_login(name: str, url: str) -> dict:
    """Open a visible browser at `url` and wait for the user to log in."""
    name = (name or "").strip()
    if not name:
        raise ValueError("登录态名称不能为空")
    sid = uuid.uuid4().hex[:12]
    sess = {
        "id": sid,
        "name": name,
        "url": url,
        "status": "starting",
        "event": threading.Event(),
        "saved": threading.Event(),
        "confirmed": False,
    }
    with _LOCK:
        for old_id, old in list(_SESSIONS.items()):
            if old["name"] == name:
                _SESSIONS.pop(old_id, None)
        _SESSIONS[sid] = sess

    threading.Thread(target=_worker, args=(sess,), daemon=True).start()
    return {
        "session_id": sid,
        "name": name,
        "url": url,
        "message": "浏览器已打开，请在窗口中完成登录，然后回到平台点「保存登录态」",
    }


def _worker(sess: dict) -> None:
    try:
        with sync_playwright() as p:
            browser = _launch_browser(p, headless=False)
            try:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                page = context.new_page()
                page.goto(sess["url"], wait_until="domcontentloaded", timeout=30000)
                sess["status"] = "waiting"

                finished = sess["event"].wait(timeout=_LOGIN_TIMEOUT_SEC)
                if finished and sess["confirmed"]:
                    sp = state_path(sess["name"])
                    context.storage_state(path=sp)
                    with open(sp, encoding="utf-8") as f:
                        state = json.load(f)
                    meta = {
                        "name": sess["name"],
                        "url": sess["url"],
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "cookie_count": len(state.get("cookies", [])),
                        "origin_count": len(state.get("origins", [])),
                    }
                    with open(meta_path(sess["name"]), "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    sess["status"] = "saved"
                else:
                    sess["status"] = "timeout"
            finally:
                browser.close()
    except Exception as e:
        sess["status"] = "error"
        sess["error"] = str(e).split("\n")[0][:200]
    finally:
        sess["saved"].set()


def complete_login(session_id: str, timeout: float = 15) -> dict:
    with _LOCK:
        sess = _SESSIONS.get(session_id)
    if not sess:
        raise ValueError("会话不存在或已过期，请重新打开浏览器登录")
    if sess["status"] == "saved":
        return {"ok": True, "name": sess["name"], "message": "登录态已保存"}
    sess["confirmed"] = True
    sess["event"].set()
    if not sess["saved"].wait(timeout=timeout):
        raise TimeoutError("保存登录态超时，请确认浏览器窗口仍然打开")
    if sess["status"] != "saved":
        raise RuntimeError(f"保存失败：{sess.get('error') or sess['status']}")
    return {"ok": True, "name": sess["name"], "message": "登录态已保存"}


def session_status(session_id: str) -> dict:
    with _LOCK:
        sess = _SESSIONS.get(session_id)
    if not sess:
        raise ValueError("会话不存在或已过期")
    return {"session_id": session_id, "status": sess["status"], "name": sess["name"]}
