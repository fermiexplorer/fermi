"""Audit 7 -- perihelion pumping (multi-revolution escape).

Independent checks — none of them call the engine and compare it to itself:
* An INDEPENDENT re-integration of the published bang-bang policy (own code,
  written from the docstring spec, 4x finer time steps) must reproduce the
  engine's endpoints, and must be step-converged (halving dt moves nothing).
* Conservation laws on the independent trajectory: the work-energy theorem
  (dE/dt = a_thrust . v — gravity does no net work on E = v^2/2 - mu/r) and
  exact rocket-equation mass closure (thrust set by power => m = m0 e^(-dv/ve)).
* Physical invariants: the thermal floor (no burn drives perihelion far below
  0.42 AU), the 4x power cap, and Oberth localisation (most of the post-latch
  energy is bought close to the Sun).
* The a0 failure threshold found by bisection with the independent integrator.
* The two-leg budget (pumped_departure_dv): the sqrt(mu/a) escape leg must
  bound the independently validated low-thrust spiral integration from above
  (conservative) within 15%, and the 2 km/s pumping tax must bracket the
  integrated dv - v_inf across the working a0 range.
* The numbers published on the web page must match the engine (drift guard).
"""

from __future__ import annotations

import math

from _util import check, close, rel_err

from fermi_sim import constants as c
from fermi_sim.departure import (
    perihelion_pumped_vinf,
    pumped_departure_dv,
    spiral_escape_dv,
)

RP_MIN_AU = 0.42
POWER_CAP = 4.0
ISP_S = 2800.0


def _indep_pump(a0, v_inf_target, dt_scale=1.0, max_yr=60.0, want_traj=False):
    """Independent integration of the published pumping policy. Written from the
    spec (docstring + page text), not from the engine source: RK4 in Cartesian,
    but a 4x finer, differently shaped step schedule (dt_scale=1), and its own
    bookkeeping. Returns (v_inf, dv, years, diag) where diag carries the
    conservation/invariant data the checks below consume.
    """
    mu, AU = c.MU_SUN, c.AU
    ve = ISP_S * c.G0
    target_E = 0.5 * v_inf_target**2
    x, y, vx, vy = AU, 0.0, 0.0, math.sqrt(mu / AU)
    m, t, dv = 1.0, 0.0, 0.0
    pumped_down = False
    work = 0.0            # integral of a_thrust . v dt  (work-energy audit)
    work_inner = 0.0      # ... the part done inside 0.8 AU after the latch
    work_post = 0.0       # ... all post-latch work
    r_min = AU
    amax_ratio = 0.0      # max (thrust accel * m / a0) — must stay <= POWER_CAP
    E0 = 0.5 * (vx * vx + vy * vy) - mu / math.hypot(x, y)
    max_t = max_yr * c.YEAR

    while t < max_t:
        r = math.hypot(x, y)
        v2 = vx * vx + vy * vy
        E = 0.5 * v2 - mu / r
        if E >= target_E:
            break
        h = x * vy - y * vx
        ecc = math.sqrt(max(0.0, 1.0 + 2.0 * E * h * h / (mu * mu)))
        p_sl = h * h / mu
        rp = p_sl / (1.0 + ecc)
        s = 1.0 if (x * vx + y * vy) >= 0.0 else -1.0
        nu = s * math.acos(max(-1.0, min(1.0, (p_sl / r - 1.0) / ecc))) if ecc > 1e-6 else 0.0
        if rp <= RP_MIN_AU * AU:
            pumped_down = True
        if not pumped_down:
            if ecc < 0.05:
                u = -1.0 if x > 0.0 else 0.0
            else:
                u = -1.0 if abs(abs(nu) - math.pi) < math.radians(60.0) else 0.0
        elif E < -3.0e7:
            u = +1.0 if abs(nu) < math.radians(70.0) else 0.0
        else:
            u = +1.0
        period = 2.0 * math.pi * math.sqrt(max(r, 0.1 * AU) ** 3 / mu)
        dt = dt_scale * min(max(150.0, 0.0005 * period), 1.25 * 86400.0)

        def acc(px, py, pvx, pvy):
            rr = math.hypot(px, py)
            vv = math.hypot(pvx, pvy) or 1.0
            am = u * a0 * min((AU / rr) ** 2, POWER_CAP) / m
            g = -mu / rr**3
            return g * px + am * pvx / vv, g * py + am * pvy / vv

        k1 = (vx, vy, *acc(x, y, vx, vy))
        k2 = (vx + 0.5 * dt * k1[2], vy + 0.5 * dt * k1[3],
              *acc(x + 0.5 * dt * k1[0], y + 0.5 * dt * k1[1],
                   vx + 0.5 * dt * k1[2], vy + 0.5 * dt * k1[3]))
        k3 = (vx + 0.5 * dt * k2[2], vy + 0.5 * dt * k2[3],
              *acc(x + 0.5 * dt * k2[0], y + 0.5 * dt * k2[1],
                   vx + 0.5 * dt * k2[2], vy + 0.5 * dt * k2[3]))
        k4 = (vx + dt * k3[2], vy + dt * k3[3],
              *acc(x + dt * k3[0], y + dt * k3[1], vx + dt * k3[2], vy + dt * k3[3]))
        if u:
            amag = a0 * min((AU / r) ** 2, POWER_CAP) / m
            vmag = math.sqrt(v2) or 1.0
            dv += amag * dt
            w = u * amag * vmag * dt          # tangential thrust: a.v = u*|a|*|v|
            work += w
            if pumped_down:
                work_post += w
                if r < 0.8 * AU:
                    work_inner += w
            amax_ratio = max(amax_ratio, amag * m / a0)
            m = max(0.05, m - (a0 * min((AU / r) ** 2, POWER_CAP) / ve) * dt)
        x += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        y += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        vx += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        vy += dt / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
        r_min = min(r_min, math.hypot(x, y))
        t += dt

    r = math.hypot(x, y)
    E = 0.5 * (vx * vx + vy * vy) - mu / r
    v_inf = math.sqrt(2.0 * E) if E > 0 else 0.0
    diag = {"E_gain": E - E0, "work": work, "work_post": work_post,
            "work_inner": work_inner, "m": m, "r_min": r_min,
            "amax_ratio": amax_ratio, "reached": E >= target_E}
    return v_inf, dv, t / c.YEAR, diag


def run() -> None:
    print("== Audit 7: perihelion pumping (multi-revolution escape) ==")
    tgt = 23.64e3
    a0_design = 2.5e-4

    # 1. Independent re-integration reproduces the engine endpoints.
    vi, dvi, yri, diag = _indep_pump(a0_design, tgt)
    ve_, dve, yre, _ = perihelion_pumped_vinf(a0_design, tgt)
    check("independent integrator reaches the cruise floor @ a0=2.5e-4",
          diag["reached"] and vi >= tgt, f"v_inf={vi/1e3:.2f} km/s")
    check("independent v_inf matches engine (<1%)", rel_err(vi, ve_) < 0.01,
          f"{vi/1e3:.2f} vs {ve_/1e3:.2f} km/s")
    check("independent dv matches engine (<3%)", rel_err(dvi, dve) < 0.03,
          f"{dvi/1e3:.2f} vs {dve/1e3:.2f} km/s")
    check("independent duration matches engine (<10%)", rel_err(yri, yre) < 0.10,
          f"{yri:.1f} vs {yre:.1f} yr")

    # 2. Step convergence: doubling the (already 4x finer) step moves nothing.
    vi2, dvi2, _, _ = _indep_pump(a0_design, tgt, dt_scale=2.0)
    check("independent integrator is step-converged (2x dt: <0.5%)",
          rel_err(vi, vi2) < 0.005 and rel_err(dvi, dvi2) < 0.005,
          f"v_inf {vi/1e3:.3f}->{vi2/1e3:.3f}, dv {dvi/1e3:.3f}->{dvi2/1e3:.3f}")

    # 3. Work-energy theorem: the orbital-energy gain must equal the thrust work
    #    (gravity contributes nothing to E = v^2/2 - mu/r).
    check("work-energy theorem closes (<0.5%)",
          rel_err(diag["E_gain"], diag["work"]) < 0.005,
          f"dE={diag['E_gain']:.4e} vs int(a.v)dt={diag['work']:.4e} J/kg")

    # 4. Rocket-equation closure: thrust follows power (not mass), so the mass
    #    fraction must satisfy m/m0 = exp(-dv/ve) — exact in the continuum; the
    #    per-step bookkeeping is first-order, so allow an O(dt) residual.
    check("rocket-equation mass closure (<5e-4)",
          rel_err(diag["m"], math.exp(-dvi / (ISP_S * c.G0))) < 5e-4,
          f"m={diag['m']:.6f} vs e^(-dv/ve)={math.exp(-dvi/(ISP_S*c.G0)):.6f}")

    # 5. Thermal floor: the trajectory must not dive far below the 0.42 AU cap
    #    (the latch fires on the osculating perihelion, so a small undershoot on
    #    the pass already in flight is expected — but not a deep one).
    check("thermal floor respected (min r > 0.35 AU, near 0.42)",
          0.35 * c.AU < diag["r_min"] <= 0.50 * c.AU,
          f"min r = {diag['r_min']/c.AU:.3f} AU")

    # 6. Power cap: thrust acceleration never exceeds 4x the 1-AU rating.
    check("4x perihelion power cap never exceeded",
          diag["amax_ratio"] <= POWER_CAP + 1e-9,
          f"max a*m/a0 = {diag['amax_ratio']:.3f}")

    # 7. Oberth localisation: the staircase must buy most of its energy close
    #    to the Sun — that is the entire point of pumping down first.
    frac = diag["work_inner"] / max(diag["work_post"], 1e-30)
    check("majority of post-latch energy bought inside 0.8 AU",
          frac > 0.5, f"{100*frac:.0f}% of post-latch thrust work")

    # 8. Failure threshold by bisection (independent integrator): the maneuver
    #    must die between 1.5e-4 (known-fail) and 2.5e-4 (known-pass), near the
    #    published a0 ~ 2.25e-4.
    lo, hi = 1.8e-4, 2.5e-4
    for _ in range(5):
        mid = 0.5 * (lo + hi)
        _, _, _, d = _indep_pump(mid, tgt, dt_scale=2.0)
        if d["reached"]:
            hi = mid
        else:
            lo = mid
    a0_star = 0.5 * (lo + hi)
    check("failure threshold near the published a0 ~ 2.25e-4 (+-15%)",
          abs(a0_star - 2.25e-4) < 0.15 * 2.25e-4, f"a0* = {a0_star:.2e} m/s^2")

    # 9. Two-leg budget — escape leg. sqrt(mu/a) must sit ON or ABOVE the
    #    independently validated low-thrust spiral integration (conservative),
    #    and within 15% of it.
    for name, alt, apo in (("LEO 400", 400.0, None), ("GTO 590x35786", 590.0, 35786.0)):
        r_p = c.R_EARTH + alt * 1e3
        r_a = c.R_EARTH + (apo if apo else alt) * 1e3
        leg = pumped_departure_dv(0.0, alt, apo, pump_tax=0.0)
        dv_int = spiral_escape_dv(c.MU_EARTH, r_p, 0.0, accel=5e-4, apogee_r=r_a)
        check(f"escape leg bounds the integrated spiral ({name})",
              dv_int <= leg <= 1.15 * dv_int,
              f"sqrt(mu/a)={leg/1e3:.2f} vs integrated {dv_int/1e3:.2f} km/s")

    # 10. Two-leg budget — pumping tax. dv - v_inf from the independent
    #     integrator must be bracketed by the 2 km/s tax within [-0.5, +1.0]
    #     km/s across the working a0 range (the budget is first-order).
    for a0 in (2.5e-4, 5.0e-4):
        v_, dv_, _, d = _indep_pump(a0, tgt, dt_scale=2.0)
        tax = dv_ - v_
        check(f"pumping tax ~2 km/s holds @ a0={a0:.1e}",
              d["reached"] and 1.5e3 <= tax <= 3.0e3, f"dv - v_inf = {tax/1e3:.2f} km/s")

    # 11. Published-numbers drift guard: the values quoted in the page table
    #     must still be what the engine produces.
    v_eng, dv_eng, yr_eng, revs_eng = perihelion_pumped_vinf(2.5e-4, tgt)
    check("page table row @ 2.5e-4 (23.66 km/s, dv 25.6, 9.6 yr, 4.9 revs)",
          close(v_eng / 1e3, 23.66, abs_=0.01) and close(dv_eng / 1e3, 25.6, abs_=0.05)
          and close(yr_eng, 9.6, abs_=0.05) and close(revs_eng, 4.9, abs_=0.05),
          f"{v_eng/1e3:.2f} km/s, dv {dv_eng/1e3:.1f}, {yr_eng:.1f} yr, {revs_eng:.1f} revs")
    v_lo, _, _, _ = perihelion_pumped_vinf(1.5e-4, tgt)
    check("page table row @ 1.5e-4 (short: 15.5 km/s)",
          v_lo < tgt and close(v_lo / 1e3, 15.5, abs_=0.1), f"{v_lo/1e3:.2f} km/s")
    v_hi, _, yr_hi, _ = perihelion_pumped_vinf(5.0e-4, tgt)
    check("page table row @ 5e-4 (23.8 km/s, 6.3 yr)",
          close(v_hi / 1e3, 23.8, abs_=0.05) and close(yr_hi, 6.3, abs_=0.05),
          f"{v_hi/1e3:.2f} km/s, {yr_hi:.1f} yr")


if __name__ == "__main__":
    from _util import summary
    run()
    raise SystemExit(summary())
