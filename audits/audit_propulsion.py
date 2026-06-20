"""Audit 4 -- propulsion and energy bookkeeping.

Independent checks:
* The rocket equation, recovered by numerically integrating m dv = -v_e dm.
* The electrical-energy formula, recovered from power x burn-time.
* The thrust/power relation F = 2 eta P / v_e.
"""

from __future__ import annotations

import math

from _util import check, rel_err, summary

from acsim import constants as c
from acsim.spacecraft import (
    electrical_energy,
    exhaust_velocity,
    propellant_mass,
    thrust_from_power,
    thrust_phase_duration,
)


def run() -> None:
    print("== Audit 4: propulsion & energy ==")

    dry, dv, isp, eta = 255.0, 20e3, 3000.0, 0.6
    ve = exhaust_velocity(isp)

    # 1. Rocket equation by direct numerical integration of the mass flow.
    #    dv = -v_e * d(ln m); integrate m from m0 down until dv is reached.
    m0 = dry + propellant_mass(dry, dv, isp)
    steps = 2_000_000
    dm = (m0 - dry) / steps
    m = m0
    dv_accum = 0.0
    for _ in range(steps):
        dv_accum += ve * dm / m
        m -= dm
    check("rocket equation recovered by integrating m dv = -v_e dm (<0.1%)",
          rel_err(dv_accum, dv) < 1e-3,
          f"integrated {dv_accum/1e3:.3f} vs {dv/1e3:.3f} km/s")

    # 2. Energy via power * time equals the closed-form 1/2 m_p v_e^2 / eta.
    mp = propellant_mass(dry, dv, isp)
    P = 5000.0
    F = thrust_from_power(P, isp, eta)
    t = thrust_phase_duration(mp, isp, P, eta)
    E_pt = P * t
    E_formula = electrical_energy(mp, isp, eta)
    check("electrical energy: P*t == 1/2 m_p v_e^2 / eta",
          rel_err(E_pt, E_formula) < 1e-9,
          f"{E_pt/3.6e6:,.0f} vs {E_formula/3.6e6:,.0f} kWh")

    # 3. Thrust/power relation and its inverse (impulse) are consistent.
    check("thrust F == 2 eta P / v_e",
          rel_err(F, 2 * eta * P / ve) < 1e-12)
    total_impulse = mp * ve
    check("burn time == total impulse / thrust",
          rel_err(t, total_impulse / F) < 1e-12,
          f"{t/c.YEAR:.2f} yr")

    # 4. Energy grows with Isp at fixed delta-v (the key trade behind 'solar wins').
    e_lo = electrical_energy(propellant_mass(dry, dv, 1500), 1500, eta)
    e_hi = electrical_energy(propellant_mass(dry, dv, 6000), 6000, eta)
    check("electrical energy rises with Isp at fixed delta-v", e_hi > e_lo,
          f"{e_lo/3.6e6:,.0f} -> {e_hi/3.6e6:,.0f} kWh (1500->6000 s)")


if __name__ == "__main__":
    run()
    raise SystemExit(summary())
