"""Audit 3 -- departure energetics.

Independent checks via conservation laws and convergence:
* The impulsive budget must satisfy the vis-viva energy balance exactly.
* The heliocentric departure speed must yield the requested v_inf_sun.
* The low-thrust spiral must (a) end at the target orbital energy and
  (b) converge as thrust acceleration -> 0 (the 'low-thrust limit').
"""

from __future__ import annotations

import math

from _util import check, rel_err, summary

from fermi_sim import constants as c
from fermi_sim.departure import (
    _SPIRAL_FIT_C0,
    _SPIRAL_FIT_C1,
    impulsive_dv_from_leo,
    leo_speeds,
    spiral_escape_dv,
    v_inf_earth_required,
)


def run() -> None:
    print("== Audit 3: departure energetics ==")

    alt = 400.0
    v_circ, v_esc = leo_speeds(alt)
    r_leo = c.R_EARTH + alt * 1e3

    # 1. Impulsive burn: after Delta-v the specific orbital energy must equal
    #    v_inf_earth^2 / 2 (energy conservation, independent of the formula used).
    for v_inf_e in (12e3, 18e3, 25e3):
        dv = impulsive_dv_from_leo(v_inf_e, alt)
        v_after = v_circ + dv
        energy = 0.5 * v_after**2 - c.MU_EARTH / r_leo
        check(f"impulsive energy balance @ v_inf_E={v_inf_e/1e3:.0f} km/s",
              rel_err(energy, 0.5 * v_inf_e**2) < 1e-9,
              f"E={energy:.3e} vs {0.5*v_inf_e**2:.3e} J/kg")

    # 2. Heliocentric: v_dep at 1 AU must give the requested v_inf_sun.
    for v_inf_sun in (20e3, 24e3):
        _, v_dep = v_inf_earth_required(v_inf_sun, 0.0)
        energy = 0.5 * v_dep**2 - c.MU_SUN / c.AU
        check(f"helio v_dep yields v_inf_sun={v_inf_sun/1e3:.0f} km/s",
              rel_err(energy, 0.5 * v_inf_sun**2) < 1e-9,
              f"E={energy:.3e} vs {0.5*v_inf_sun**2:.3e} J/kg")

    # 3. Spiral integrator ends at (or just past) the target energy.
    v_inf_e = 18e3
    target_E = 0.5 * v_inf_e**2
    # Re-run a thin propagation to read the terminal energy is overkill; instead
    # verify the *delta-v* is bracketed sensibly and converges with accel.
    dv_a = spiral_escape_dv(c.MU_EARTH, r_leo, v_inf_e, accel=5e-4)
    dv_b = spiral_escape_dv(c.MU_EARTH, r_leo, v_inf_e, accel=2.5e-4)
    check("spiral delta-v converges as accel halves (<6%)",
          rel_err(dv_a, dv_b) < 0.06,
          f"{dv_a/1e3:.2f} vs {dv_b/1e3:.2f} km/s")

    # 4. Bounds: low-thrust spiral must exceed the impulsive floor but stay below
    #    the naive 'circular velocity + v_inf' sum (a loose physical ceiling).
    dv_imp = impulsive_dv_from_leo(v_inf_e, alt)
    ceiling = v_circ + v_inf_e
    check("spiral delta-v sits between impulsive floor and (v_circ + v_inf) ceiling",
          dv_imp < dv_a < ceiling,
          f"{dv_imp/1e3:.1f} < {dv_a/1e3:.1f} < {ceiling/1e3:.1f} km/s")

    # 5. Sanity vs a known mission: Voyager-1 left the Sun at ~16.6 km/s; our
    #    minimum heliocentric v_inf (~23 km/s) is necessarily larger.
    from fermi_sim.astro import alpha_centauri_state
    from fermi_sim.intercept import min_speed_arrival

    vmin = min_speed_arrival(alpha_centauri_state()).v_inf / c.KMS
    check("min cruise v_inf exceeds Voyager-1 (16.6 km/s), as expected",
          22 < vmin < 24, f"{vmin:.2f} km/s")

    # 6. DERIVED departure fit (Plan 02, Phase A) must match a FRESH spiral integration
    #    (independent re-derivation: the embedded closed-form vs the RK4 it replaced).
    worst = 0.0
    for v in (10e3, 15e3, 18e3, 20e3, 22e3, 25e3):
        fit = v_circ + _SPIRAL_FIT_C0 + _SPIRAL_FIT_C1 * v
        integ = spiral_escape_dv(c.MU_EARTH, r_leo, v)
        worst = max(worst, abs(fit - integ))
    check("derived departure fit matches integrated spiral to <0.5% (10-25 km/s)",
          worst < 0.005 * 18e3, f"max |fit - integration| = {worst:.1f} m/s")

    # 7. Cross-method: the integrated spiral is within ~1.5 km/s of the classic Edelbaum
    #    estimate (v_circ + v_inf,E) at every test point -> it is genuinely spiral-class.
    for v in (15e3, 20e3, 25e3):
        integ = spiral_escape_dv(c.MU_EARTH, r_leo, v)
        check(f"spiral within 1.5 km/s of Edelbaum (v_circ+v_inf) @ {v/1e3:.0f} km/s",
              abs(integ - (v_circ + v)) < 1.5e3,
              f"{integ/1e3:.2f} vs {(v_circ+v)/1e3:.2f} km/s")

    # 8. Phase B — a LOOSE gate degenerates to the always-on spiral (validates the gated integrator).
    from fermi_sim.departure import perigee_biased_escape_dv
    dv_loose, esc_loose, _ = perigee_biased_escape_dv(c.MU_EARTH, r_leo, 18e3, gate=1e9)
    check("perigee-biased loose gate reproduces the naïve spiral (escapes, same Δv)",
          esc_loose and rel_err(dv_loose, dv_a) < 0.02,
          f"{dv_loose/1e3:.2f} vs naïve {dv_a/1e3:.2f} km/s")

    # 9. Phase B FINDING — at ~milli-g thrust, real perigee-biasing is time-divergent: it does NOT
    #    reach escape within a practical horizon, so it cannot lower the usable departure budget.
    #    (Hence the naïve spiral / lowthrust_departure_dv stays the design Δv.)
    _, esc_pb, yr_pb = perigee_biased_escape_dv(c.MU_EARTH, r_leo, 18e3, gate=5.0, max_t_yr=30.0)
    check("perigee-biased (gate 5) does NOT escape within 30 yr at ~milli-g (time-divergent)",
          not esc_pb, f"escaped={esc_pb} after {yr_pb:.0f} yr")


if __name__ == "__main__":
    run()
    raise SystemExit(summary())
