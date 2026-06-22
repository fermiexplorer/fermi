"""Derive the low-thrust Earth-escape departure-Δv fit (Plan 02, Phase A: naïve spiral).

This is the AUDITABLE generator behind the web tool's departure Δv. It integrates
``fermi_sim.departure.spiral_escape_dv`` (constant-tangential-thrust RK4 spiral from LEO to
the required Earth-relative hyperbolic excess) across a grid of v∞,E and LEO altitudes, then
fits a closed form so the browser can evaluate it in O(1) — no live integration, instant
slider response, but the number is DERIVED from the real spiral, not a hand-set penalty.

It prints (a) the altitude-collapse check that justifies the fit form, (b) the coefficients to
embed in `fermi_sim` and `web/physics.js`, and (c) the max fit error in the feasible band.
Re-run to reproduce:  .venv/bin/python tools/fit_spiral.py
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from fermi_sim import constants as c
from fermi_sim.departure import spiral_escape_dv

K = 1000.0  # m/s per km/s


def v_circ_kms(alt_km: float) -> float:
    return math.sqrt(c.MU_EARTH / (c.R_EARTH + alt_km * 1e3)) / K


def integrate(alt_km: float, vinf_grid):
    r0 = c.R_EARTH + alt_km * 1e3
    return np.array([spiral_escape_dv(c.MU_EARTH, r0, v * K) / K for v in vinf_grid])


def main():
    vinf = np.linspace(0.0, 32.0, 33)          # km/s
    alts = [200.0, 400.0, 700.0, 1000.0, 1500.0, 2000.0]

    dv = {a: integrate(a, vinf) for a in alts}

    # Hypothesis: dv(v∞,E, alt) ≈ v_circ(alt) + g(v∞,E), with g altitude-independent.
    G = np.array([dv[a] - v_circ_kms(a) for a in alts])
    spread = float(np.max(np.ptp(G, axis=0)))
    print(f"altitude-collapse check: max spread of (Δv − v_circ) across {alts[0]:.0f}–{alts[-1]:.0f} km")
    print(f"  = {spread*1000:.1f} m/s  (small ⇒ the v_circ(alt) + g(v∞,E) form is justified)\n")

    # g(v∞,E) = Δv − v_circ is ~linear (slope≈1) with an offset; fit over the relevant range
    # v∞,E ≥ 8 km/s (feasible interstellar arrivals give v∞,E ≈ 17–20 km/s, never the low-v curve).
    allv = np.tile(vinf, len(alts))
    allg = G.flatten()
    fitmask = allv >= 8.0
    fv, fg = allv[fitmask], allg[fitmask]
    A = np.vstack([np.ones_like(fv), fv]).T        # LINEAR: g = c0 + c1·v (data is slope≈1)
    (c0, c1), *_ = np.linalg.lstsq(A, fg, rcond=None)

    pred = c0 + c1 * allv
    err = np.abs(pred - allg)
    band = (allv >= 10.0) & (allv <= 25.0)        # the feasible band
    valid = allv >= 8.0

    print(f"FIT  Δv = v_circ(alt) + {c0:.6f} + {c1:.6f}·v∞,E   [km/s, v∞,E km/s, valid ≥8 km/s]")
    print(f"  v_circ(alt) = sqrt(MU_EARTH/(R_EARTH+alt))  (exact, per altitude)")
    print(f"  SI form: dv = v_circ + ({1000*c0:.3f}) + ({c1:.6f})*v_inf_e   [m/s, v_inf_e m/s]")
    print(f"  max |error| valid ≥8 km/s   : {np.max(err[valid])*1000:.1f} m/s")
    print(f"  max |error| feasible 10–25  : {np.max(err[band])*1000:.1f} m/s "
          f"({100*np.max(err[band])/np.mean(allg[band]):.2f}%)")

    print("\n v∞,E   Δv_integrated   Δv_fit   (alt=400 km)")
    vc4 = v_circ_kms(400.0)
    for i, v in enumerate(vinf):
        if v in (8, 10, 15, 18, 20, 25, 30):
            print(f"  {v:5.1f}   {dv[400.0][i]:10.3f}   {vc4 + c0 + c1*v:8.3f}")


if __name__ == "__main__":
    main()
