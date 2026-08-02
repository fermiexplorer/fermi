"""Derive the pumped-mission arrival-epoch table by DIRECT SIMULATION — issue #11.

No closed-form budget in the loop: for each candidate arrival epoch T the aim
(v_inf, tilt) comes from the intercept geometry (2600-AU miss shave), and the FULL
3-D anchored thermal campaign is integrated to that aim
(:func:`fermi_sim.pump_schedule.scheduled_pumped_vinf_3d`, steering angle optimised
per epoch by golden section, dt/4 with the dt/8 overshoot correction of
tools/derive_plane_tax.py). The optimum arrival is then READ OFF the rows, not
asserted. The closed-form budget's own sweep is printed alongside as a cross-check.

Run:  .venv/bin/python tools/derive_epoch_table.py
"""
import math
import sys

sys.path.insert(0, ".")
from fermi_sim import constants as c                              # noqa: E402
from fermi_sim.astro import alpha_centauri_state                  # noqa: E402
from fermi_sim.departure import pumped_departure_dv               # noqa: E402
from fermi_sim.intercept import ecliptic_crossing_time, solve_intercept  # noqa: E402
from fermi_sim.pump_schedule import ANCHORED_THERMAL, scheduled_pumped_vinf_3d  # noqa: E402

A0, ISP = 2.5e-4, 2800.0
MISS = 2600.0 * c.AU
ESCAPE = math.sqrt(c.MU_EARTH / (c.R_EARTH + 400e3))   # LEO 400 km orbit-energy leg
DTS = 0.25
GOLD = (math.sqrt(5.0) - 1.0) / 2.0
STATE = alpha_centauri_state()


def aim(T_yr):
    s = solve_intercept(STATE, T_yr * c.YEAR)
    v = max(0.0, s.v_inf - MISS / (T_yr * c.YEAR))
    return v, s.plane_angle_deg


def campaign(v_t, beta, gamma):
    return scheduled_pumped_vinf_3d(A0, v_t, beta, ANCHORED_THERMAL, isp_s=ISP,
                                    power_model="thermal", steer_gamma_deg=gamma,
                                    _dt_scale=DTS, max_yr=30.0)


def best_campaign(v_t, beta):
    """Golden-section on the steering angle; returns (dv, yr, lat, ok)."""
    if beta < 1e-6:
        v, dv, yr, revs, lat = campaign(v_t, 0.0, 0.0)
        return dv - 0.64 * (v - v_t), yr, lat, v >= v_t - 1.0
    cache = {}

    def f(g):
        g = round(g, 3)
        if g not in cache:
            v, dv, yr, revs, lat = campaign(v_t, beta, g)
            ok = (v >= v_t - 1.0 and lat is not None and abs(lat + beta) <= 0.06
                  and yr <= 14.5)
            adj = (dv - 0.64 * (v - v_t))
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
    return adj, yr, lat, ok


def main():
    tcx = ecliptic_crossing_time(STATE) / c.YEAR
    epochs = [58000.0, 65000.0, 70000.0, 73000.0, 75000.0, 77000.0, 77800.0,
              round(tcx), 81000.0, 85000.0]
    print(f"escape leg (400 km LEO): {ESCAPE/1e3:.2f} km/s; campaign: 3-D anchored "
          f"thermal, a0 {A0:.1e}, Isp {ISP:.0f}, dt/{int(1/DTS)}")
    print(f"{'T (yr)':>8} {'v_inf':>7} {'tilt':>7} {'campaign':>9} {'total':>7} "
          f"{'vs best':>8} {'custody':>8}  note")
    rows = []
    for T in epochs:
        v_t, beta = aim(T)
        dv_c, yr, lat, ok = best_campaign(v_t, abs(beta))
        total = ESCAPE + dv_c if ok else float("inf")
        rows.append((T, v_t, beta, dv_c, total, yr, ok))
    best = min(r[4] for r in rows)
    for T, v_t, beta, dv_c, total, yr, ok in rows:
        note = ""
        if not ok:
            note = "campaign CANNOT acquire this aim (tilt beyond the hyperbolic-leg validity)"
        elif abs(T - round(tcx)) < 1:
            note = "ecliptic crossing (in-plane aim) — DESIGN POINT"
        print(f"{T:8,.0f} {v_t/1e3:7.3f} {beta:+7.2f} "
              f"{dv_c/1e3 if ok else float('nan'):9.3f} "
              f"{total/1e3 if ok else float('nan'):7.3f} "
              f"{(total-best) if ok else float('nan'):+8.1f} {yr:8.2f}  {note}")
    print("\ncross-check — closed-form budget sweep (v_inf + derived plane tax + tax tables):")
    for T in epochs:
        v_t, beta = aim(T)
        try:
            dv = pumped_departure_dv(v_t, beta, 400.0)
            print(f"{T:8,.0f} budget {dv/1e3:7.3f} km/s")
        except ValueError as e:
            print(f"{T:8,.0f} budget refused: {e}")


if __name__ == "__main__":
    main()
