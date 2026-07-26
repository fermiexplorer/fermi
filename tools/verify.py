#!/usr/bin/env python3
"""Run the FULL verification battery as ONE command — no one-off command chains.

    .venv/bin/python tools/verify.py            # standard battery
    .venv/bin/python tools/verify.py --ui       # + the browser UI suite (heavy: Playwright)

Steps (each subprocess-isolated, with its own timeout):
  1. run_audits.py         independent audit suite (astropy, conservation laws, pins)
  2. audit_webjs.mjs       web JS <-> Python parity
  3. syntax_check.mjs      inline <script> blocks of index.html parse
  4. pytest tests/         smoke / regression
  5. ui_sliders.py         (--ui only) browser behaviour suite — one heavy process,
                           run strictly after everything else (RAM hygiene)

Prints one PASS/FAIL line per step plus each step's own summary tail; exits
non-zero if anything fails. Keep this the ONLY way the battery is invoked —
see CLAUDE.md ("Running Tests").
"""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
PY = os.path.join(".venv", "bin", "python")

STEPS = [
    ("audits", [PY, "audit/calcs/run_audits.py"], 420),
    ("parity", ["node", "audit/calcs/audit_webjs.mjs"], 180),
    ("syntax", ["node", "tools/syntax_check.mjs"], 60),
    ("pytest", [PY, "-m", "pytest", "tests/", "-q"], 240),
]
if "--ui" in sys.argv:
    STEPS.append(("ui", [PY, "audit/calcs/ui_sliders.py"], 420))

failed = []
for name, cmd, tmo in STEPS:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=tmo)
        out = (r.stdout + r.stderr).strip().splitlines()
        tail = "\n".join("    " + ln for ln in out[-3:])
        ok = r.returncode == 0
    except subprocess.TimeoutExpired:
        tail, ok = f"    (timed out after {tmo}s)", False
    print(f"[{'PASS' if ok else 'FAIL'}] {name}\n{tail}")
    if not ok:
        failed.append(name)

print("-" * 60)
print("VERIFY: ALL PASSED" if not failed else f"VERIFY: FAILED -> {failed}")
sys.exit(1 if failed else 0)
