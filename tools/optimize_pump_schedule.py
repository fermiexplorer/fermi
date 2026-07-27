#!/usr/bin/env python3
"""Optimise the pumping-campaign schedule parameters per a0 (issue #4).

Search: scipy Nelder-Mead over Schedule(th_retro, th_pro, e_guard, rp_latch),
objective = campaign delta-v at COARSE resolution (dt x3) with a reach penalty,
multi-start from the bang-bang geometry and two perturbed seeds; the winner is
re-evaluated at FULL engine resolution and only that fine-grained result is
reported/baked (the optimiser's own numbers are never published).

Importable: optimize_at(a0, tgt) -> (Schedule, fine_result). CLI prints a table
for the requested a0 list (read-only; baking into fermi_sim is a separate,
reviewed edit).
"""
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import numpy as np
from scipy.optimize import minimize

from fermi_sim.pump_schedule import Schedule, scheduled_pumped_vinf, RP_FLOOR_AU

TGT = 23.64e3


def _clip(p):
    return Schedule(
        th_retro=float(np.clip(p[0], 15.0, 175.0)),
        th_pro=float(np.clip(p[1], 15.0, 175.0)),
        e_guard=float(np.clip(p[2], -25.0, -0.3)) * 1e7,
        rp_latch=float(np.clip(p[3], RP_FLOOR_AU, 0.90)),
    )


def _cost(p, a0, tgt, dt_scale, max_yr, power_model):
    sch = _clip(p)
    v, dv, yr, _ = scheduled_pumped_vinf(a0, tgt, sch, max_yr=max_yr, _dt_scale=dt_scale,
                                         power_model=power_model)
    if v >= tgt * 0.999:
        return dv
    return dv + 1.0e5 + 10.0 * (tgt - v)


def optimize_at(a0, tgt=TGT, max_yr=60.0, verbose=True, seeds=None, maxiter=160,
                power_model="cap"):
    if seeds is None:
        seeds = [
            [60.0, 70.0, -3.0, RP_FLOOR_AU],      # the bang-bang geometry
            [100.0, 110.0, -1.5, 0.50],           # wide arcs, shallow latch
            [40.0, 50.0, -6.0, RP_FLOOR_AU],      # narrow arcs, deep guard
        ]
    best_p, best_c = None, float("inf")
    for s0 in seeds:
        res = minimize(_cost, s0, args=(a0, tgt, 3.0, max_yr, power_model),
                       method="Nelder-Mead",
                       options={"maxiter": maxiter, "xatol": 0.5, "fatol": 5.0})
        if res.fun < best_c:
            best_c, best_p = res.fun, res.x
        if verbose:
            print(f"  seed {s0}: coarse cost {res.fun/1e3:.3f} km/s "
                  f"-> {_clip(res.x)}")
    sch = _clip(best_p)
    fine = scheduled_pumped_vinf(a0, tgt, sch, max_yr=max_yr,
                                 power_model=power_model)   # full resolution
    return sch, fine


def main():
    a0s = [float(a) for a in sys.argv[1:]] or [2.5e-4]
    for a0 in a0s:
        print(f"== a0 = {a0:.2e}, target {TGT/1e3:.2f} km/s ==")
        sch, (v, dv, yr, revs) = optimize_at(a0)
        reach = v >= TGT * 0.999
        print(f"  OPTIMISED (fine): v_inf {v/1e3:.2f}  dv {dv/1e3:.3f} km/s  "
              f"{yr:.1f} yr  {revs:.1f} revs  {'REACH' if reach else 'STALL'}")
        print(f"  schedule: {sch}")


if __name__ == "__main__":
    main()
