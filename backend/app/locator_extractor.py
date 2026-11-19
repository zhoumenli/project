"""Element locator extractor.

Opens a real browser (Playwright + system Chrome/Edge), matches page elements by
keyword, then generates locators with a strict priority chain:

  1. Role (semantic) locator  — getByRole / getByLabel / getByPlaceholder / getByText
  2. CSS locator              — #id > [data-testid] > [attr] > .class > structural path
  3. XPath locator            — //[@id] > text > attribute > absolute path

Every candidate is verified against the live page for uniqueness; the first unique
locator in the chain is marked as recommended.
"""
import os
import re
import time
import random
import string
import threading
from urllib.parse import urlsplit, urlunsplit, unquote

from playwright.sync_api import sync_playwright

# one extraction at a time (each opens a real browser)
_LOCK = threading.Lock()

SHOTS_BASE = os.path.join(os.path.dirname(__file__), "shots")
LOCATOR_SHOT_DIR = os.path.join(SHOTS_BASE, "locator")
os.makedirs(LOCATOR_SHOT_DIR, exist_ok=True)

_BROWSER_CANDIDATES = [
    os.getenv("LOCATOR_BROWSER"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

IDENT_RE = re.compile(r"^[A-Za-z_][-\w]*$")

KNOWN_TAGS = {
    "a", "button", "input", "form", "select", "textarea", "label", "img", "table",
    "nav", "header", "footer", "main", "aside", "section", "article", "div", "span",
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "dialog", "video",
    "audio", "canvas", "iframe", "summary", "details", "meter", "progress", "search",
}

# ---------------------------------------------------------------------------
# In-browser matching script
# ---------------------------------------------------------------------------
MATCH_JS = r"""
(payload) => {
  const keyword = payload.keyword;
  const exact = payload.exact;
  const tagMode = payload.tagMode;
  const skip = new Set(['script','style','noscript','meta','link','head','title','html','svg','path','br','hr','base','template','option']);

  const IMPLICIT = { a:'link', button:'button', nav:'navigation', main:'main', aside:'complementary',
    header:'banner', footer:'contentinfo', form:'form', img:'img', ul:'list', ol:'list', li:'listitem',
    table:'table', textarea:'textbox', select:'combobox', h1:'heading',h2:'heading',h3:'heading',
    h4:'heading',h5:'heading',h6:'heading', article:'article', section:'region', dialog:'dialog',
    search:'search', meter:'meter', progress:'progressbar' };
  const INPUT_ROLES = { text:'textbox', email:'textbox', password:'textbox', tel:'textbox', url:'textbox',
    search:'searchbox', number:'spinbutton', checkbox:'checkbox', radio:'radio', submit:'button',
    button:'button', reset:'button', date:'textbox', 'datetime-local':'textbox', month:'textbox',
    week:'textbox', time:'textbox', range:'slider', color:'colorwell', file:'button' };

  const directText = (el) => Array.from(el.childNodes)
    .filter(n => n.nodeType === 3).map(n => n.textContent.trim()).filter(Boolean).join(' ');

  function roleOf(el) {
    const r = el.getAttribute('role');
    if (r && r.trim()) return r.trim().split(/\s+/)[0];
    const t = el.tagName.toLowerCase();
    if (t === 'input') return INPUT_ROLES[(el.getAttribute('type') || 'text').toLowerCase()] || 'textbox';
    if (t === 'hgroup') return 'group';
    return IMPLICIT[t] || null;
  }

  function accNameOf(el) {
    const al = el.getAttribute('aria-label');
    if (al && al.trim()) return { name: al.trim(), source: 'aria-label' };
    const lb = el.getAttribute('aria-labelledby');
    if (lb) {
      const parts = lb.split(/\s+/).map(id => {
        const e = document.getElementById(id);
        return e ? (e.innerText || '').trim() : '';
      }).filter(Boolean);
      if (parts.length) return { name: parts.join(' ').slice(0, 120), source: 'aria-labelledby' };
    }
    const t = el.tagName;
    if (t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') {
      if (el.id) {
        const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
        if (l && l.textContent.trim()) return { name: l.textContent.trim(), source: 'label' };
      }
      const wrap = el.closest('label');
      if (wrap) {
        const wt = (wrap.innerText || '').trim();
        if (wt) return { name: wt.slice(0, 120), source: 'label' };
      }
      const ph = el.getAttribute('placeholder');
      if (ph && ph.trim()) return { name: ph.trim(), source: 'placeholder' };
      const ti = el.getAttribute('title');
      if (ti && ti.trim()) return { name: ti.trim(), source: 'title' };
      if (typeof el.value === 'string' && el.value.trim()) return { name: el.value.trim(), source: 'value' };
      return { name: null, source: null };
    }
    const own = directText(el);
    if (own) return { name: own.slice(0, 120), source: 'text' };
    const ti2 = el.getAttribute('title');
    if (ti2 && ti2.trim()) return { name: ti2.trim(), source: 'title' };
    if (t === 'IMG') {
      const alt = el.getAttribute('alt');
      if (alt && alt.trim()) return { name: alt.trim(), source: 'alt' };
    }
    return { name: null, source: null };
  }

  const test = (v) => {
    if (!v) return false;
    return exact ? v.trim() === keyword : v.includes(keyword);
  };

  const out = [];
  const all = document.querySelectorAll('*');
  let matchIdx = 0;
  for (const el of all) {
    const tag = el.tagName.toLowerCase();
    if (skip.has(tag)) continue;
    const st = getComputedStyle(el);
    if (!st || st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;

    const dt = directText(el);
    const inner = (el.innerText || '').trim();
    const placeholder = el.getAttribute('placeholder') || '';
    const ariaLabel = el.getAttribute('aria-label') || '';
    const title = el.getAttribute('title') || '';
    const name = el.getAttribute('name') || '';
    const value = (typeof el.value === 'string' ? el.value : '') || '';
    const alt = el.getAttribute('alt') || '';
    const testid = el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('data-cy') || '';
    const id = el.id || '';
    const an = accNameOf(el);

    let score = 0, matchedOn = null;
    if (tagMode) {
      if (tag !== keyword) continue;
      score = 50; matchedOn = 'tag';
    } else {
      if (test(dt)) { score = exact ? 100 : 90; matchedOn = 'text'; }
      else if (test(ariaLabel)) { score = 85; matchedOn = 'aria-label'; }
      else if (test(placeholder)) { score = 80; matchedOn = 'placeholder'; }
      else if (test(title)) { score = 75; matchedOn = 'title'; }
      else if (test(value)) { score = 70; matchedOn = 'value'; }
      else if (test(alt)) { score = 68; matchedOn = 'alt'; }
      else if (an.name && test(an.name)) { score = 65; matchedOn = 'accessible-name'; }
      else if (test(name)) { score = 60; matchedOn = 'name'; }
      else if (test(testid)) { score = 58; matchedOn = 'data-testid'; }
      else if (test(id)) { score = 55; matchedOn = 'id'; }
      else if (!el.querySelector('*') && test(inner)) { score = 40; matchedOn = 'inner'; }
      else continue;
    }

    // structural path: element -> ... -> html
    const path = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && path.length < 30) {
      const ct = cur.tagName.toLowerCase();
      let nth = 1, sib = cur;
      while ((sib = sib.previousElementSibling)) { if (sib.tagName === cur.tagName) nth++; }
      path.push({
        tag: ct,
        id: cur.id || null,
        classes: (cur.getAttribute('class') || '').split(/\s+/).filter(Boolean),
        nthOfType: nth,
      });
      cur = cur.parentElement;
    }

    out.push({
      index: matchIdx,
      tag, score, matchedOn,
      directText: dt.slice(0, 150),
      innerText: inner.slice(0, 200),
      role: roleOf(el),
      accessibleName: an.name,
      nameSource: an.source,
      attrs: { id, name, placeholder, ariaLabel, title, value, alt, testid,
               type: el.getAttribute('type') || '', href: el.getAttribute('href') || '',
               className: el.getAttribute('class') || '' },
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      path,
      outerHTML: el.outerHTML.slice(0, 400),
    });
    el.setAttribute('data-__dsh-match', String(matchIdx));
    matchIdx++;
    if (out.length >= 20) break;
  }
  out.sort((a, b) => b.score - a.score || (a.rect.w * a.rect.h) - (b.rect.w * b.rect.h));
  return out;
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _css_escape_ident(v: str) -> str | None:
    """Return a CSS-usable token for an id/class, or None if it needs quoting."""
    if IDENT_RE.match(v or ""):
        return v
    return None


def _q(v: str) -> str:
    return v.replace('"', '\\"')


def _split_basic_auth(url: str) -> tuple[str, dict | None]:
    """Extract HTTP Basic credentials from a URL like http://user:pass@host/path.

    Chromium does not reliably send credentials embedded in the URL, so we strip
    the userinfo and pass them via Playwright's http_credentials instead.
    """
    try:
        parts = urlsplit(url)
    except Exception:
        return url, None
    if not parts.username and not parts.password:
        return url, None
    user = unquote(parts.username or "")
    pwd = unquote(parts.password or "")
    # rebuild netloc without userinfo
    host = parts.hostname or ""
    if ":" in host:  # IPv6 literal needs brackets
        host = f"[{host}]"
    if parts.port:
        host = f"{host}:{parts.port}"
    clean = urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
    return clean, {"username": user, "password": pwd}


def _launch_browser(p, headless: bool = True):
    for path in _BROWSER_CANDIDATES:
        if path and os.path.exists(path):
            return p.chromium.launch(executable_path=path, headless=headless)
    return p.chromium.launch(headless=headless)  # playwright bundled chromium


def _css_count(page, sel: str) -> int:
    try:
        return page.evaluate("s => document.querySelectorAll(s).length", sel)
    except Exception:
        return -1


def _xpath_count(page, xp: str) -> int:
    try:
        return page.evaluate(
            "x => document.evaluate(x, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null).snapshotLength",
            xp,
        )
    except Exception:
        return -1


def _structural_css(path: list) -> str:
    """Build a '>'-joined structural selector, anchored at nearest id (or html)."""
    start = None
    for i, seg in enumerate(path):
        if seg.get("id"):
            start = i
            break
    if start is None:
        start = len(path) - 1
    parts = []
    for i in range(start, -1, -1):
        seg = path[i]
        if i == start and seg.get("id"):
            esc = _css_escape_ident(seg["id"])
            parts.append(f"#{esc}" if esc else f'[id="{_q(seg["id"])}"]')
        elif seg["tag"] in ("html", "body"):
            parts.append(seg["tag"])  # unique by definition
        else:
            parts.append(f"{seg['tag']}:nth-of-type({seg['nthOfType']})")
    return " > ".join(parts)


def _absolute_xpath(path: list) -> str:
    parts = []
    for seg in reversed(path):  # html -> ... -> element
        parts.append(f"{seg['tag']}[{seg['nthOfType']}]")
    return "/" + "/".join(parts)


def _shortest_xpath(path: list) -> str:
    """XPath from nearest id anchor down to element."""
    start = None
    for i, seg in enumerate(path):
        if seg.get("id"):
            start = i
            break
    if start is None:
        return _absolute_xpath(path)
    parts = []
    for i in range(start, -1, -1):
        seg = path[i]
        if i == start:
            parts.append(f"*[@id='{_q(seg['id'])}']")
        else:
            parts.append(f"{seg['tag']}[{seg['nthOfType']}]")
    return "//" + "/".join(parts)


# ---------------------------------------------------------------------------
# Locator generation (with live uniqueness verification)
# ---------------------------------------------------------------------------
def _role_locators(page, m: dict) -> list:
    """Priority 1: semantic / role locators (Playwright API style)."""
    out = []
    tag = m["tag"]
    role = m.get("role")
    name = m.get("accessibleName")
    src = m.get("nameSource")
    attrs = m.get("attrs") or {}

    def add(expr_py, expr_js, verifier, desc):
        try:
            cnt = verifier()
        except Exception:
            cnt = -1
        out.append({
            "type": "role", "value": expr_py, "value_js": expr_js,
            "unique": cnt == 1, "match_count": cnt, "note": desc,
        })

    # 1. getByRole
    if role:
        if name:
            add(f'get_by_role("{role}", name="{name}")',
                f'getByRole("{role}", {{ name: "{name}" }})',
                (lambda r=role, n=name: page.get_by_role(r, name=n).count()),
                f'按语义角色 {role} + 可访问名匹配')
        else:
            add(f'get_by_role("{role}")',
                f'getByRole("{role}")',
                (lambda r=role: page.get_by_role(r).count()),
                f'按语义角色 {role} 匹配（无名称）')
    # 2. getByLabel (accessible name from label / aria-label)
    if name and src in ("label", "aria-label", "aria-labelledby") and tag in ("input", "textarea", "select"):
        add(f'get_by_label("{name}")', f'getByLabel("{name}")',
            (lambda n=name: page.get_by_label(n).count()),
            '按关联标签文本匹配')
    # 3. getByPlaceholder
    if attrs.get("placeholder"):
        ph = attrs["placeholder"]
        add(f'get_by_placeholder("{ph}")', f'getByPlaceholder("{ph}")',
            (lambda v=ph: page.get_by_placeholder(v).count()),
            '按占位符文本匹配')
    # 4. getByText (elements whose own text matches)
    if m.get("directText"):
        dt = m["directText"]
        add(f'get_by_text("{dt}", exact=True)', f'getByText("{dt}", {{ exact: true }})',
            (lambda v=dt: page.get_by_text(v, exact=True).count()),
            '按元素自身文本精确匹配')
    return out


def _css_locators(page, m: dict) -> list:
    """Priority 2: CSS selectors, each verified for uniqueness."""
    out = []
    attrs = m.get("attrs") or {}
    tag = m["tag"]
    path = m.get("path") or []

    def add(sel, desc):
        cnt = _css_count(page, sel)
        out.append({"type": "css", "value": sel, "unique": cnt == 1,
                    "match_count": cnt, "note": desc})

    if attrs.get("id"):
        esc = _css_escape_ident(attrs["id"])
        add(f"#{esc}" if esc else f'[id="{_q(attrs["id"])}"]', "唯一 id")
    if attrs.get("testid"):
        add(f'[data-testid="{_q(attrs["testid"])}"]', "data-testid")
    if attrs.get("name"):
        add(f'{tag}[name="{_q(attrs["name"])}"]', "name 属性")
    if attrs.get("placeholder"):
        add(f'{tag}[placeholder="{_q(attrs["placeholder"])}"]', "placeholder 属性")
    if attrs.get("ariaLabel"):
        add(f'{tag}[aria-label="{_q(attrs["ariaLabel"])}"]', "aria-label 属性")
    if attrs.get("title"):
        add(f'{tag}[title="{_q(attrs["title"])}"]', "title 属性")
    if attrs.get("alt"):
        add(f'{tag}[alt="{_q(attrs["alt"])}"]', "alt 属性")
    if attrs.get("value"):
        add(f'{tag}[value="{_q(attrs["value"])}"]', "value 属性")
    if attrs.get("href"):
        add(f'{tag}[href="{_q(attrs["href"])}"]', "href 属性")
    # class combination (up to 4 classes)
    classes = [c for c in (attrs.get("className") or "").split() if c and not c.startswith("!")
               and _css_escape_ident(c)][:4]
    if classes:
        add(f"{tag}." + ".".join(classes), "class 组合")
    # structural path (always unique by construction)
    if path:
        add(_structural_css(path), "结构路径（父链 + nth-of-type）")
    return out


def _xpath_locators(page, m: dict) -> list:
    """Priority 3: XPath expressions, each verified for uniqueness."""
    out = []
    attrs = m.get("attrs") or {}
    tag = m["tag"]
    path = m.get("path") or []
    dt = m.get("directText") or ""
    inner = m.get("innerText") or ""

    def add(xp, desc):
        cnt = _xpath_count(page, xp)
        out.append({"type": "xpath", "value": xp, "unique": cnt == 1,
                    "match_count": cnt, "note": desc})

    if attrs.get("id"):
        add(f'//*[@id="{_q(attrs["id"])}"]', "按 id")
    if dt:
        add(f'//{tag}[normalize-space(text())="{_q(dt)}"]', "按自身文本精确")
    if inner:
        add(f'//{tag}[contains(normalize-space(.), "{_q(inner[:60])}")]', "按包含文本")
    if attrs.get("placeholder"):
        add(f'//{tag}[@placeholder="{_q(attrs["placeholder"])}"]', "按 placeholder")
    if attrs.get("name"):
        add(f'//{tag}[@name="{_q(attrs["name"])}"]', "按 name")
    if attrs.get("ariaLabel"):
        add(f'//{tag}[@aria-label="{_q(attrs["ariaLabel"])}"]', "按 aria-label")
    if attrs.get("testid"):
        add(f'//*[@data-testid="{_q(attrs["testid"])}"]', "按 data-testid")
    if path:
        add(_shortest_xpath(path), "相对路径（id 锚点）")
        add(_absolute_xpath(path), "绝对路径（兜底）")
    return out


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------
def _locate_on_page(page, url: str, keyword: str, exact: bool = False,
                    prefix: str | None = None) -> dict:
    """Run matching + locator generation + screenshots on an ALREADY OPEN page.

    Used by both the one-shot extractor and the interactive browser session.
    The page may be at any URL/state the user navigated to.
    """
    tag_mode = keyword.lower() in KNOWN_TAGS and not exact
    if prefix is None:
        ts = int(time.time() * 1000)
        rnd = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        prefix = f"{ts}_{rnd}"

    page_title = page.title()
    current_url = page.url or url
    matches = page.evaluate(MATCH_JS, {
        "keyword": keyword, "exact": exact, "tagMode": tag_mode,
    })
    if not matches:
        return {
            "url": current_url, "keyword": keyword, "page_title": page_title,
            "matched": 0, "elements": [], "full_shot": None,
            "message": f"未找到与「{keyword}」匹配的可见元素，请调整关键词或匹配模式",
        }

    elements = []
    for m in matches:
        role_l = _role_locators(page, m)
        css_l = _css_locators(page, m)
        xp_l = _xpath_locators(page, m)
        best_role = next((x for x in role_l if x["unique"]), role_l[0] if role_l else None)
        best_css = next((x for x in css_l if x["unique"]), css_l[-1] if css_l else None)
        best_xp = next((x for x in xp_l if x["unique"]), xp_l[-1] if xp_l else None)
        chain = [best_role, best_css, best_xp]
        recommended = None
        for cand in chain:
            if cand and cand.get("unique"):
                cand["recommended"] = True
                recommended = cand["type"]
                break
        elements.append({
            "index": m["index"], "tag": m["tag"], "score": m["score"],
            "matched_on": m["matchedOn"], "direct_text": m["directText"],
            "inner_text": m["innerText"], "role": m["role"],
            "accessible_name": m["accessibleName"], "name_source": m["nameSource"],
            "attrs": m["attrs"], "rect": m["rect"], "outer_html": m["outerHTML"],
            "locators": {"role": role_l[:4], "css": css_l[:5], "xpath": xp_l[:5]},
            "best": {"role": best_role, "css": best_css, "xpath": best_xp},
            "recommended_type": recommended,
            "element_shot": None,
        })

    for el in elements:
        shot = os.path.join(LOCATOR_SHOT_DIR, f"{prefix}_e{el['index']}.png")
        try:
            loc = page.locator(f'[data-__dsh-match="{el["index"]}"]')
            if loc.count() == 1:
                loc.screenshot(path=shot)
                el["element_shot"] = f"/shots/locator/{prefix}_e{el['index']}.png"
        except Exception:
            pass

    try:
        page.evaluate(
            "document.querySelectorAll('[data-__dsh-match]').forEach(el => {"
            "  el.style.outline = '3px solid #e8534e';"
            "  el.style.outlineOffset = '2px';"
            "})"
        )
        full_path = os.path.join(LOCATOR_SHOT_DIR, f"{prefix}_full.png")
        page.screenshot(path=full_path, full_page=True)
        full_shot = f"/shots/locator/{prefix}_full.png"
    except Exception:
        full_shot = None

    return {
        "url": current_url, "keyword": keyword, "page_title": page_title,
        "matched": len(elements), "elements": elements,
        "full_shot": full_shot, "message": "",
    }


def extract_locators(url: str, keyword: str, exact: bool = False,
                     wait_ms: int = 1000, steps: list | None = None,
                     storage_state: str | dict | None = None) -> dict:
    """Open the page, match elements, generate + verify locators, take screenshots.

    storage_state: path to a saved Playwright storage_state JSON — lets the
    extractor run on pages behind login without re-entering credentials.
    """
    tag_mode = keyword.lower() in KNOWN_TAGS and not exact
    ts = int(time.time() * 1000)
    rnd = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    prefix = f"{ts}_{rnd}"

    # support http://user:pass@host/path (HTTP Basic Auth) embedded in the URL
    clean_url, credentials = _split_basic_auth(url)

    with sync_playwright() as p:
        browser = _launch_browser(p)
        try:
            ctx_opts = {
                "viewport": {"width": 1440, "height": 900},
                "storage_state": storage_state,
            }
            if credentials:
                ctx_opts["http_credentials"] = credentials
            context = browser.new_context(**ctx_opts)
            page = context.new_page()
            page.set_default_timeout(25000)
            page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
            if wait_ms:
                page.wait_for_timeout(min(wait_ms, 10000))
            # optional pre-steps (click/fill/wait) to reach the relevant page state
            for st in steps or []:
                act = (st.get("action") or "").strip()
                tgt = st.get("target") or ""
                val = st.get("value") or ""
                if act == "click":
                    page.click(tgt)
                elif act == "fill":
                    page.fill(tgt, val)
                elif act == "check":
                    page.check(tgt)
                elif act == "wait":
                    page.wait_for_timeout(min(int(val or 500), 10000))
                elif act == "goto":
                    page.goto(tgt, wait_until="domcontentloaded", timeout=30000)

            # 复用同一套定位逻辑（对当前 page）
            result = _locate_on_page(page, url, keyword, exact, prefix=prefix)
            return result
        finally:
            browser.close()
