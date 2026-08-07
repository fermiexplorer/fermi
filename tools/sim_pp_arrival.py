"""Deep PP arrival-epoch simulation — the derivation behind docs/PP-ARRIVAL-OPTIMUM.md.

For each candidate arrival epoch T:
  aim(T)   : v_inf and tilt from the intercept geometry (2600-AU miss shave),
  campaign : the FULL 3-D anchored thermal pumping campaign integrated to that aim
             (fermi_sim.pump_schedule.scheduled_pumped_vinf_3d — hyperbolic-leg
             steering, asymptote-latitude gate), steering angle optimised per epoch
             by golden section, dt/4 with the v_inf-overshoot correction
             (d(dv)/d(v_inf) = 0.64 along the campaign; tools/derive_plane_tax.py),
  total    : + the LEO-400 orbit-energy escape leg sqrt(mu_E/a).

Grid: coarse 66-86 kyr (2 kyr) + fine 75-80.5 kyr (500 yr) + the exact ecliptic
crossing. The flyability edge (earliest epoch whose aim tilt the campaign can still
acquire within the 15-yr custody gate) is located by bisection. Three rows are
re-integrated at dt/8 with the winning steering angle as a convergence check.

Output: a printed table + the tracked machine record docs/data/pp_arrival_sim.json
(audit/calcs/audit_pumping.py replays rows from it). Runtime ~4-6 min.

Run:  .venv/bin/python tools/sim_pp_arrival.py
"""
import json
import math
import os
import sys

sys.path.insert(0, ".")
from fermi_sim import constants as c                                     # noqa: E402
from fermi_sim.astro import alpha_centauri_state                         # noqa: E402
from fermi_sim.intercept import ecliptic_crossing_time, solve_intercept  # noqa: E402
from fermi_sim.pump_schedule import ANCHORED_THERMAL, scheduled_pumped_vinf_3d  # noqa: E402

A0, ISP = 2.5e-4, 2800.0
MISS = 2600.0 * c.AU
ESCAPE = math.sqrt(c.MU_EARTH / (c.R_EARTH + 400e3))
DTS = 0.25
DV_SLOPE = 0.64
LAT_GATE = 0.06
CUSTODY_GATE = 15.0
GOLD = (math.sqrt(5.0) - 1.0) / 2.0
STATE = alpha_centauri_state()
OUT = os.path.join("docs", "data", "pp_arrival_sim.json")


def aim(T_yr):
    """Aim (v_inf, tilt) at epoch T with the 2600-AU miss allowance spent OPTIMALLY.

    The permitted aim-point offset (|delta| <= 2600 AU on the encounter sphere) is a
    free DIRECTION: it can shave speed, buy down tilt, or blend both. The pre-audit
    convention (max speed shave at unchanged tilt) one-sidedly overpriced tilted
    epochs (adversarial-audit finding 0). Here the offset direction is optimized
    against the closed-form pumped budget (v_inf + derived plane tax + pump tax) —
    a proxy used ONLY for aim selection; every row's Δv is still the full 3-D
    campaign integration.
    """
    import numpy as np
    from scipy.optimize import minimize

    from fermi_sim.departure import plane_tax_for, pump_tax_for

    s = solve_intercept(STATE, T_yr * c.YEAR)
    V = s.v_inf_vec
    dv_mag = MISS / (T_yr * c.YEAR)

    def decompose(Vv):
        v = float(np.linalg.norm(Vv))
        tilt = math.degrees(math.atan2(float(Vv[2]), float(np.hypot(Vv[0], Vv[1]))))
        return v, tilt

    def cost(ang):
        th, ph = ang
        d = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph),
                      math.cos(th)]) * dv_mag
        v, tilt = decompose(V + d)
        return v + plane_tax_for(v, tilt) + pump_tax_for(v)

    best = None
    for th0, ph0 in ((0.3, 0.0), (1.57, 3.14), (2.8, 0.0), (1.57, 0.0)):
        r = minimize(cost, [th0, ph0], method="Nelder-Mead",
                     options={"xatol": 1e-3, "fatol": 0.01, "maxiter": 200})
        if best is None or r.fun < best.fun:
            best = r
    th, ph = best.x
    d = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph),
                  math.cos(th)]) * dv_mag
    v, tilt = decompose(V + d)
    return v, tilt


def run_campaign(v_t, beta, gamma, dts=DTS):
    v, dv, yr, revs, lat = scheduled_pumped_vinf_3d(
        A0, v_t, beta, ANCHORED_THERMAL, isp_s=ISP, power_model="thermal",
        steer_gamma_deg=gamma, _dt_scale=dts, max_yr=30.0)
    ok = (v >= v_t - 1.0 and yr <= CUSTODY_GATE
          and (beta < 1e-6 or (lat is not None and abs(lat + beta) <= LAT_GATE)))
    return (dv - DV_SLOPE * (v - v_t)), yr, lat, ok


def best_campaign(v_t, beta, dts=DTS):
    if beta < 1e-6:
        adj, yr, lat, ok = run_campaign(v_t, 0.0, 0.0, dts)
        return 0.0, adj, yr, lat, ok
    cache = {}

    def f(g):
        g = round(g, 3)
        if g not in cache:
            adj, yr, lat, ok = run_campaign(v_t, beta, g, dts)
            cache[g] = (adj if ok else adj + 1e6, adj, yr, lat, ok)
        return cache[g][0]

    a, b = 0.0, 40.0
    c1, c2 = b - GOLD * (b - a), a + GOLD * (b - a)
    for _ in range(12):
        if f(c1) <= f(c2):
            b, c2 = c2, c1
            c1 = b - GOLD * (b - a)
        else:
            a, c1 = c1, c2
            c2 = a + GOLD * (b - a)
        if b - a < 0.8:
            break
    g = min(cache, key=lambda k: cache[k][0])
    _, adj, yr, lat, ok = cache[g]
    return g, adj, yr, lat, ok


def flyable(T_yr):
    """Can the campaign acquire aim(T)? Uses the SAME golden steering search as the
    table rows (audit finding 6: a fixed 3-angle probe missed feasible angles near
    the edge — 65 kyr flies at gamma ~33-36 deg)."""
    v_t, beta = aim(T_yr)
    _, _, _, _, ok = best_campaign(v_t, abs(beta))
    return ok


def main():
    tcx = ecliptic_crossing_time(STATE) / c.YEAR
    # Row grid starts at 66,000: under the adopted state the flyability edge sits
    # ~64.8 kyr, so a 65,000-yr row would ride the 15-yr custody gate with no
    # margin (the edge itself is located by bisection below, not by a row).
    epochs = sorted(set(list(range(66000, 86001, 2000)) + [73000]
                        + list(range(75000, 80501, 500)) + [round(tcx)]))
    rows = []
    print(f"{'T (yr)':>8} {'v_inf':>7} {'tilt':>7} {'gamma*':>7} {'campaign':>9} "
          f"{'total':>8} {'custody':>8}  flag")
    for T in epochs:
        v_t, beta = aim(T)
        g, dv_c, yr, lat, ok = best_campaign(v_t, abs(beta))
        total = (ESCAPE + dv_c) if ok else None
        rows.append({"T": T, "vinf": round(v_t, 1), "tilt": round(beta, 3),
                     "gamma": round(g, 1), "dv_campaign": round(dv_c, 1) if ok else None,
                     "dv_total": round(total, 1) if ok else None,
                     "custody_yr": round(yr, 3), "ok": ok,
                     "crossing": abs(T - round(tcx)) < 1})
        print(f"{T:8,} {v_t/1e3:7.3f} {beta:+7.2f} {g:7.1f} "
              f"{(dv_c/1e3 if ok else float('nan')):9.3f} "
              f"{(total/1e3 if ok else float('nan')):8.3f} {yr:8.2f}  "
              f"{'OK' if ok else 'UNFLYABLE'}{'  << crossing' if abs(T-round(tcx))<1 else ''}")

    good = [r for r in rows if r["ok"]]
    tmin = min(good, key=lambda r: r["dv_total"])
    cx = next(r for r in rows if r["crossing"])
    print(f"\nbasin bottom: T={tmin['T']:,} total {tmin['dv_total']/1e3:.3f} km/s; "
          f"crossing +{cx['dv_total']-tmin['dv_total']:.1f} m/s")

    # flyability edge by bisection (earliest flyable aim between 64k and the first OK row)
    lo, hi = 62000.0, float(min(r["T"] for r in good))
    for _ in range(7):
        mid = 0.5 * (lo + hi)
        if flyable(mid):
            hi = mid
        else:
            lo = mid
    edge = 0.5 * (lo + hi)
    print(f"flyability edge: ~{edge:,.0f} yr (aim tilt {aim(edge)[1]:+.2f} deg)")

    # convergence: re-integrate three rows at dt/8 with the winning gamma
    conv = []
    for T in (75000, tmin["T"], round(tcx)):
        r = next(x for x in rows if x["T"] == T)
        v_t, beta = aim(T)
        adj, yr, lat, ok = run_campaign(v_t, abs(beta), r["gamma"], dts=0.125)
        d = (ESCAPE + adj) - r["dv_total"]
        conv.append({"T": T, "dv_total_dt8": round(ESCAPE + adj, 1), "delta": round(d, 1)})
        print(f"convergence T={T:,}: dt/8 total {(ESCAPE+adj)/1e3:.3f} km/s "
              f"(dt/4 - dt/8 = {-d:+.1f} m/s)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"meta": {"a0": A0, "isp_s": ISP, "escape_leg": round(ESCAPE, 1),
                            "dt_scale": DTS, "dv_slope_correction": DV_SLOPE,
                            "miss_au": 2600, "crossing_yr": round(tcx, 1),
                            "basin_bottom_T": tmin["T"],
                            "basin_bottom_total": tmin["dv_total"],
                            "crossing_penalty": round(cx["dv_total"] - tmin["dv_total"], 1),
                            "flyable_edge_yr": round(edge),
                            "schedule": "ANCHORED_THERMAL", "power_model": "thermal"},
                   "rows": rows, "convergence": conv}, f, indent=1)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
