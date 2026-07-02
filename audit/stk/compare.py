#!/usr/bin/env python3
"""Compare STK/Astrogator results against the Fermi engine (fermi_sim).

Reads out/stk_results.json (written by run_stk_audit.py on the Windows host, or filled
in by hand from the STK GUI — see README.md), computes the fermi_sim reference numbers
LIVE (so they can never go stale), and prints PASS/FAIL.

Run from the repo root or this folder:  .venv/bin/python audit/stk/compare.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from fermi_sim import constants as c
from fermi_sim import departure as dep

# ---- shared config (identical to run_stk_audit.py and audit/gmat) ----
ALT_KM = 400.0
ACCEL = 5.0e-4                                   # m/s^2
VINF_SUN = 23270.0                               # m/s (min-speed intercept @ 58,138 yr)
TILT_DEG = -10.0


def fermi_reference():
    v_inf_e, _ = dep.v_inf_earth_required(VINF_SUN, TILT_DEG)
    dv_imp = dep.impulsive_dv_from_leo(v_inf_e, ALT_KM)
    r_p = c.R_EARTH + ALT_KM * 1e3
    t_escape = dep.spiral_escape_dv(c.MU_EARTH, r_p, 0.0, accel=ACCEL) / ACCEL
    return dict(c3=(v_inf_e / 1e3) ** 2, dv_imp=dv_imp, t_escape=t_escape)


def pct(a, b):
    return abs(a - b) / abs(b) * 100.0 if b else float("inf")


def main():
    ref = fermi_reference()
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out", "stk_results.json")
    if not os.path.exists(path):
        print("out/stk_results.json not found — run run_stk_audit.py on the Windows host")
        print("(or do the Manual GUI path in README.md and fill the JSON in by hand).")
        return 1
    with open(path) as fh:
        r = json.load(fh)

    print("=" * 72)
    print("STK/Astrogator  vs  fermi_sim   --   independent cross-validation")
    print("=" * 72)
    ok = True

    print("\nCHECK 1 -- impulsive (Oberth) departure from LEO")
    print(f"  fermi_sim: dv = {ref['dv_imp']/1e3:.4f} km/s prograde  ->  required "
          f"C3 = v_inf,E^2 = {ref['c3']:.4f} km^2/s^2")
    if "check1_c3_km2s2" in r:
        d = pct(r["check1_c3_km2s2"], ref["c3"])
        passed = d < 0.05
        ok &= passed
        print(f"  STK:       post-burn C3 = {r['check1_c3_km2s2']:.4f} km^2/s^2")
        print(f"  -> diff {d:.4g}%   [{'PASS' if passed else 'FAIL'}]  (tol 0.05%)")
    else:
        print("  (check1_c3_km2s2 missing from stk_results.json)")
        ok = False

    print("\nCHECK 2 -- low-thrust Earth-escape spiral (constant accel 5e-4 m/s^2, to C3=0)")
    print(f"  fermi_sim: escape t = {ref['t_escape']:.4e} s "
          f"(dv = a*t = {ACCEL*ref['t_escape']/1e3:.4f} km/s, ~692 revs)")
    if "check2_escape_s" in r:
        d = pct(r["check2_escape_s"], ref["t_escape"])
        passed = d < 1.5
        ok &= passed
        print(f"  STK:       escape t = {r['check2_escape_s']:.4e} s "
              f"(dv = a*t = {ACCEL*r['check2_escape_s']/1e3:.4f} km/s)")
        if "check2_dv_kms" in r:
            print(f"             (STK's own maneuver DeltaV = {r['check2_dv_kms']:.4f} km/s)")
        print(f"  -> diff {d:.4g}%   [{'PASS' if passed else 'FAIL'}]  (tol 1.5%)")
    else:
        print("  (check2_escape_s missing from stk_results.json)")
        ok = False

    print("\n" + "=" * 72)
    print("RESULT:", "ALL CHECKS PASS -- STK confirms the Fermi engine" if ok
          else "FAIL / incomplete -- see above")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
