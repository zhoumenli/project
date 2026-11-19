"""Capture screenshots of the platform pages using real Chrome via Playwright."""
import os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUT, exist_ok=True)

PAGES = [
    ("dashboard", "http://127.0.0.1:8000/dashboard"),
    ("cases", "http://127.0.0.1:8000/cases"),
    ("api-test", "http://127.0.0.1:8000/api-test"),
    ("ui-test", "http://127.0.0.1:8000/ui-test"),
    ("runs", "http://127.0.0.1:8000/runs"),
]

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    for name, url in PAGES:
        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(600)
            path = os.path.join(OUT, f"{name}.png")
            page.screenshot(path=path, full_page=True)
            print(f"OK {name}: {path}")
        except Exception as e:
            print(f"FAIL {name}: {e}")
    if errors:
        print("PAGE ERRORS:")
        for e in errors:
            print("  -", e)
    browser.close()
