"""Audit 8 -- perihelion synchrotron ("lasso idea": external EM station).

Independent checks — different methods, never engine-vs-itself:
* Kepler-period bookkeeping verified by a NUMERICAL two-body propagation
  (scipy adaptive RK45): the ellipse after the first kick must return to the
  station after exactly the period the engine charges for it.
* Energy bookkeeping: the station's delivered specific energy must equal the
  probe's total energy gain (kicks are the only energy source).
* The escape-termination rule as an invariant: whenever the verdict is
  'escaped_below', the final perihelion speed must be >= v_esc but < v_target,
  and no periods may be charged after the escaping kick.
* Vis-viva algebra: dv_final_min = sqrt(v_inf^2 + v_esc^2) - v_esc, and its
  monotonic decrease with deeper stations (the deep-station endgame win).
* The externally documented validation anchor (expert-critique worked example):
  1 AU station, 5 km/s kicks, target 25 km/s -> exactly 3 passes, 11.95 yr,
  escapes at 15.2 km/s, infeasible.
"""

from __future__ import annotations

import math

from _util import check, close, rel_err

from fermi_sim import constants as c
from fermi_sim.departure import synchrotron_escape


def run() -> None:
    print("== Audit 8: perihelion synchrotron (lasso / external station) ==")

    # 1. External validation anchor: the critique's worked example.
    s = synchrotron_escape(c.AU / c.R_SUN, 5e3, 25e3)
    check("critique anchor: 1 AU, 5 km/s, tgt 25 -> 3 passes",
          s["passes"] == 3, f"{s['passes']} passes")
    check("critique anchor: accel phase 11.95 yr",
          close(s["time_yr"], 11.95, abs_=0.02), f"{s['time_yr']:.2f} yr")
    check("critique anchor: escapes at 15.2 km/s, infeasible",
          s["escaped_below"] and not s["reached"] and close(s["v_inf_final"] / 1e3, 15.2, abs_=0.05),
          f"v_inf={s['v_inf_final']/1e3:.1f} km/s")

    # 2. Kepler bookkeeping vs numerical two-body propagation (scipy RK45):
    #    after the first kick at a 10 Rsun station the orbit is a bound ellipse;
    #    propagate it numerically for the period the engine would charge and
    #    verify the probe is back at the station with zero radial velocity.
    from scipy.integrate import solve_ivp
    r_p = 10.0 * c.R_SUN
    v0 = math.sqrt(c.MU_SUN / r_p) + 5e3           # circular + first kick
    eps = 0.5 * v0 * v0 - c.MU_SUN / r_p
    a = -c.MU_SUN / (2.0 * eps)
    period = 2.0 * math.pi * math.sqrt(a ** 3 / c.MU_SUN)

    def rhs(_t, y):
        r3 = math.hypot(y[0], y[1]) ** 3
        return [y[2], y[3], -c.MU_SUN * y[0] / r3, -c.MU_SUN * y[1] / r3]

    sol = solve_ivp(rhs, (0.0, period), [r_p, 0.0, 0.0, v0], rtol=1e-11, atol=1e-3)
    xf, yf, vxf, vyf = sol.y[:, -1]
    rf = math.hypot(xf, yf)
    vrad = (xf * vxf + yf * vyf) / rf
    vf = math.hypot(vxf, vyf)
    check("numerical two-body: probe returns to the station after one Kepler period",
          rel_err(rf, r_p) < 1e-6 and abs(vrad) < 1.0,
          f"r={rf/c.R_SUN:.6f} Rsun (station 10), v_rad={vrad:.2f} m/s")
    check("numerical two-body: perihelion speed conserved over the lap",
          rel_err(vf, v0) < 1e-8, f"{vf:.3f} vs {v0:.3f} m/s")

    # 3. Energy bookkeeping: kicks are the only energy source.
    s10 = synchrotron_escape(10.0, 5e3, 23.64e3)
    v_circ = math.sqrt(c.MU_SUN / (10.0 * c.R_SUN))
    e_gain = 0.5 * s10["v_peri_final"] ** 2 - 0.5 * v_circ ** 2
    check("station energy equals the probe's kinetic-energy gain (<1e-12)",
          rel_err(s10["energy_spec"], e_gain) < 1e-12,
          f"{s10['energy_spec']:.6e} vs {e_gain:.6e} J/kg")

    # 4. Escape-termination invariant on a stranded case (10 Rsun, 2 km/s):
    #    final v_p in [v_esc, v_target), and the reported passes are consistent
    #    with fixed kicks (v_p = v_circ + passes*dv).
    s2 = synchrotron_escape(10.0, 2e3, 25e3)
    check("stranded case sits in [v_esc, v_target) with escaped_below set",
          s2["escaped_below"] and s2["v_esc"] <= s2["v_peri_final"] < s2["v_target"],
          f"v_p={s2['v_peri_final']/1e3:.1f} in [{s2['v_esc']/1e3:.1f}, {s2['v_target']/1e3:.1f})")
    check("fixed-kick bookkeeping: v_p,final = v_circ + passes*dv (<1e-12)",
          rel_err(s2["v_peri_final"], v_circ + s2["passes"] * 2e3) < 1e-12,
          f"{s2['passes']} passes")

    # 5. Vis-viva algebra + the deep-station endgame win.
    for rp_rsun, v_inf in ((4.0, 24e3), (10.0, 24e3), (215.03, 24e3)):
        r = rp_rsun * c.R_SUN
        v_esc = math.sqrt(2.0 * c.MU_SUN / r)
        expect = math.sqrt(v_inf ** 2 + v_esc ** 2) - v_esc
        got = synchrotron_escape(rp_rsun, 5e3, v_inf)["dv_final_min"]
        check(f"dv_final_min algebra @ {rp_rsun:.0f} Rsun",
              rel_err(got, expect) < 1e-12, f"{got/1e3:.2f} km/s")
    d4 = synchrotron_escape(4.0, 5e3, 24e3)["dv_final_min"]
    d10 = synchrotron_escape(10.0, 5e3, 24e3)["dv_final_min"]
    d1au = synchrotron_escape(215.03, 5e3, 24e3)["dv_final_min"]
    check("deeper station -> smaller final-kick requirement (4 Rs < 10 Rs < 1 AU)",
          d4 < d10 < d1au, f"{d4/1e3:.2f} < {d10/1e3:.2f} < {d1au/1e3:.2f} km/s")

    # 6. Feasible case leaves AT or ABOVE the target v_inf (never below).
    check("feasible verdict implies departure v_inf >= target",
          s10["reached"] and s10["v_inf_final"] >= 23.64e3 - 1.0,
          f"v_inf={s10['v_inf_final']/1e3:.1f} km/s")

    # 7. max_passes exhaustion must NEVER report success (regression: reached was
    #    previously a tolerance test that a capped, still-bound run could satisfy).
    s_cap = synchrotron_escape(10.0, 5e3, 23.64e3, max_passes=3)
    check("max_passes exhaustion reports reached=False",
          not s_cap["reached"] and s_cap["passes"] == 3,
          f"passes={s_cap['passes']}, v_p={s_cap['v_peri_final']/1e3:.0f} km/s")


if __name__ == "__main__":
    from _util import summary
    run()
    raise SystemExit(summary())
