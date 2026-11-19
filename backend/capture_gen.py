"""Capture screenshots including the new requirement-generation feature."""
import os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUT, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # 1. Case center list (now with new tab)
    page.goto("http://127.0.0.1:8000/cases", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(OUT, "cases-with-tab.png"), full_page=True)
    print("OK cases-with-tab")

    # 2. Click the generation tab
    page.get_by_text("需求生成用例").first.click()
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(OUT, "gen-empty.png"), full_page=True)
    print("OK gen-empty")

    # 3. Simulate upload + generate
    page.locator('input[type=file]').set_input_files("demo_requirement.md")
    page.wait_for_timeout(200)
    page.get_by_text("一键生成全方位测试用例").click()
    page.wait_for_timeout(3000)
    page.screenshot(path=os.path.join(OUT, "gen-result.png"), full_page=True)
    print("OK gen-result")

    # 4. History tab
    page.get_by_text("历史记录").first.click()
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(OUT, "gen-history.png"), full_page=True)
    print("OK gen-history")

    if errors:
        print("PAGE ERRORS:")
        for e in errors:
            print("  -", e)
    browser.close()
