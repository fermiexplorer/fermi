"""Section 14 — golden-fixture gate: fermi_sim vs the pinned PSI oracle.

The fixture (audit/psi/golden/) is an agreed test vector authored by PSI: one
astrometric state + pinned unit conventions + 13 expected values (T_cross
triple + v_inf/beta at five epochs). The expected outputs were generated and
cross-validated by implementations INDEPENDENT of fermi_sim, so gating the
engine against them is a genuine cross-check, not self-comparison. The
oracle is sha256-pinned here; the archived reference checker has its
regeneration mode removed, so the oracle cannot be silently rebuilt from the
code under test.

The gate feeds the FIXTURE's inputs and constants through the engine's own
chain (astro.alpha_centauri_state + intercept), then restores the engine's
carried values — the repo's own catalog state never enters the comparison.
"""

from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

from _util import check, summary

import fermi_sim.astro as astro
import fermi_sim.constants as c
import fermi_sim.intercept as intercept

GOLDEN_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "psi", "golden"))
SHA_INPUTS = "1abd1276645bd5aa67c8b41cf25b0c47348e82344df59fe28705c20be1ad2b4a"
SHA_ORACLE = "99b093a62345aa6d0d606fa68160e2e6908ba726e465db64796aef0949dd7e52"
# v2 (adopted state): Akeson 2021 at native epoch J2019.5, kinematic-frame RV,
# departure origin 2029.0 — the state the engine itself carries.
GOLDEN_V2_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "psi", "golden_v2"))
SHA_INPUTS_V2 = "d05cc162b7194d391e9ad72b373c2e1a45c6f437949c4fe57897a8a856ea6e64"
SHA_ORACLE_V2 = "2054f82417c1c7bdc03a496ee221c11f8b412d04ed2ae36dd800e78b39ece7c4"

_PATCH_ASTRO = ("AC_RA_DEG", "AC_DEC_DEG", "AC_DIST_LY", "AC_PMRA_MASYR",
                "AC_PMDEC_MASYR", "AC_RV_KMS", "_MASYR_PC_TO_KMS")
_PATCH_CONST = ("LY", "PC", "OBLIQUITY")


def _sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _engine_chain(fix: dict, obliquity_deg: float, kappa: float,
                  ly_km: float) -> dict:
    """Run the fixture state through fermi_sim's own chain under the given
    constants; returns the 13 fixture quantities."""
    a, conv = fix["astrometry"], fix["conventions"]
    astro.AC_RA_DEG = a["ra_deg"]
    astro.AC_DEC_DEG = a["dec_deg"]
    astro.AC_PMRA_MASYR = a["pm_ra_masyr"]
    astro.AC_PMDEC_MASYR = a["pm_dec_masyr"]
    astro.AC_RV_KMS = a["rv_kms"]
    astro._MASYR_PC_TO_KMS = kappa
    c.LY = ly_km * 1e3
    c.PC = conv["pc_km"] * 1e3
    c.OBLIQUITY = math.radians(obliquity_deg)
    d_pc = 1000.0 / a["parallax_mas"]
    astro.AC_DIST_LY = d_pc * conv["pc_km"] / ly_km
    st = astro.alpha_centauri_state()
    ys = conv["year_s"]
    tc = intercept.ecliptic_crossing_time(st)
    rc = st.position_at(tc)
    out = {"T_cross_yr": tc / ys,
           "distance_ly": float(np.linalg.norm(rc)) / (ly_km * 1e3),
           "v_inf_kms": float(np.linalg.norm(rc)) / tc / 1e3, "epochs": []}
    for T in fix["epochs_yr"]:
        s = intercept.solve_intercept(st, T * ys)
        out["epochs"].append({"T_yr": T, "v_inf_kms": s.v_inf / 1e3,
                              "beta_deg": s.plane_angle_deg})
    return out


def run() -> None:
    print("\n== 14. Golden-fixture gate (fermi_sim vs pinned PSI oracle) ==")

    in_path = os.path.join(GOLDEN_DIR, "golden_inputs.json")
    or_path = os.path.join(GOLDEN_DIR, "expected_outputs.json")
    check("14a inputs sha256 pinned", _sha256(in_path) == SHA_INPUTS,
          _sha256(in_path)[:16])
    check("14a oracle sha256 pinned", _sha256(or_path) == SHA_ORACLE,
          _sha256(or_path)[:16])
    checker_src = open(os.path.join(GOLDEN_DIR, "check_golden.py"),
                       encoding="utf-8").read()
    check("14a reference checker has no oracle-regeneration mode",
          '"--write" in sys.argv' not in checker_src
          and "json.dump(" not in checker_src)

    fix = json.load(open(in_path))
    exp = json.load(open(or_path))
    tol = exp["tolerances"]
    conv = fix["conventions"]

    saved_a = {k: getattr(astro, k) for k in _PATCH_ASTRO}
    saved_c = {k: getattr(c, k) for k in _PATCH_CONST}
    try:
        got = _engine_chain(fix, conv["obliquity_deg"],
                            conv["kms_per_masyr_pc"] * 1000.0, conv["ly_km"])
        for key in ("T_cross_yr", "distance_ly", "v_inf_kms"):
            d = got[key] - exp["T_cross"][key]
            check(f"14b engine T_cross.{key} vs oracle (tol {tol[key]})",
                  abs(d) <= tol[key], f"delta {d:+.3e}")
        for ge, ee in zip(got["epochs"], exp["epochs"]):
            for key in ("v_inf_kms", "beta_deg"):
                d = ge[key] - ee[key]
                check(f"14b engine T={ge['T_yr']:.0f}.{key} (tol {tol[key]})",
                      abs(d) <= tol[key], f"delta {d:+.3e}")
        # Convention drift: the same state under the repo's own constants must
        # stay inside the fixture's T_cross tolerance (measures obliquity/
        # kappa/LY digit drift, deliberately tolerated below 0.02 yr).
        got_repo = _engine_chain(fix, math.degrees(saved_c["OBLIQUITY"]),
                                 saved_a["_MASYR_PC_TO_KMS"],
                                 saved_c["LY"] / 1e3)
        d = got_repo["T_cross_yr"] - exp["T_cross"]["T_cross_yr"]
        check("14c repo-constants convention drift inside T_cross tolerance",
              abs(d) <= tol["T_cross_yr"], f"delta {d:+.4f} yr")
    finally:
        for k, v in saved_a.items():
            setattr(astro, k, v)
        for k, v in saved_c.items():
            setattr(c, k, v)

    # --- v2: the ADOPTED state (epoch-pinned; 15 values + derived time rows) ---
    in2 = os.path.join(GOLDEN_V2_DIR, "golden_inputs.json")
    or2 = os.path.join(GOLDEN_V2_DIR, "expected_outputs.json")
    check("14e v2 inputs sha256 pinned", _sha256(in2) == SHA_INPUTS_V2,
          _sha256(in2)[:16])
    check("14e v2 oracle sha256 pinned", _sha256(or2) == SHA_ORACLE_V2,
          _sha256(or2)[:16])
    checker2 = open(os.path.join(GOLDEN_V2_DIR, "check_golden.py"),
                    encoding="utf-8").read()
    check("14e v2 reference checker has no oracle-regeneration mode",
          '"--write" in sys.argv' not in checker2
          and "json.dump(" not in checker2)
    fix2 = json.load(open(in2))
    exp2 = json.load(open(or2))
    tol2 = exp2["tolerances"]
    conv2 = fix2["conventions"]
    a2 = fix2["astrometry"]
    # kinematic-frame arithmetic pins (V0 + gravitational-redshift correction)
    check("14e v2 kinematic RV = V0 (-22.3796) + 61.4 m/s correction",
          abs(a2["rv_kms"] - (-22.3796 + 0.0614)) < 1e-9, str(a2["rv_kms"]))
    check("14e v2 epochs pinned (state J2019.5, departure 2029.0)",
          conv2["state_epoch_jyear"] == 2019.5
          and conv2["departure_epoch_jyear"] == 2029.0)
    dep_off = conv2["departure_epoch_jyear"] - conv2["state_epoch_jyear"]
    saved_a2 = {k: getattr(astro, k) for k in _PATCH_ASTRO}
    saved_c2 = {k: getattr(c, k) for k in _PATCH_CONST}
    try:
        got2 = _engine_chain(fix2, conv2["obliquity_deg"],
                             conv2["kms_per_masyr_pc"] * 1000.0,
                             conv2["ly_km"])
        got2["T_cross_from_departure_yr"] = got2["T_cross_yr"] - dep_off
        got2["crossing_date_AD"] = conv2["state_epoch_jyear"] + got2["T_cross_yr"]
        for key in ("T_cross_yr", "T_cross_from_departure_yr",
                    "crossing_date_AD", "distance_ly", "v_inf_kms"):
            d = got2[key] - exp2["T_cross"][key]
            check(f"14f engine v2 T_cross.{key} vs oracle (tol {tol2[key]})",
                  abs(d) <= tol2[key], f"delta {d:+.3e}")
        for ge, ee in zip(got2["epochs"], exp2["epochs"]):
            for key in ("v_inf_kms", "beta_deg"):
                d = ge[key] - ee[key]
                check(f"14f engine v2 T={ge['T_yr']:.0f}.{key} (tol {tol2[key]})",
                      abs(d) <= tol2[key], f"delta {d:+.3e}")
    finally:
        for k, v in saved_a2.items():
            setattr(astro, k, v)
        for k, v in saved_c2.items():
            setattr(c, k, v)
    # The engine's CARRIED state must be the v2 state exactly.
    check("14g engine carries the v2 state verbatim (RA/Dec/PM/RV/parallax)",
          astro.AC_RA_DEG == a2["ra_deg"] and astro.AC_DEC_DEG == a2["dec_deg"]
          and astro.AC_PMRA_MASYR == a2["pm_ra_masyr"]
          and astro.AC_PMDEC_MASYR == a2["pm_dec_masyr"]
          and astro.AC_RV_KMS == a2["rv_kms"]
          and astro.AC_PARALLAX_MAS == a2["parallax_mas"])
    check("14g engine epoch constants match the fixture conventions",
          astro.AC_EPOCH_JYEAR == conv2["state_epoch_jyear"]
          and astro.DEPARTURE_EPOCH_JYEAR == conv2["departure_epoch_jyear"])

    # Restoration guard: the engine's carried state must be untouched.
    st = astro.alpha_centauri_state()
    tc_repo = intercept.ecliptic_crossing_time(st) / (365.25 * 86400.0)
    check("14h engine state restored after gate (crossing ~79,765.9 yr)",
          abs(tc_repo - 79765.9) < 5.0, f"{tc_repo:.1f} yr")


if __name__ == "__main__":
    run()
    raise SystemExit(summary())
