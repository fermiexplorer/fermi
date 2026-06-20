"""Playwright UI test: render index.html in Chromium, verify all charts draw,
exercise the tech dropdowns + sliders, run the animation, and screenshot.

Catches real render errors the DOM-shim parity check cannot (Plotly, 3D WebGL,
interactions). Requires:  pip install playwright  &&  playwright install chromium

Run:  .venv/bin/python audits/ui_playwright.py
"""

import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
URL = "file://" + os.path.join(ROOT, "index.html")
SHOT = os.path.join(ROOT, "tmp", "ro", "ui.png")  # tmp/ is gitignored

errors = []


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1500, "height": 1600})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL, wait_until="networkidle")

        charts = ["follow3d", "chartOrbit3d", "follow2d", "chartOrbit2d", "chartTimeline",
                  "chartDv", "chartMass", "chartPower", "chartTime"]
        for cid in charts:
            page.wait_for_selector(f"#{cid} .plot-container", state="attached", timeout=15000)
        print(f"[ok] all {len(charts)} charts rendered")

        summary = page.inner_text("#summary")
        assert "Minimum spacecraft" in summary and "km/s" in summary, "summary missing"
        kpi = page.inner_text("#kpis")
        assert "Solar array" in kpi and "m²" in kpi, "array area missing from KPIs"
        print("[ok] summary panel + solar-array KPIs present")

        page.select_option("#soltech", "30|2.8")
        assert page.inner_text("#o_cellEff") == "30", "GaAs preset failed"
        page.select_option("#propsel", "Krypton|12")
        assert page.inner_text("#o_tankfrac") == "12", "krypton preset failed"
        page.select_option("#enginetech", "hall|2000|0.55|5")
        assert page.inner_text("#o_isp") == "2000", "hall preset failed"
        print("[ok] tech dropdowns drive their sliders")

        page.select_option("#enginetech", "gridded|3000|0.60|6")
        label0 = page.inner_text("#tlabel")
        page.click("#playbtn")
        page.wait_for_timeout(1500)
        page.click("#playbtn")
        assert page.inner_text("#tlabel") != label0, "animation did not advance"
        print("[ok] Play animates the trajectory + timeline")

        os.makedirs(os.path.dirname(SHOT), exist_ok=True)
        page.screenshot(path=SHOT, full_page=True)
        print(f"[ok] screenshot saved to {os.path.relpath(SHOT, ROOT)}")
        browser.close()

    if errors:
        print("\nCONSOLE/PAGE ERRORS:")
        for e in errors[:20]:
            print("  -", e)
        return 1
    print("\nALL PLAYWRIGHT UI CHECKS PASSED (no console errors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
