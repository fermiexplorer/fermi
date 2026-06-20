"""Audit 2 -- intercept geometry.

Independent checks:
* Forward-propagation: fly a probe in a straight line at the required v_inf for T
  and confirm it actually lands on Alpha Centauri's position at T.
* Brute-force the minimum-|v_inf| arrival time and compare to the closed form.
* Confirm the minimum |v_inf| equals AC's tangential speed (a geometric identity).
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

from _util import check, rel_err, summary

from fermi_sim import constants as c
from fermi_sim.astro import alpha_centauri_state
from fermi_sim.intercept import min_speed_arrival, required_v_inf, solve_intercept


def run() -> None:
    print("== Audit 2: intercept geometry ==")
    st = alpha_centauri_state()

    # 1. Forward-propagation closes the loop: probe at v_inf for T reaches AC.
    for t_yr in (60_000, 75_000, 90_000):
        T = t_yr * c.YEAR
        v_inf = required_v_inf(st, T)
        probe_pos = v_inf * T  # straight line from the Sun
        ac_pos = st.position_at(T)
        miss = np.linalg.norm(probe_pos - ac_pos)
        check(f"forward-propagation lands on AC at {t_yr:,} yr",
              miss < 1e-3 * np.linalg.norm(ac_pos),
              f"miss {miss/c.AU:.3e} AU (numerical)")

    # 2. Closed-form tangential optimum == brute-force minimum.
    tan = min_speed_arrival(st)

    def speed(t_yr):
        return solve_intercept(st, t_yr * c.YEAR).v_inf

    res = minimize_scalar(speed, bounds=(40_000, 100_000), method="bounded")
    check("closed-form min-speed time matches numerical optimiser (<1%)",
          rel_err(tan.arrival_time_yr, res.x) < 1e-2,
          f"closed {tan.arrival_time_yr:,.0f} yr vs numeric {res.x:,.0f} yr")

    # 3. Minimum |v_inf| equals AC's tangential speed (independent identity).
    d = np.linalg.norm(st.r)
    v_rad = float(np.dot(st.r, st.v)) / d
    v_tan = np.sqrt(np.dot(st.v, st.v) - v_rad**2)
    check("min |v_inf| == AC tangential speed",
          rel_err(tan.v_inf, v_tan) < 1e-3,
          f"{tan.v_inf/c.KMS:.3f} vs tangential {v_tan/c.KMS:.3f} km/s")

    # 4. At the ecliptic crossing the required v_inf is in-plane (tilt ~ 0).
    from fermi_sim.intercept import ecliptic_crossing_time

    sol = solve_intercept(st, ecliptic_crossing_time(st))
    check("v_inf is in-plane at the ecliptic crossing (|tilt|<0.5 deg)",
          abs(sol.plane_angle_deg) < 0.5,
          f"tilt {sol.plane_angle_deg:.3f} deg")


if __name__ == "__main__":
    run()
    raise SystemExit(summary())
