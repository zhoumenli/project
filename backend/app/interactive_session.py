"""Interactive browser session.

Opens a VISIBLE browser the user can operate manually (login, navigate, scroll).
The browser lives in a dedicated background thread; the user then submits a
keyword and we run the locator engine against whatever page they are currently on.

Design: a command queue drives the Playwright thread (sync_api is not thread-safe,
so all page operations MUST happen inside the worker thread).
"""
import os
import uuid
import queue
import threading
import traceback

from playwright.sync_api import sync_playwright

from .locator_extractor import _launch_browser, _split_basic_auth, _locate_on_page

_SESSIONS: dict[str, dict] = {}
_LOCK = threading.Lock()
IDLE_TIMEOUT_SEC = 1800  # 30 minutes


def _new_sid() -> str:
    return uuid.uuid4().hex[:12]


def _worker(sess: dict) -> None:
    """Owns the Playwright browser. Loops on commands until 'close' or idle timeout."""
    try:
        with sync_playwright() as p:
            headless = os.getenv("INTERACTIVE_HEADLESS", "0") == "1"
            browser = _launch_browser(p, headless=headless)
            try:
                ctx_opts = {"viewport": {"width": 1440, "height": 900}}
                if sess.get("credentials"):
                    ctx_opts["http_credentials"] = sess["credentials"]
                context = browser.new_context(**ctx_opts)
                page = context.new_page()
                page.set_default_timeout(20000)
                page.goto(sess["clean_url"], wait_until="domcontentloaded", timeout=30000)
                sess["status"] = "ready"
                sess["current_url"] = page.url

                while True:
                    try:
                        cmd = sess["cmd_q"].get(timeout=IDLE_TIMEOUT_SEC)
                    except queue.Empty:
                        sess["status"] = "expired"
                        break
                    if not cmd:
                        continue
                    action = cmd.get("action")
                    reply_q = cmd.get("reply")

                    if action == "locate":
                        try:
                            sess["current_url"] = page.url
                            result = _locate_on_page(
                                page, page.url,
                                cmd["keyword"], cmd.get("exact", False),
                            )
                            sess["status"] = "ready"
                            reply_q.put({"ok": True, "data": result})
                        except Exception as e:
                            reply_q.put({"ok": False, "error": f"定位失败: {e}"})

                    elif action == "state":
                        try:
                            reply_q.put({"ok": True, "data": {
                                "url": page.url, "title": page.title(),
                            }})
                        except Exception as e:
                            reply_q.put({"ok": False, "error": str(e)})

                    elif action == "close":
                        reply_q.put({"ok": True})
                        break
            finally:
                browser.close()
    except Exception as e:
        sess["status"] = "error"
        sess["error"] = str(e)[:300]
        traceback.print_exc()
    finally:
        sess["status"] = "closed" if sess["status"] != "expired" else "expired"


def start_session(url: str) -> dict:
    """Launch a visible browser at `url`. Returns session id."""
    clean_url, credentials = _split_basic_auth(url)
    sid = _new_sid()
    sess = {
        "id": sid,
        "url": url,
        "clean_url": clean_url,
        "credentials": credentials,
        "status": "starting",
        "current_url": clean_url,
        "cmd_q": queue.Queue(),
        "error": "",
    }
    with _LOCK:
        _SESSIONS[sid] = sess
    t = threading.Thread(target=_worker, args=(sess,), daemon=True)
    t.start()
    return {"session_id": sid, "status": "starting", "message": "浏览器正在打开，请稍候"}


def _send(sid: str, cmd: dict, timeout: float = 60) -> dict:
    with _LOCK:
        sess = _SESSIONS.get(sid)
    if not sess:
        raise ValueError("浏览器会话不存在或已关闭")
    reply_q = queue.Queue()
    cmd["reply"] = reply_q
    sess["cmd_q"].put(cmd)
    try:
        return reply_q.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError("浏览器响应超时，请确认窗口仍然打开")


def locate(sid: str, keyword: str, exact: bool = False) -> dict:
    return _send(sid, {"action": "locate", "keyword": keyword, "exact": exact}, timeout=60)


def get_state(sid: str) -> dict:
    return _send(sid, {"action": "state"}, timeout=15)


def close_session(sid: str) -> dict:
    with _LOCK:
        sess = _SESSIONS.get(sid)
    if not sess:
        return {"ok": True}
    try:
        reply = _send(sid, {"action": "close"}, timeout=10)
    except Exception:
        reply = {"ok": True}
    with _LOCK:
        _SESSIONS.pop(sid, None)
    return reply


def session_status(sid: str) -> dict:
    with _LOCK:
        sess = _SESSIONS.get(sid)
    if not sess:
        raise ValueError("浏览器会话不存在或已关闭")
    return {"session_id": sid, "status": sess["status"], "url": sess.get("current_url", "")}
