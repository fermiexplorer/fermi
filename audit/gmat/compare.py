#!/usr/bin/env python3
"""Compare GMAT's independent propagation against the Fermi engine (fermi_sim).

Run the two GMAT scripts first (see run_gmat.sh), then:  python3 audit/gmat/compare.py

The Fermi reference numbers are computed live from fermi_sim, so they can never go
stale. GMAT is a completely independent astrodynamics propagator (NASA), so a match
is a genuine cross-validation -- not the engine checking itself.

Config (must match the .script files):
  * circular orbit, radius 6771 km  (= fermi_sim "400 km altitude", R_earth 6371 km)
  * Earth point-mass gravity, mu = 398600.4 km^3/s^2  (= fermi_sim MU_EARTH 3.986004e14)
  * mission: min-speed intercept @ 58,138 yr -> v_inf,Sun = 23.270 km/s, tilt -10 deg
  * Check 2 spiral: constant tangential acceleration 5e-4 m/s^2, escape at energy = 0
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from fermi_sim import constants as c
from fermi_sim import departure as dep

# ---- shared config ----
ALT_KM = 400.0
R_P_KM = (c.R_EARTH + ALT_KM * 1e3) / 1e3          # 6771.0 km
MU_KM = c.MU_EARTH / 1e9                            # 398600.4 km^3/s^2
ACCEL = 5.0e-4                                      # m/s^2 (constant, model default)
MASS = 1000.0                                       # kg
VINF_SUN = 23270.0                                 # m/s
TILT_DEG = -10.0


def fermi_reference():
    v_inf_e, v_dep = dep.v_inf_earth_required(VINF_SUN, TILT_DEG)
    dv_imp = dep.impulsive_dv_from_leo(v_inf_e, ALT_KM)
    c3_expected = (v_inf_e / 1e3) ** 2             # km^2/s^2
    r_p = c.R_EARTH + ALT_KM * 1e3
    dv_spiral = dep.spiral_escape_dv(c.MU_EARTH, r_p, 0.0, accel=ACCEL)
    t_escape = dv_spiral / ACCEL                   # s
    n_revs, _ = dep.earth_escape_revs(ACCEL * MASS, MASS, perigee_km=ALT_KM)
    return dict(v_inf_e=v_inf_e, dv_imp=dv_imp, c3_expected=c3_expected,
                dv_spiral=dv_spiral, t_escape=t_escape, n_revs=n_revs)


def read_rows(path):
    """Return numeric data rows (skip the repeated GMAT header lines)."""
    rows = []
    with open(path) as fh:
        for line in fh:
            tok = line.split()
            if not tok:
                continue
            try:
                rows.append([float(x) for x in tok])
            except ValueError:
                continue                            # header row
    return rows


def parse_impulsive(path):
    rows = read_rows(path)
    # columns: ElapsedSecs, Earth.RMAG, Earth.C3Energy ; last row = post-burn
    return rows[-1][2]                              # GMAT C3 (km^2/s^2)


def parse_lowthrust(path):
    rows = read_rows(path)
    # columns: ElapsedSecs, RMAG, X, Y, Z, VX, VY, VZ, TotalMass
    prev_t, prev_e = None, None
    for r in rows:
        t, rmag = r[0], r[1]
        vx, vy, vz = r[5], r[6], r[7]
        energy = 0.5 * (vx * vx + vy * vy + vz * vz) - MU_KM / rmag   # km^2/s^2
        if prev_e is not None and prev_e < 0.0 <= energy:
            # linear interpolation of the energy=0 crossing
            f = (0.0 - prev_e) / (energy - prev_e)
            return prev_t + f * (t - prev_t)
        prev_t, prev_e = t, energy
    return None                                     # never escaped within the log


def pct(a, b):
    return abs(a - b) / abs(b) * 100.0 if b else float("inf")


def main():
    ref = fermi_reference()
    out = os.path.join(HERE, "out")
    f1 = os.path.join(out, "01_impulsive.txt")
    f2 = os.path.join(out, "02_lowthrust.txt")

    print("=" * 72)
    print("GMAT  vs  fermi_sim   --   independent cross-validation")
    print("=" * 72)
    ok = True

    print("\nCHECK 1 -- impulsive (Oberth) departure from LEO")
    print(f"  fermi_sim: dv = {ref['dv_imp']/1e3:.4f} km/s prograde  ->  required "
          f"C3 = v_inf,E^2 = {ref['c3_expected']:.4f} km^2/s^2")
    if os.path.exists(f1):
        c3 = parse_impulsive(f1)
        d = pct(c3, ref["c3_expected"])
        passed = d < 0.05
        ok &= passed
        print(f"  GMAT:      post-burn C3 = {c3:.4f} km^2/s^2")
        print(f"  -> diff {d:.4g}%   [{'PASS' if passed else 'FAIL'}]  (tol 0.05%)")
    else:
        print(f"  (GMAT output {f1} not found -- run run_gmat.sh first)")
        ok = False

    print("\nCHECK 2 -- low-thrust Earth-escape spiral (constant accel 5e-4 m/s^2, to energy=0)")
    print(f"  fermi_sim: escape t = {ref['t_escape']:.4e} s "
          f"(dv = a*t = {ref['dv_spiral']/1e3:.4f} km/s, ~{ref['n_revs']:.0f} revs)")
    if os.path.exists(f2):
        t_g = parse_lowthrust(f2)
        if t_g is None:
            print(f"  GMAT: spiral did not reach escape within the log -- extend the run")
            ok = False
        else:
            dv_g = ACCEL * t_g
            dt = pct(t_g, ref["t_escape"])
            passed = dt < 1.5
            ok &= passed
            print(f"  GMAT:      escape t = {t_g:.4e} s "
                  f"(dv = a*t = {dv_g/1e3:.4f} km/s)")
            print(f"  -> diff {dt:.4g}%   [{'PASS' if passed else 'FAIL'}]  (tol 1.5%)")
    else:
        print(f"  (GMAT output {f2} not found -- run run_gmat.sh first)")
        ok = False

    print("\n" + "=" * 72)
    print("RESULT:", "ALL CHECKS PASS -- GMAT confirms the Fermi engine" if ok
          else "FAIL / incomplete -- see above")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
