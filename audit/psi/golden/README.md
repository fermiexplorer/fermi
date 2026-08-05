# Golden fixture — alpha Cen AB linear-kinematics chain (joint validation)

A minimal, self-contained test vector — authored by PSI, adopted here as a
permanent audit gate — for cross-validating independent implementations of
the alpha Centauri AB intercept kinematics. If an implementation reproduces
`expected_outputs.json` from `golden_inputs.json` within the stated
tolerances, the kinematic chains agree end-to-end (astrometry conversion,
frame rotation, linear propagation, crossing solve, and the v_inf/beta
curves) and any remaining disagreement is attributable to *inputs*, not code.

## Scope — what a PASS does and does not certify

**Code-parity fixture only.** The input state is an agreed test vector pinned
to full precision. Its parallax is the Akeson et al. 2021 (AJ 162, 14)
central value and its position is Kervella et al. 2016 (A&A 594, A107); its
proper-motion and radial-velocity values are **carried working constants of
the exchange, not Akeson 2021 catalog centrals** (the paper's J2019.5 table
gives mu = (−3639.95 ± 0.42, +700.40 ± 0.17) mas/yr and
V0 = −22.3796 ± 0.0020 km/s). A PASS certifies that the linear kinematic
chains agree end-to-end to the stated tolerances; it does **not** certify
pinned-constant usage below ~0.02 yr (obliquity-digit and kappa-digit drift
sit at ~0.003 yr, under every tolerance), does not endorse any catalog, and
does not validate any input's provenance. Year/pc/position-convention drift
IS distinguishable at the tolerances; sub-0.02-yr constant precision drift is
deliberately tolerated.

No astrometric epoch is pinned inside the state: T_cross is measured from the
epoch at which the state is taken as current, and the crossing *point* is
epoch-invariant. The fixture validates the *linear* chain only; neglected
terms (Proxima's pull on the AB barycenter ~92 AU over the flight, light-time
convention, galactic tide, barycentric wobble) are bounded in
`docs/PP-ARRIVAL-OPTIMUM.md` §5.

## Contents

| File | Role |
|---|---|
| `golden_inputs.json` | One agreed astrometric state + unit conventions + 5 test epochs |
| `expected_outputs.json` | T_cross and v_inf/beta at the 5 epochs, with tolerances — the pinned oracle (sha256-locked in `audit/calcs/audit_golden.py`) |
| `check_golden.py` | PSI's standalone reference checker (stdlib only), archived with its `--write` regeneration mode removed so the oracle cannot be silently rebuilt from the code under test |

## Model and definitions

Heliocentric mean-ecliptic J2000 frame; obliquity rotation R_x(23.43928 deg)
applied to the ICRS Cartesian state; constant space velocity (linear motion):

    r(T) = r0 + v T
    T_cross  = -z0 / v_z                    [yr]   ecliptic-plane crossing
    v_inf(T) = |r0 + v T| / T               [km/s] required straight-line coast speed
    beta(T)  = asin( z(T) / |r(T)| )        [deg]  ecliptic latitude of intercept point

Unit constants are pinned in `golden_inputs.json` (`pc_km`, `ly_km`, Julian
`year_s`, `kms_per_masyr_pc` = 4.74047e-3).

## Headline expected values

- T_cross = 79,371.931 yr; crossing distance 6.40327 ly; v_inf at crossing
  24.18551 km/s.
- beta passes through zero between the 79,000 and 80,000 yr epochs, by
  construction of T_cross.

Full-precision values and per-quantity tolerances (T_cross to 0.02 yr, v_inf
to 1e-4 km/s, beta to 1e-4 deg, distance to 1e-6 ly) are in
`expected_outputs.json`.

## Validation status

The 13 expected values are independently validated by four implementations:
PSI's generator, PSI's second (vectorized) implementation (max relative
deviation 3e-14), this project's `fermi_sim` chain run under the fixture's
pinned constants (max deviation ~1e-15 relative; +0.005 yr on T_cross under
this repo's own constants — inside tolerance), and a fourth structurally
distinct implementation from the foundations audit (≤7.4e-15). The audit
suite (`audit/calcs/audit_golden.py`, section 14) re-runs the `fermi_sim`
chain against the pinned oracle on every audit run.

## Running

    python3 check_golden.py            # PSI's reference checker: PASS/FAIL per value
    .venv/bin/python audit/calcs/audit_golden.py   # the audit gate (engine vs oracle)
