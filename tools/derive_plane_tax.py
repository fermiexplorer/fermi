"""Derive the pumped-campaign out-of-plane (tilt) cost curve — issue #9.

For each aim tilt beta, integrate the 3-D anchored campaign
(:func:`fermi_sim.pump_schedule.scheduled_pumped_vinf_3d`) with the steering angle
gamma optimised by golden section, and measure

    plane_tax(beta) = dv_3d(beta, gamma*) - dv_3d(0)

with both runs at a REFINED timestep (_dt_scale = 0.125 — the engine-dt termination
overshoot is ~30 m/s per step, comparable to the small-beta signal) and a residual
overshoot correction: runs terminate with slightly different achieved v_inf, and along
the anchored campaign d(dv)/d(v_inf) ~= 0.64 (from OPT_CAMPAIGN_THERMAL_TABLE), so

    cost_adj = (dv - dv_base) - 0.64 * (v_achieved - v_base).

Acceptance gates per knot: achieved v_inf >= target, asymptote latitude within
0.05 deg of -beta, custody within 2 yr of the planar 12.0 yr. The printed table is
baked into fermi_sim/pump_schedule.py (PLANE_TAX_THERMAL_TABLE) and mirrored to
web/physics.js; audit_pumping re-derives pinned knots independently (DOP853).

Run:  .venv/bin/python tools/derive_plane_tax.py [quick]
      quick = coarser dt (_dt_scale 0.25) and fewer knots, for smoke runs.
"""
import math
import sys

sys.path.insert(0, ".")
from fermi_sim.pump_schedule import (            # noqa: E402
    ANCHORED_THERMAL, OPTIMIZED_SCHEDULES, scheduled_pumped_vinf_3d,
)

A0, ISP, VT = 2.5e-4, 2800.0, 23640.0
DV_SLOPE = 0.64          # d(dv)/d(v_inf) along the anchored thermal campaign
LAT_GATE = 0.05          # deg
CUSTODY_GATE = 14.0      # yr

GOLD = (math.sqrt(5.0) - 1.0) / 2.0


def run(beta, gamma, sch=ANCHORED_THERMAL, power_model="thermal", dts=0.125):
    v, dv, yr, revs, lat = scheduled_pumped_vinf_3d(
        A0, VT, beta, sch, isp_s=ISP, power_model=power_model,
        steer_gamma_deg=gamma, _dt_scale=dts, max_yr=30.0)
    return v, dv, yr, lat


def cost_of(beta, gamma, base_v, base_dv, sch=ANCHORED_THERMAL,
            power_model="thermal", dts=0.125):
    v, dv, yr, lat = run(beta, gamma, sch, power_model, dts)
    ok = (v >= VT - 1.0 and lat is not None and abs(lat + beta) <= LAT_GATE
          and yr <= CUSTODY_GATE)
    adj = (dv - base_dv) - DV_SLOPE * (v - base_v)
    return adj, ok, v, dv, yr, lat


def golden_gamma(beta, base_v, base_dv, lo=0.0, hi=40.0, iters=14,
                 sch=ANCHORED_THERMAL, power_model="thermal", dts=0.125):
    """Golden-section min of cost(gamma); returns (gamma*, cost*, ok, yr, lat)."""
    cache = {}

    def f(g):
        g = round(g, 4)
        if g not in cache:
            adj, ok, v, dv, yr, lat = cost_of(beta, g, base_v, base_dv, sch,
                                              power_model, dts)
            cache[g] = (adj if ok else adj + 1.0e6, adj, ok, yr, lat)
        return cache[g][0]

    a, b = lo, hi
    c1 = b - GOLD * (b - a)
    c2 = a + GOLD * (b - a)
    while b - a > 0.5:
        if f(c1) <= f(c2):
            b, c2 = c2, c1
            c1 = b - GOLD * (b - a)
        else:
            a, c1 = c1, c2
            c2 = a + GOLD * (b - a)
        iters -= 1
        if iters <= 0:
            break
    g_best = min(cache, key=lambda g: cache[g][0])
    _, adj, ok, yr, lat = cache[g_best]
    return g_best, adj, ok, yr, lat


def main():
    quick = "quick" in sys.argv[1:]
    dts = 0.25 if quick else 0.125
    betas = ([0.5, 2.48, 6.0] if quick else
             [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.48, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0])

    print(f"baseline 3-D(0) runs (dt_scale {dts}) ...")
    bv, bdv, byr, blat = run(0.0, 0.0, dts=dts)
    print(f"  thermal base: v {bv:.1f} dv {bdv:.2f} yr {byr:.3f}")

    rows = []
    for beta in betas:
        g, adjc, ok, yr, lat = golden_gamma(beta, bv, bdv, dts=dts)
        naive = VT * math.sin(math.radians(beta))
        rows.append((beta, adjc, g, yr))
        print(f"  beta {beta:5.2f}: plane_tax {adjc:7.1f} m/s  (naive {naive:7.1f}, "
              f"ratio {adjc/naive if naive else 0.0:5.3f})  gamma* {g:5.1f}  yr {yr:6.3f} "
              f" lat {round(lat, 3) if lat is not None else None}  {'OK' if ok else 'GATE-FAIL'}")

    print("\nPLANE_TAX_THERMAL_TABLE = (      # (beta_deg, plane tax m/s) — derived, issue #9")
    print("    (0.0, 0.0),")
    for beta, adjc, g, yr in rows:
        print(f"    ({beta}, {max(0.0, round(adjc, 1))}),   # gamma* {g:.1f} deg, {yr:.2f} yr")
    print(")")

    print("\ncap-model comparison point (PSI's assumption; their measured 578 m/s):")
    sch_cap = OPTIMIZED_SCHEDULES[2.5e-4][0]
    cv, cdv, cyr, _ = run(0.0, 0.0, sch=sch_cap, power_model="cap", dts=dts)
    g, adjc, ok, yr, lat = golden_gamma(2.48, cv, cdv, sch=sch_cap,
                                        power_model="cap", dts=dts)
    print(f"  cap 2.48 deg: plane_tax {adjc:.1f} m/s  gamma* {g:.1f}  yr {yr:.3f}  "
          f"lat {round(lat,3) if lat is not None else None}  {'OK' if ok else 'GATE-FAIL'}")


if __name__ == "__main__":
    main()
