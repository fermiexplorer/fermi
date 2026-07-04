"""Playwright UI test: render index.html in Chromium, verify all charts draw,
exercise the tech dropdowns + sliders, run the animation, and screenshot.

Catches real render errors the DOM-shim parity check cannot (Plotly, 3D WebGL,
interactions). Requires:  pip install playwright  &&  playwright install chromium

Run:  .venv/bin/python audit/calcs/ui_playwright.py
"""

import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PORT = 8123
URL = f"http://127.0.0.1:{PORT}/index.html"   # http, not file:// — history.replaceState needs a real origin
SHOT = os.path.join(ROOT, "tmp", "ro", "ui.png")  # tmp/ is gitignored

errors = []


def main() -> int:
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    try:
        return run()
    finally:
        srv.terminate()


def run() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1500, "height": 1600})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL, wait_until="networkidle")

        charts = ["chartOrbit3d", "chartTimeline", "chartDv", "chartMass", "chartPower", "chartTime"]
        for cid in charts:
            page.wait_for_selector(f"#{cid} .plot-container", state="attached", timeout=15000)
        # #follow3d is the Three.js chase cam by default (build 91+): expect a WebGL canvas
        page.wait_for_selector("#follow3d canvas", state="attached", timeout=15000)
        # the 2D views are opt-in: enable the toggle, then they must draw
        page.check("#show2d")
        for cid in ("follow2d", "chartOrbit2d"):
            page.wait_for_selector(f"#{cid} .plot-container", state="attached", timeout=15000)
        print(f"[ok] {len(charts)} Plotly charts + Three.js chase cam + 2D views rendered")

        summary = page.inner_text("#summary")
        assert "FEASIBLE" in summary and "km/s" in summary, "summary missing"
        kpi = page.inner_text("#kpis")
        assert "Solar array" in kpi and "m²" in kpi, "array area missing from KPIs"
        print("[ok] summary panel + solar-array KPIs present")

        page.select_option("#soltech", "30|146")
        assert page.inner_text("#o_cellEff") == "30", "GaAs preset failed"
        page.select_option("#propsel", "Krypton|4|83.80")
        assert page.inner_text("#o_tankfrac") == "4.0", "krypton preset failed"
        isp_before = page.inner_text("#o_isp")
        page.select_option("#enginetech", "hall|1585|0.50|5")
        assert page.inner_text("#o_isp") != isp_before, "hall preset did not move the Isp display"
        print("[ok] tech dropdowns drive their sliders")

        page.select_option("#enginetech", "gridded-adv|3000|0.50|4")
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
