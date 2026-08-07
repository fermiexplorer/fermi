#!/usr/bin/env python3
"""Golden-fixture v2 checker for the alpha Cen AB linear-kinematics chain.

Self-contained (Python 3.8+ standard library only). Recomputes every value in
expected_outputs.json from golden_inputs.json through the agreed kinematic
chain and asserts agreement to the stated tolerances.

This is PSI's reference implementation, archived with ONE modification: the
original's `--write` mode (which regenerated expected_outputs.json from this
same code, making the checker its own oracle) is removed. The expected
outputs are a fixed oracle, pinned by sha256 in audit/calcs/audit_golden.py;
the audit suite gates fermi_sim against that oracle, never this script
against itself.

Chain (heliocentric mean-ecliptic J2000 frame; state epoch J2019.5):
  1. RA/Dec/parallax (all at J2019.5) -> ICRS Cartesian position;
     d_pc = 1000/parallax_mas.
  2. PM (mu_alpha* convention, includes cos-dec) + kinematic-frame RV
     -> ICRS velocity on the J2019.5 direction basis,
     v = rv*u + pm_ra*d_pc*k*e_ra + pm_dec*d_pc*k*e_dec,
     k = kms_per_masyr_pc.
  3. Rotate both by R_x(obliquity) into the mean-ecliptic frame.
  4. Linear motion r(T) = r0 + v T, T in years since J2019.5 (state clock).
     T_cross = -z0/v_z  (ecliptic-plane crossing, exact closed form).
     v_inf(T) = |r0 + v T| / T   [km/s]  (state-clock T, same origin as
                T_cross_yr).
     beta(T)  = asin(z(T)/|r(T)|)  [deg] (ecliptic latitude of the intercept
                direction; 0 at T_cross by construction).
  5. Reported time conventions:
     T_cross_yr               state clock, years since J2019.5
     T_cross_from_departure_yr = T_cross_yr - (2029.0 - 2019.5)
     crossing_date_AD          = 2019.5 + T_cross_yr

Usage:
  python3 check_golden.py           # recompute + assert -> PASS/FAIL
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def ecliptic_state(inp, conv):
    """Astrometry -> (r0 [km], v [km/s]) 3-vectors, mean-ecliptic frame."""
    ra = math.radians(inp["ra_deg"])
    dec = math.radians(inp["dec_deg"])
    d_pc = 1000.0 / inp["parallax_mas"]
    d_km = d_pc * conv["pc_km"]
    u = (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra),
         math.sin(dec))
    e_ra = (-math.sin(ra), math.cos(ra), 0.0)
    e_dec = (-math.sin(dec) * math.cos(ra), -math.sin(dec) * math.sin(ra),
             math.cos(dec))
    k = conv["kms_per_masyr_pc"]
    r_eq = [d_km * u[i] for i in range(3)]
    v_eq = [inp["rv_kms"] * u[i] + inp["pm_ra_masyr"] * d_pc * k * e_ra[i]
            + inp["pm_dec_masyr"] * d_pc * k * e_dec[i] for i in range(3)]
    eps = math.radians(conv["obliquity_deg"])
    ce, se = math.cos(eps), math.sin(eps)

    def rot(w):
        return (w[0], ce * w[1] + se * w[2], -se * w[1] + ce * w[2])

    return rot(r_eq), rot(v_eq)


def compute(fix):
    r0, v = ecliptic_state(fix["astrometry"], fix["conventions"])
    conv = fix["conventions"]
    ys, ly = conv["year_s"], conv["ly_km"]
    epoch0 = conv["state_epoch_jyear"]
    dep = conv["departure_epoch_jyear"]
    tc_s = -r0[2] / v[2]
    tc_yr = tc_s / ys
    rc = [r0[i] + v[i] * tc_s for i in range(3)]
    dc = math.sqrt(sum(x * x for x in rc))
    out = {"T_cross": {"T_cross_yr": tc_yr,
                       "T_cross_from_departure_yr": tc_yr - (dep - epoch0),
                       "crossing_date_AD": epoch0 + tc_yr,
                       "distance_ly": dc / ly,
                       "v_inf_kms": dc / tc_s}, "epochs": []}
    for t_yr in fix["epochs_yr"]:
        t_s = t_yr * ys
        r = [r0[i] + v[i] * t_s for i in range(3)]
        dist = math.sqrt(sum(x * x for x in r))
        out["epochs"].append({"T_yr": t_yr, "v_inf_kms": dist / t_s,
                              "beta_deg": math.degrees(math.asin(r[2] / dist))})
    return out


def main():
    with open(os.path.join(HERE, "golden_inputs.json")) as f:
        fix = json.load(f)
    got = compute(fix)
    with open(os.path.join(HERE, "expected_outputs.json")) as f:
        exp = json.load(f)
    n_fail = 0

    def check(name, a, b, tol):
        nonlocal n_fail
        ok = abs(a - b) <= tol
        n_fail += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'} {name}: got {a!r} expected {b!r} "
              f"(tol {tol})")

    for key in ("T_cross_yr", "T_cross_from_departure_yr", "crossing_date_AD",
                "distance_ly", "v_inf_kms"):
        check(f"T_cross.{key}", got["T_cross"][key], exp["T_cross"][key],
              exp["tolerances"][key])
    for ge, ee in zip(got["epochs"], exp["epochs"]):
        assert ge["T_yr"] == ee["T_yr"], "epoch list mismatch"
        for key in ("v_inf_kms", "beta_deg"):
            check(f"T={ge['T_yr']:.0f}.{key}", ge[key], ee[key],
                  exp["tolerances"][key])
    print("RESULT:", "PASS" if n_fail == 0 else f"FAIL ({n_fail})")
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
