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
* The 3-D plane tax (issue #9): planar embedding, an independent own-code 3-D
  re-integration of the cap-model 2.48-deg point (the point PSI's final
  assessment measures with a third implementation), bake replay + step
  convergence of the thermal knot, the conservative far-field bound, and the
  arrival-epoch basin the rounded corner produces.
"""

from __future__ import annotations

import math

from _util import check, close, rel_err

from fermi_sim import constants as c
from fermi_sim.departure import (
    perihelion_pumped_vinf,
    plane_tax_for,
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


def _phase_split(a0, v_inf_target, isp_s=ISP_S):
    """Independent re-integration returning the phase split (retrograde pump-down revs to
    the 0.42 AU latch, prograde perihelion-pass count, dv by thrust direction). Written
    from the policy spec, standalone (does NOT call departure.py)."""
    mu, AU = c.MU_SUN, c.AU
    ve = isp_s * c.G0
    target_E = 0.5 * v_inf_target ** 2
    x, y, vx, vy = AU, 0.0, 0.0, math.sqrt(mu / AU)
    m, t, ang_prev, revs = 1.0, 0.0, 0.0, 0.0
    pumped_down, revs_at_latch, passes, prev_rdot = False, None, 0, None
    dv_retro = dv_pro = 0.0
    while t < 60.0 * c.YEAR:
        r = math.hypot(x, y)
        E = 0.5 * (vx * vx + vy * vy) - mu / r
        if E >= target_E:
            break
        h = x * vy - y * vx
        ecc = math.sqrt(max(0.0, 1.0 + 2.0 * E * h * h / (mu * mu)))
        p_sl = h * h / mu
        rp = p_sl / (1.0 + ecc)
        rdot = x * vx + y * vy
        s = 1.0 if rdot >= 0.0 else -1.0
        nu = s * math.acos(max(-1.0, min(1.0, (p_sl / r - 1.0) / ecc))) if ecc > 1e-6 else 0.0
        if rp <= RP_MIN_AU * AU and not pumped_down:
            pumped_down, revs_at_latch = True, revs
        if not pumped_down:
            td = (-1.0 if x > 0.0 else 0.0) if ecc < 0.05 else (-1.0 if abs(abs(nu) - math.pi) < math.radians(60.0) else 0.0)
        elif E < -3.0e7:
            td = 1.0 if abs(nu) < math.radians(70.0) else 0.0
        else:
            td = 1.0
        if pumped_down and prev_rdot is not None and prev_rdot < 0 and rdot >= 0:
            passes += 1
        prev_rdot = rdot
        amag = (a0 * min((AU / r) ** 2, POWER_CAP) / m) if td else 0.0
        period = 2.0 * math.pi * math.sqrt(max(r, 0.1 * AU) ** 3 / mu)
        dt = min(max(600.0, 0.002 * period), 5.0 * 86400.0)

        def deriv(st):
            X, Y, VX, VY = st
            rr = math.hypot(X, Y)
            vv = math.hypot(VX, VY) or 1.0
            am = (a0 * min((AU / rr) ** 2, POWER_CAP) / m * td) if td else 0.0
            g = -mu / rr ** 3
            return (VX, VY, g * X + am * VX / vv, g * Y + am * VY / vv)

        st = (x, y, vx, vy)
        k1 = deriv(st)
        k2 = deriv(tuple(st[i] + 0.5 * dt * k1[i] for i in range(4)))
        k3 = deriv(tuple(st[i] + 0.5 * dt * k2[i] for i in range(4)))
        k4 = deriv(tuple(st[i] + dt * k3[i] for i in range(4)))
        x += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        y += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        vx += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        vy += dt / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
        if td:
            step = amag * dt
            if td < 0:
                dv_retro += step
            else:
                dv_pro += step
            m = max(0.05, m - (a0 * min((AU / r) ** 2, POWER_CAP) / ve) * dt)
        ang = math.atan2(y, x)
        d = ang - ang_prev
        d = (d + math.pi) % (2 * math.pi) - math.pi
        revs += abs(d) / (2 * math.pi)
        ang_prev = ang
        t += dt
    return {"retro_revs": revs_at_latch or 0.0, "passes": passes,
            "dv_retro": dv_retro, "dv_pro": dv_pro}


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

    # 8. The lower edge of the CONTIGUOUS working region, by bisection with the
    #    independent integrator. NOTE (multi-model adversarial audit): success is
    #    NOT monotonic in a0 — a phasing-dependent success island exists near
    #    1.75-1.88e-4 with strand bands at 1.9-2.2e-4 and ~2.9-3.1e-4 — so the
    #    bracket must start from a verified strand INSIDE the band (2.2e-4), not
    #    from the island region.
    _, _, _, d_band = _indep_pump(2.2e-4, tgt, dt_scale=2.0)
    check("2.2e-4 sits in the strand band (bracket premise)", not d_band["reached"])
    lo, hi = 2.2e-4, 2.5e-4
    for _ in range(5):
        mid = 0.5 * (lo + hi)
        _, _, _, d = _indep_pump(mid, tgt, dt_scale=2.0)
        if d["reached"]:
            hi = mid
        else:
            lo = mid
    a0_star = 0.5 * (lo + hi)
    check("contiguous-region edge near the published a0 ~ 2.24e-4 (+-10%)",
          abs(a0_star - 2.24e-4) < 0.10 * 2.24e-4, f"a0* = {a0_star:.2e} m/s^2")
    # ...and the island really exists (published fine print): 1.8e-4 reaches.
    _, _, yr_isl, d_isl = _indep_pump(1.8e-4, tgt, dt_scale=2.0)
    check("success island below the edge exists (1.8e-4 reaches, non-monotonic)",
          d_isl["reached"], f"reached in {yr_isl:.0f} yr")

    # 9. Two-leg budget — escape leg. sqrt(mu/a) must sit ON or ABOVE the
    #    independently validated low-thrust spiral integration (conservative),
    #    and within 15% of it.
    for name, alt, apo in (("LEO 400", 400.0, None), ("GTO 590x35786", 590.0, 35786.0)):
        r_p = c.R_EARTH + alt * 1e3
        r_a = c.R_EARTH + (apo if apo else alt) * 1e3
        # compute the escape leg INDEPENDENTLY (sqrt(mu/a) from first principles) rather than
        # calling the budget with zeroed args — which the corridor guard now rightly refuses
        leg = math.sqrt(c.MU_EARTH / (0.5 * (r_p + r_a)))
        dv_int = spiral_escape_dv(c.MU_EARTH, r_p, 0.0, accel=5e-4, apogee_r=r_a)
        check(f"escape leg bounds the integrated spiral ({name})",
              dv_int <= leg <= 1.15 * dv_int,
              f"sqrt(mu/a)={leg/1e3:.2f} vs integrated {dv_int/1e3:.2f} km/s")

    # 9b. Two-leg budget — plane change. Since issue #9 the out-of-plane aim is charged
    #     by the DERIVED 3-D steering curve (plane_tax_for): the budget difference must
    #     equal the curve exactly, sit BELOW the old conservative bound v_inf*|sin(beta)|,
    #     and still be a multi-km/s charge at the steep 58-kyr aim (~3.6 km/s at 10.1 deg).
    d0 = pumped_departure_dv(23.64e3, 0.0, 400.0)
    d_tilt = pumped_departure_dv(23.64e3, -10.1, 400.0)
    expect_plane = plane_tax_for(23.64e3, -10.1)
    naive_plane = 23.64e3 * abs(math.sin(math.radians(10.1)))
    check("budget charges the DERIVED plane tax (58 kyr aim ~3.6 km/s, below the 4.1 bound)",
          rel_err(d_tilt - d0, expect_plane) < 1e-12
          and 3.0e3 < expect_plane < naive_plane,
          f"{(d_tilt-d0)/1e3:.2f} km/s at 10.1 deg (bound {naive_plane/1e3:.2f})")

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

    # 12. VALIDATED-DESIGN-PROFILE pins. Builds 133-135 fly every pumped campaign at
    #     a0_eff = min(vehicle a0, PUMP_DESIGN_A0), Isp PUMP_DESIGN_ISP. A silent edit to
    #     either constant would drift every consumer (JS mirror, page gate, run_analysis)
    #     while the parity audit stays green (it re-dumps from the same constant), so pin
    #     the constants and the function's default Isp against them explicitly.
    check("PUMP_DESIGN_A0 constant is 2.5e-4 m/s^2", c.PUMP_DESIGN_A0 == 2.5e-4, f"{c.PUMP_DESIGN_A0:.2e}")
    check("PUMP_DESIGN_ISP constant is 2800 s", c.PUMP_DESIGN_ISP == 2800.0, f"{c.PUMP_DESIGN_ISP:.0f}")
    check("perihelion_pumped_vinf default Isp == PUMP_DESIGN_ISP (gate/policy lockstep)",
          ISP_S == c.PUMP_DESIGN_ISP, f"module ISP_S={ISP_S}")

    # 13. NON-MONOTONICITY is load-bearing (the 'gate by integration, not a threshold'
    #     claim): a success island must exist BELOW the contiguous edge, and a stall band
    #     must exist ABOVE the design point. If the policy ever became monotone these pin
    #     the page's fine print to reality.
    v_isl, _, _, _ = perihelion_pumped_vinf(1.8e-4, tgt)
    check("success island below the edge: 1.8e-4 reaches (non-monotone)", v_isl >= tgt * 0.999,
          f"{v_isl/1e3:.2f} km/s")
    v_stall, _, _, _ = perihelion_pumped_vinf(3.0e-4, tgt)
    check("stall band above the design point: 3.0e-4 strands (non-monotone)", v_stall < tgt,
          f"{v_stall/1e3:.2f} km/s")

    # 13b. Power-CAP non-monotonicity (pins the page's caveat: the closure is non-monotone in the
    #      delivered concentration exactly as it is in a0/Isp — it reaches at 2.0x/2.5x/3.5x/4.0x but
    #      STRANDS at 1.5x/3.0x/3.25x and at the physical uncapped ~5.67x). Guards against a future
    #      "halving the cap always survives" regression, and keeps the 4x figure honest as a validated
    #      working point, not a smooth floor. (Regression drift guard, like the page-table-row pins.)
    def _reach(cap):
        v, _, yr, _ = perihelion_pumped_vinf(a0_design, tgt, ISP_S, RP_MIN_AU, cap, 200.0)
        return v >= tgt * 0.999
    reach_caps = [c_ for c_ in (2.0, 2.5, 3.5, 4.0) if _reach(c_)]
    stall_caps = [c_ for c_ in (1.5, 3.0, 3.25, 5.67) if not _reach(c_)]
    check("power cap is non-monotone: 2.0/2.5/3.5/4.0x reach, 1.5/3.0/3.25/5.67x stall",
          len(reach_caps) == 4 and len(stall_caps) == 4,
          f"reach={reach_caps}, stall={stall_caps}")

    # 13c. v_inf-DEPENDENT tax model (issues #3/#4): the budget prices targets through TWO
    #      schedule tables — the anchored-optimised default ([8, 26] km/s, negative past ~23:
    #      the Oberth-efficient campaign spends less than the v_inf it buys) and the bang-bang
    #      cross-check ([8, 29] km/s, anchored 2.0 km/s at the corridor). Both refuse below 8.
    from fermi_sim.departure import pump_tax_for
    try:
        pump_tax_for(7.0e3)
        guard_low = False
    except ValueError:
        guard_low = True
    check("pump tax refuses v_inf below the swept range (8 km/s, both schedules)",
          guard_low, "ValueError raised at 7 km/s")
    try:
        pump_tax_for(27.0e3)          # optimised table ends at 26 — must refuse, not extrapolate
        guard_hi = False
    except ValueError:
        guard_hi = True
    check("optimised tax refuses v_inf above its swept range (26 km/s)",
          guard_hi, "ValueError raised at 27 km/s")
    check("bang-bang anchor is pinned to the shipped calibration (tax_bb(23.64) = 2.000 km/s)",
          abs(pump_tax_for(23.64e3, "bangbang") - 2000.0) < 1e-9,
          f"{pump_tax_for(23.64e3, 'bangbang'):.1f} m/s")
    check("cap-model optimised anchor is negative (Oberth: campaign dv < v_inf bought): -0.509",
          abs(pump_tax_for(23.64e3, "optimized") - (-509.0)) < 1e-9,
          f"{pump_tax_for(23.64e3, 'optimized'):.1f} m/s")
    # the alpha2-Lib case that the old flat tax mispriced (34.7 vs integrated ~41.0) prices
    # correctly through the closed form under the BANG-BANG tax it was integrated with.
    # The historical 41.0 record carries the FAR-FIELD plane change (the budget's pricing
    # when it was integrated); reconstruct that pricing explicitly, since the budget now
    # charges the cheaper derived curve (issue #9 — ~0.3 km/s less at this 47-deg tilt).
    alib_bb = pumped_departure_dv(14.5e3, -47.0, 400.0,
                                  pump_tax=pump_tax_for(14.5e3, "bangbang"))
    alib_naive = (alib_bb - plane_tax_for(14.5e3, -47.0)
                  + 14.5e3 * math.sin(math.radians(47.0)))
    check("closed-form budget reproduces the integrated alpha2-Lib total (~41.0 km/s, "
          "bang-bang tax + far-field plane pricing)",
          abs(alib_naive - 41.0e3) < 0.25e3, f"{alib_naive/1e3:.2f} km/s")
    check("optimised schedule prices alpha2-Lib below the bang-bang total",
          pumped_departure_dv(14.5e3, -47.0, 400.0) < alib_bb,
          f"{pumped_departure_dv(14.5e3, -47.0, 400.0)/1e3:.2f} < {alib_bb/1e3:.2f} km/s")
    # fit-vs-integrator at OFF-knot targets (interp must track the campaign to < 0.3 km/s)
    for v_t in (12.5e3, 20.5e3, 27.5e3):
        vi_t, dv_t, _, _ = perihelion_pumped_vinf(a0_design, v_t, max_yr=200.0)
        err = abs(pump_tax_for(v_t, "bangbang") - (dv_t - vi_t))
        check(f"bang-bang tax table tracks the integrator at v_inf {v_t/1e3:.1f} km/s (<0.3 km/s)",
              err < 300.0, f"err {err:.0f} m/s")

    # 13d. OPTIMISED schedule (issue #4): the shipped default campaign is the baked 12-yr
    #      custody optimum at the design a0. Re-integrate it here (fine dt, event-located
    #      switches) and pin the baked tuple, energy bookkeeping, and the a0-grid closures
    #      that the bang-bang policy failed (1.9e-4 strand band, 3.0e-4 stall window).
    from fermi_sim.pump_schedule import OPTIMIZED_SCHEDULES, DESIGN_A0, scheduled_pumped_vinf
    sch_d, baked_d = OPTIMIZED_SCHEDULES[DESIGN_A0]
    v_o, dv_o, yr_o, rv_o, diag_o = scheduled_pumped_vinf(
        DESIGN_A0, baked_d[0], sch_d, return_diag=True)
    check("optimised anchor replay reaches the target (design a0, fine dt)",
          v_o >= baked_d[0] * 0.999, f"{v_o/1e3:.3f} km/s")
    check("optimised anchor replay reproduces the baked dv (23.136 km/s)",
          abs(dv_o - baked_d[1]) < 25.0, f"{dv_o:.1f} vs baked {baked_d[1]:.1f} m/s")
    check("optimised anchor replay reproduces the baked custody (~12.0 yr) and revs (~5.9)",
          abs(yr_o - baked_d[2]) < 0.15 and abs(rv_o - baked_d[3]) < 0.15,
          f"{yr_o:.2f} yr, {rv_o:.2f} revs")
    check("optimised campaign beats the bang-bang policy on dv (23.1 < 25.6 km/s)",
          dv_o < 25.0e3, f"{dv_o/1e3:.2f} km/s vs bang-bang 25.63")
    check("optimised replay overhead matches the baked tax anchor (-0.509 km/s, <30 m/s)",
          abs((dv_o - v_o) - (-509.0)) < 30.0, f"{dv_o - v_o:.1f} m/s")
    # energy bookkeeping: thrust work (a.v dt, first-order) must equal the specific-energy
    # gain — the only non-conservative force is the thrust (work-energy theorem)
    check("optimised campaign conserves energy: thrust work == specific-energy gain (<1%)",
          abs(diag_o["work"] - diag_o["E_gain"]) / diag_o["E_gain"] < 0.01,
          f"work {diag_o['work']:.4e} vs dE {diag_o['E_gain']:.4e} J/kg")
    check("optimised campaign respects the 0.42 AU thermal floor (min r >= 0.41 AU)",
          diag_o["min_r_au"] >= 0.41, f"min r {diag_o['min_r_au']:.3f} AU")
    # the a0-grid closures the bang-bang policy failed: 1.9e-4 (old strand band, coarse-dt
    # drift guard — fine-dt REACH was verified when the table was baked) and 3.0e-4 (old
    # stall window, fine dt)
    sch_19, baked_19 = OPTIMIZED_SCHEDULES[1.9e-4]
    v_19, _, _, _ = scheduled_pumped_vinf(1.9e-4, baked_19[0], sch_19, _dt_scale=3)
    check("optimised schedule closes the old 1.9e-4 strand band (coarse-dt replay)",
          v_19 >= baked_19[0] * 0.999, f"{v_19/1e3:.2f} km/s")
    sch_30, baked_30 = OPTIMIZED_SCHEDULES[3.0e-4]
    v_30, _, _, _ = scheduled_pumped_vinf(3.0e-4, baked_30[0], sch_30)
    check("optimised schedule closes the old 3.0e-4 stall window (fine-dt replay)",
          v_30 >= baked_30[0] * 0.999, f"{v_30/1e3:.2f} km/s")

    # 13e. DERIVED THERMAL power model (issue #5): the shipped default replaces the assumed
    #      4x cap with cap_eff(r) from the array's own energy balance. Verify the balance by
    #      an INDEPENDENT bisection solve (not the module's fixed-point), pin the derived
    #      curve, the Si sensitivity collapse, the design-point closure under the re-optimised
    #      anchored schedule, and the motivating fact that the fixed geometries strand.
    from fermi_sim.thermal import (GAAS, SI, SOLAR_CONST_1AU, SIGMA_SB,
                                   cap_eff, cell_temperature)
    from fermi_sim.pump_schedule import ANCHORED_THERMAL, OPTIMIZED_SCHEDULES_THERMAL

    def _t_bisect(r_au, m):
        # independent solve: f(T) = (alpha - eta(T))*S - eps*sigma*T^4, bisected on [100, 2000]
        s_flux = SOLAR_CONST_1AU / (r_au * r_au)
        eps = m.eps_front + m.eps_back

        def f(t):
            eta = max(0.0, m.eta_ref * (1.0 - m.beta * (t - m.t_ref)))
            return (m.alpha_s - eta) * s_flux - eps * SIGMA_SB * t ** 4

        lo, hi = 100.0, 2000.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if f(mid) > 0.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    t_ind = _t_bisect(0.42, GAAS)
    t_mod = cell_temperature(0.42)
    check("thermal balance closes: independent bisection matches the module solve (<0.1 K)",
          abs(t_ind - t_mod) < 0.1, f"{t_ind:.3f} vs {t_mod:.3f} K")
    check("derived cap is 1 at 1 AU by construction and ~3.54 at the 0.42 AU floor",
          cap_eff(1.0) == 1.0 and abs(cap_eff(0.42) - 3.536) < 0.005,
          f"cap_eff(1)={cap_eff(1.0):.6f}, cap_eff(0.42)={cap_eff(0.42):.4f}")
    check("Si sensitivity case COLLAPSES at the floor (0.45%/K kills the harvest)",
          cap_eff(0.42, SI) < 0.2, f"cap_eff(0.42, Si) = {cap_eff(0.42, SI):.3f}")
    # the motivating measurement: under the derived curve the FIXED geometries strand at
    # the design a0 (bang-bang reaches only ~20 km/s) — re-optimisation is what closes it
    v_bbth, _, _, _ = perihelion_pumped_vinf(a0_design, tgt, power_model="thermal")
    check("bang-bang geometry STRANDS at the design a0 under the derived thermal cap",
          v_bbth < tgt * 0.99, f"{v_bbth/1e3:.2f} km/s")
    sch_t, baked_t = OPTIMIZED_SCHEDULES_THERMAL[a0_design]
    v_t, dv_t2, yr_t, rv_t, diag_t = scheduled_pumped_vinf(
        a0_design, tgt, sch_t, power_model="thermal", return_diag=True)
    check("re-optimised anchored schedule CLOSES the design point under thermal (12-yr custody)",
          v_t >= tgt * 0.999 and abs(yr_t - 12.0) < 0.15, f"v {v_t/1e3:.3f}, {yr_t:.2f} yr")
    check("thermal anchor replay reproduces the baked campaign (dv 24.437, ~7.9 revs)",
          abs(dv_t2 - 24436.6) < 25.0 and abs(rv_t - 7.886) < 0.15,
          f"dv {dv_t2:.1f}, {rv_t:.2f} revs")
    check("thermal derate costs ~+1.3 km/s vs the idealised 4x cap at the same custody",
          23136.0 < dv_t2 < 25000.0 and dv_t2 - 23136.0 > 1000.0,
          f"{dv_t2/1e3:.2f} vs 23.14 km/s")
    check("thermal replay overhead matches the baked tax anchor (+0.785 km/s, <30 m/s)",
          abs((dv_t2 - v_t) - 785.3) < 30.0, f"{dv_t2 - v_t:.1f} m/s")
    check("thermal campaign conserves energy: thrust work == specific-energy gain (<1%)",
          abs(diag_t["work"] - diag_t["E_gain"]) / diag_t["E_gain"] < 0.01,
          f"work {diag_t['work']:.4e} vs dE {diag_t['E_gain']:.4e} J/kg")
    check("thermal campaign respects the 0.42 AU floor (min r >= 0.41 AU)",
          diag_t["min_r_au"] >= 0.41, f"min r {diag_t['min_r_au']:.3f} AU")
    check("thermal budget anchor: escape + v_inf + tax = 32.10 km/s (tax +785.3 at 23.64)",
          abs(pumped_departure_dv(23.64e3, 0.0, 400.0) - 32097.9) < 1.0
          and abs(pump_tax_for(23.64e3) - 785.3) < 1e-9,
          f"{pumped_departure_dv(23.64e3, 0.0, 400.0):.1f} m/s")
    # the old bang-bang strand band (1.9e-4) closes under its per-a0 thermal schedule too
    sch_19t, baked_19t = OPTIMIZED_SCHEDULES_THERMAL[1.9e-4]
    v_19t, _, _, _ = scheduled_pumped_vinf(1.9e-4, tgt, sch_19t, power_model="thermal")
    check("per-a0 thermal schedule closes the 1.9e-4 strand band (fine replay)",
          v_19t >= tgt * 0.999, f"{v_19t/1e3:.2f} km/s")

    # 13f. INDEPENDENCE BRIDGE + campaign-table guards (deep-audit b154-167 findings).
    #      (i) The scheduled integrator's physics is tied to the INDEPENDENTLY re-integrated
    #      path: run scheduled_pumped_vinf with the BANG_BANG geometry under the cap model
    #      and require it to agree with perihelion_pumped_vinf (whose physics checks 1-10
    #      above re-derive with a separate integrator, work-energy closure and step
    #      convergence). The two implementations differ only in event location (bisected vs
    #      per-step), measured at ~0.1% dv — so agreement here transfers the independent
    #      validation onto the scheduled code path that prices the shipped default.
    from fermi_sim.pump_schedule import BANG_BANG, campaign_overhead_curve, TAX_OPT_THERMAL_TABLE
    v_sb, dv_sb, yr_sb, _ = scheduled_pumped_vinf(a0_design, tgt, BANG_BANG)
    v_bb, dv_bb, yr_bb, _ = perihelion_pumped_vinf(a0_design, tgt)
    check("independence bridge: scheduled(BANG_BANG geometry) matches the validated bang-bang "
          "integrator (<0.5% dv, <0.2% v_inf)",
          abs(dv_sb - dv_bb) / dv_bb < 5e-3 and abs(v_sb - v_bb) / v_bb < 2e-3,
          f"dv {dv_sb:.0f} vs {dv_bb:.0f}, v {v_sb:.0f} vs {v_bb:.0f}")
    #      (ii) The baked thermal tax/campaign knots must reproduce from a FRESH
    #      campaign_overhead_curve integration (they were previously baked records with no
    #      replay guard). Same code path — a drift/tamper guard, not an independent check.
    from fermi_sim.pump_schedule import ANCHORED_THERMAL, OPT_CAMPAIGN_THERMAL_TABLE
    knots = [15000.0, 20000.0, 23640.0, 25000.0]
    fresh = {row[0]: row for row in campaign_overhead_curve(
        a0_design, ANCHORED_THERMAL, knots, power_model="thermal")}
    tax_map = dict(TAX_OPT_THERMAL_TABLE)
    ok_tax = all(abs(fresh[k][1] - tax_map[k]) < 1.0 for k in knots if k in fresh)
    check("baked thermal tax knots reproduce from a fresh campaign integration (<1 m/s)",
          len(fresh) == len(knots) and ok_tax,
          str({k: (round(fresh[k][1], 1), tax_map[k]) for k in knots if k in fresh}))
    camp_map = {row[0]: row for row in OPT_CAMPAIGN_THERMAL_TABLE}
    ok_camp = all(abs(fresh[k][2] - camp_map[k][2]) < 0.01
                  and abs(fresh[k][3] - camp_map[k][3]) < 0.01
                  for k in (23640.0, 25000.0))
    check("baked thermal campaign years/revs knots reproduce from the fresh integration",
          ok_camp, str({k: (round(fresh[k][2], 3), camp_map[k][2]) for k in (23640.0, 25000.0)}))

    # 13g. DERIVED 3-D PLANE TAX (issue #9). The pumped budget's out-of-plane charge
    #      comes from the 3-D campaign integration (scheduled_pumped_vinf_3d +
    #      PLANE_TAX_THERMAL_TABLE, derived by tools/derive_plane_tax.py). Checks:
    #      (i) planar embedding — the 3-D integrator at beta=0 must REPRODUCE the planar
    #          integrator (same trajectory, dv to <0.01 m/s);
    #      (ii) an INDEPENDENT own-code 3-D re-integration (this file, written from the
    #          docstring spec, own step schedule, own osculating/steering bookkeeping,
    #          cap power model) must reproduce the engine's cap-model tilt cost at the
    #          2.48-deg point — the same point PSI's final assessment measures at
    #          578 m/s with a third, unrelated implementation;
    #      (iii) the baked 2.48-deg THERMAL knot must replay from the engine at the
    #          derivation's dt (a bake/tamper guard) and be step-converged;
    #      (iv) the derived curve is bounded above by the far-field v_inf*|sin(beta)|
    #          everywhere and is ~quadratic near zero (the rounded corner);
    #      (v) the arrival-epoch consequence: the pumped-budget optimum sits in a
    #          shallow basin at ~77.8 kyr, the in-plane crossing aim costs <60 m/s
    #          more, and the early-arrival branch stays >2.5 km/s out.
    from fermi_sim.pump_schedule import (OPTIMIZED_SCHEDULES, PLANE_TAX_THERMAL_TABLE,
                                         scheduled_pumped_vinf_3d)
    # (i) planar embedding
    v3e, dv3e, yr3e, rev3e, lat3e = scheduled_pumped_vinf_3d(
        a0_design, tgt, 0.0, ANCHORED_THERMAL, power_model="thermal")
    v2e, dv2e, yr2e, rev2e = scheduled_pumped_vinf(
        a0_design, tgt, ANCHORED_THERMAL, power_model="thermal")
    check("3-D integrator at beta=0 embeds the planar integrator exactly (<0.01 m/s dv)",
          abs(dv3e - dv2e) < 0.01 and abs(v3e - v2e) < 0.01 and abs(yr3e - yr2e) < 1e-6,
          f"dv {dv3e:.3f} vs {dv2e:.3f}")

    # (ii) independent own-code 3-D re-integration, cap model, 2.48-deg point
    def _indep_plane_cap(beta_deg, gamma_deg, sch):
        mu, AU = c.MU_SUN, c.AU
        ve = ISP_S * c.G0
        v_t = tgt
        target_E = 0.5 * v_t ** 2
        tang = math.tan(math.radians(gamma_deg))
        lat_t = -beta_deg

        def osc(x, y, z, vx, vy, vz):
            r = math.hypot(x, y, z)
            v2 = vx * vx + vy * vy + vz * vz
            E = 0.5 * v2 - mu / r
            hx, hy, hz = y * vz - z * vy, z * vx - x * vz, x * vy - y * vx
            h2 = hx * hx + hy * hy + hz * hz
            ecc = math.sqrt(max(0.0, 1.0 + 2.0 * E * h2 / (mu * mu)))
            p = h2 / mu
            rp = p / (1.0 + ecc) if p > 0 else 0.0
            s = 1.0 if (x * vx + y * vy + z * vz) >= 0.0 else -1.0
            nu = (s * math.acos(max(-1.0, min(1.0, (p / r - 1.0) / ecc)))
                  if ecc > 1e-6 else 0.0)
            return r, E, ecc, rp, nu

        def asym_lat(x, y, z, vx, vy, vz):
            r = math.hypot(x, y, z)
            v2 = vx * vx + vy * vy + vz * vz
            rv = x * vx + y * vy + z * vz
            ex = ((v2 - mu / r) * x - rv * vx) / mu
            ey = ((v2 - mu / r) * y - rv * vy) / mu
            ez = ((v2 - mu / r) * z - rv * vz) / mu
            e = math.hypot(ex, ey, ez)
            if e <= 1.0:
                return None
            hx, hy, hz = y * vz - z * vy, z * vx - x * vz, x * vy - y * vx
            h = math.hypot(hx, hy, hz)
            exh, eyh, ezh = ex / e, ey / e, ez / e
            hxh, hyh, hzh = hx / h, hy / h, hz / h
            pz = hxh * eyh - hyh * exh
            nu_inf = math.acos(max(-1.0, min(1.0, -1.0 / e)))
            uz = math.cos(nu_inf) * ezh + math.sin(nu_inf) * pz
            return math.degrees(math.asin(max(-1.0, min(1.0, uz))))

        x, y, z = AU, 0.0, 0.0
        vx, vy, vz = 0.0, math.sqrt(mu / AU), 0.0
        m, t, dv = 1.0, 0.0, 0.0
        latched = False
        vend = None
        while t < 30.0 * c.YEAR:
            r, E, ecc, rp, nu = osc(x, y, z, vx, vy, vz)
            lat = asym_lat(x, y, z, vx, vy, vz) if E > 0.0 else None
            tilt_needed = beta_deg > 0.0 and (lat is None or lat > lat_t)
            if E >= target_E and not tilt_needed:
                vend = math.sqrt(2.0 * E)
                break
            if not latched and rp <= sch.rp_latch * AU:
                latched = True
            if not latched:
                if ecc < 0.05:
                    u = -1.0 if x > 0.0 else 0.0
                else:
                    u = -1.0 if abs(abs(nu) - math.pi) < math.radians(sch.th_retro) else 0.0
            elif E < sch.e_guard:
                u = +1.0 if abs(nu) < math.radians(sch.th_pro) else 0.0
            else:
                u = +1.0
            purez = E >= target_E and tilt_needed
            if purez:
                u = +1.0
            period = 2.0 * math.pi * math.sqrt(max(r, 0.1 * AU) ** 3 / mu)
            dt = min(max(150.0, 5.0e-4 * period), 1.25 * 86400.0)

            def acc(px, py, pz_, pvx, pvy, pvz, pm):
                rr = math.hypot(px, py, pz_)
                vv = math.hypot(pvx, pvy, pvz) or 1.0
                am = u * a0_design * min((AU / rr) ** 2, POWER_CAP) / pm
                if purez:
                    ux, uy, uz = 0.0, 0.0, -1.0
                    am = abs(am)
                    tx, ty, tz = 0.0, 0.0, -am
                else:
                    ux, uy, uz = pvx / vv, pvy / vv, pvz / vv
                    if u > 0.0 and tilt_needed and E > 0.0 and lat is not None:
                        # steering only ever fires on the hyperbolic (finisher) leg, u=+1
                        uz2 = uz - tang
                        un = math.sqrt(ux * ux + uy * uy + uz2 * uz2)
                        tx, ty, tz = am * ux / un, am * uy / un, am * uz2 / un
                    else:
                        tx, ty, tz = am * ux, am * uy, am * uz
                g = -mu / rr ** 3
                return g * px + tx, g * py + ty, g * pz_ + tz
            s0 = (x, y, z, vx, vy, vz)
            k1 = (vx, vy, vz, *acc(x, y, z, vx, vy, vz, m))
            k2s = tuple(s0[i] + 0.5 * dt * k1[i] for i in range(6))
            k2 = (k2s[3], k2s[4], k2s[5], *acc(*k2s, m))
            k3s = tuple(s0[i] + 0.5 * dt * k2[i] for i in range(6))
            k3 = (k3s[3], k3s[4], k3s[5], *acc(*k3s, m))
            k4s = tuple(s0[i] + dt * k3[i] for i in range(6))
            k4 = (k4s[3], k4s[4], k4s[5], *acc(*k4s, m))
            x, y, z, vx, vy, vz = (s0[i] + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
                                   for i in range(6))
            if u:
                pf_r = a0_design * min((AU / r) ** 2, POWER_CAP)
                dv += pf_r / m * dt
                m = max(m - pf_r / ve * dt, 0.05)
            t += dt
        if vend is None:
            r, E, _, _, _ = osc(x, y, z, vx, vy, vz)
            vend = math.sqrt(2.0 * E) if E > 0 else 0.0
        return vend, dv, asym_lat(x, y, z, vx, vy, vz)

    sch_cap = OPTIMIZED_SCHEDULES[2.5e-4][0]
    vA, dvA, latA = _indep_plane_cap(0.0, 0.0, sch_cap)
    vB, dvB, latB = _indep_plane_cap(2.48, 22.8, sch_cap)
    cost_indep = (dvB - dvA) - 0.64 * (vB - vA)
    check("independent 3-D re-integration prices the cap-model 2.48-deg tilt near the "
          "engine's 606 m/s (and PSI's measured 578)",
          latB is not None and abs(latB + 2.48) < 0.10
          and abs(cost_indep - 606.1) < 90.0 and abs(cost_indep - 578.0) < 160.0,
          f"indep {cost_indep:.0f} m/s, lat {latB}")

    # (iii) bake replay + step convergence of the thermal 2.48-deg knot
    def _knot(dts):
        _, dv0k, _, _, _ = scheduled_pumped_vinf_3d(
            a0_design, tgt, 0.0, ANCHORED_THERMAL, power_model="thermal", _dt_scale=dts)
        vk, dvk, _, _, latk = scheduled_pumped_vinf_3d(
            a0_design, tgt, 2.48, ANCHORED_THERMAL, power_model="thermal",
            steer_gamma_deg=19.7, _dt_scale=dts)
        v0k = scheduled_pumped_vinf_3d(
            a0_design, tgt, 0.0, ANCHORED_THERMAL, power_model="thermal", _dt_scale=dts)[0]
        return (dvk - dv0k) - 0.64 * (vk - v0k), latk
    knot8, lat8 = _knot(0.125)
    knot4, _ = _knot(0.25)
    check("baked thermal 2.48-deg knot (512.1 m/s) replays at the derivation dt (<2 m/s) "
          "and is step-converged (dt/4 vs dt/8 < 25 m/s)",
          abs(knot8 - 512.1) < 2.0 and abs(knot4 - knot8) < 25.0
          and lat8 is not None and abs(lat8 + 2.48) < 0.05,
          f"dt/8 {knot8:.1f}, dt/4 {knot4:.1f} m/s")

    # (iv) conservative bound + quadratic small-beta structure
    ok_bound = True
    for vv in (8.0e3, 23.17e3, 23.64e3, 26.0e3):
        for bb in [0.1 * i for i in range(1, 400)]:
            if plane_tax_for(vv, bb) > vv * math.sin(math.radians(min(bb, 90.0))) + 1e-6:
                ok_bound = False
    check("derived plane tax <= far-field v_inf*|sin(beta)| everywhere (grid sweep)",
          ok_bound and plane_tax_for(23.64e3, 0.0) == 0.0, "")
    q1, q2 = plane_tax_for(23.64e3, 0.5), plane_tax_for(23.64e3, 1.0)
    check("plane tax is ~quadratic near zero (the corner is rounded, not kinked)",
          2.5 < q2 / q1 < 5.5, f"tax(1)/tax(0.5) = {q2/q1:.2f} (quadratic -> 4)")

    # (v) arrival-epoch consequence: shallow basin at ~77.8 kyr; crossing +<60 m/s;
    #     early-arrival branch >2.5 km/s out (settles the issue-#9 early-arrival trade)
    from fermi_sim.astro import alpha_centauri_state
    from fermi_sim.intercept import ecliptic_crossing_time, solve_intercept
    st = alpha_centauri_state()
    miss = 2600.0 * c.AU

    def _budget(T_yr):
        s = solve_intercept(st, T_yr * c.YEAR)
        vv = max(0.0, s.v_inf - miss / (T_yr * c.YEAR))
        return pumped_departure_dv(vv, s.plane_angle_deg, 400.0)
    scan = {T: _budget(T) for T in range(56000, 90001, 100)}
    t_min = min(scan, key=scan.get)
    t_cx = ecliptic_crossing_time(st) / c.YEAR
    pen_cx = _budget(t_cx) - scan[t_min]
    pen_58 = _budget(58000) - scan[t_min]
    check("pumped-budget optimum sits in the ~77.8-kyr basin (rounded corner, issue #9)",
          77300 <= t_min <= 78300, f"argmin {t_min} yr")
    check("in-plane crossing aim costs < 60 m/s over the basin optimum",
          0.0 < pen_cx < 60.0, f"+{pen_cx:.1f} m/s at {t_cx:.0f} yr")
    check("early-arrival branch (58 kyr) stays > 2.5 km/s above the optimum",
          pen_58 > 2.5e3, f"+{pen_58/1e3:.2f} km/s")

    # 13h. PP ARRIVAL-EPOCH SIMULATION RECORD (issue #13). The deep per-epoch direct
    #      simulation (tools/sim_pp_arrival.py) writes docs/data/pp_arrival_sim.json —
    #      the derivation behind docs/PP-ARRIVAL-OPTIMUM.md. Guards: the record exists
    #      and is self-consistent; ONE row replays FRESH from the engine at its recorded
    #      steering angle; the convergence records are tight; the basin facts match the
    #      independent closed-form scan of 13g(v); and the flyability edge is real (a
    #      65-kyr aim is not acquirable).
    import json as _json
    import os as _os
    _rec_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                              "..", "..", "docs", "data", "pp_arrival_sim.json")
    _have_rec = _os.path.exists(_rec_path)
    check("PP arrival simulation record exists (docs/data/pp_arrival_sim.json)", _have_rec)
    if _have_rec:
        rec = _json.load(open(_rec_path))
        meta, rrows = rec["meta"], rec["rows"]
        _esc = math.sqrt(c.MU_EARTH / (c.R_EARTH + 400e3))   # LEO-400 orbit-energy leg
        check("record meta: anchored thermal schedule, design a0/Isp, LEO-400 escape leg",
              meta["schedule"] == "ANCHORED_THERMAL" and meta["power_model"] == "thermal"
              and meta["a0"] == 2.5e-4 and meta["isp_s"] == 2800.0
              and abs(meta["escape_leg"] - _esc) < 1.0, str(meta.get("escape_leg")))
        check("record basin bottom in the 77.0-78.5 kyr window; crossing penalty < 60 m/s",
              77000 <= meta["basin_bottom_T"] <= 78500
              and 0.0 < meta["crossing_penalty"] < 60.0,
              f"{meta['basin_bottom_T']} / +{meta['crossing_penalty']} m/s")
        check("record and the independent closed-form scan agree on the basin (<= 600 yr)",
              abs(meta["basin_bottom_T"] - t_min) <= 600,
              f"sim {meta['basin_bottom_T']} vs scan {t_min}")
        check("record convergence rows: |dt/4 - dt/8| < 40 m/s each",
              all(abs(cv["delta"]) < 40.0 for cv in rec["convergence"]),
              str([cv["delta"] for cv in rec["convergence"]]))
        # fresh single-row replay from the engine at the RECORDED aim + steering angle
        # (the aim is data — the record's miss-allowance convention optimizes the offset
        # direction, so the replay validates the CAMPAIGN integration, not the aim search)
        row = next(r for r in rrows if r["T"] == 75000)
        v_a, dv_a, yr_a, _rv, lat_a = scheduled_pumped_vinf_3d(
            a0_design, row["vinf"], abs(row["tilt"]), ANCHORED_THERMAL,
            power_model="thermal", steer_gamma_deg=row["gamma"], _dt_scale=0.25,
            max_yr=30.0)
        tot_a = _esc + (dv_a - 0.64 * (v_a - row["vinf"]))
        check("record row T=75,000 replays fresh from the engine (<40 m/s)",
              abs(tot_a - row["dv_total"]) < 40.0 and lat_a is not None
              and abs(lat_a + abs(row["tilt"])) < 0.06,
              f"fresh {tot_a:.0f} vs recorded {row['dv_total']:.0f}")
        # 13h-edge (rewritten per adversarial-audit findings 6/7 — the old single-angle
        # probe once certified a false edge by 0.08 yr). TWO-SIDED with margins:
        # (+) the earliest recorded FLYABLE row must replay flyable with >=0.5 yr of
        #     custody margin under the tool's 15-yr gate;
        # (-) an aim ~1.2 kyr BELOW the recorded edge, made strictly EASIER than any
        #     achievable aim there (tilt reduced by MORE than the whole 2600-AU
        #     allowance could buy), must fail a GOLDEN-SEARCHED steering sweep even
        #     with the gate relaxed by +0.5 yr — so unflyability cannot hinge on the
        #     angle probe or on hair-thin custody.
        first_fly = min((r for r in rrows if r["ok"]), key=lambda r: r["T"])
        vf, dvf, yrf, _rvf, latf = scheduled_pumped_vinf_3d(
            a0_design, first_fly["vinf"], abs(first_fly["tilt"]), ANCHORED_THERMAL,
            power_model="thermal", steer_gamma_deg=first_fly["gamma"], _dt_scale=0.5,
            max_yr=30.0)
        check("earliest recorded flyable row replays flyable with >=0.5 yr custody margin",
              vf >= first_fly["vinf"] - 1.0 and yrf <= 14.5 and latf is not None
              and abs(latf + abs(first_fly["tilt"])) <= 0.08,
              f"T={first_fly['T']}: {yrf:.2f} yr, lat {latf}")
        T_neg = meta["flyable_edge_yr"] - 1200.0
        s_neg = solve_intercept(st, T_neg * c.YEAR)
        v_neg = max(0.0, s_neg.v_inf - miss / (T_neg * c.YEAR))
        tilt_ease = math.degrees(math.atan2(miss / (T_neg * c.YEAR), v_neg)) + 0.05
        beta_neg = max(0.0, abs(s_neg.plane_angle_deg) - tilt_ease)
        golden = (math.sqrt(5.0) - 1.0) / 2.0

        def _neg_ok(g):
            v_e, _d, yr_e, _r2, lat_e = scheduled_pumped_vinf_3d(
                a0_design, v_neg, beta_neg, ANCHORED_THERMAL, power_model="thermal",
                steer_gamma_deg=g, _dt_scale=0.5, max_yr=17.0)
            return (v_e >= v_neg - 1.0 and yr_e <= 15.5
                    and lat_e is not None and abs(lat_e + beta_neg) <= 0.08)
        any_fly = False
        a_g, b_g = 0.0, 40.0
        probes = set()
        for _ in range(9):
            c1 = b_g - golden * (b_g - a_g)
            c2 = a_g + golden * (b_g - a_g)
            for g in (round(c1, 1), round(c2, 1)):
                if g not in probes:
                    probes.add(g)
                    if _neg_ok(g):
                        any_fly = True
            if any_fly:
                break
            a_g, b_g = a_g + 0.18 * (b_g - a_g), b_g - 0.18 * (b_g - a_g)
        check("below the recorded edge (-1.2 kyr, easier-than-achievable aim) NOTHING "
              "flies across a steering sweep even at gate+0.5 yr",
              not any_fly, f"T={T_neg:.0f}, beta {beta_neg:.2f}, probes {sorted(probes)}")

    # 14. Phase-split drift guard (the pumped-vs-PSI comparison numbers): retrograde
    #     pump-down ~2.1 revs to the 0.42 AU latch, 3 prograde perihelion passes, and the
    #     dv split ~8.3 retro + ~17.3 prograde. Re-integrated independently.
    ph = _phase_split(2.5e-4, tgt)
    check("phase split: ~2.1 retro pump-down revs, 3 perihelion passes",
          close(ph["retro_revs"], 2.13, abs_=0.25) and ph["passes"] == 3,
          f"{ph['retro_revs']:.2f} retro revs, {ph['passes']} passes")
    check("phase split: dv ~8.3 retro + ~17.3 prograde",
          close(ph["dv_retro"] / 1e3, 8.31, abs_=0.6) and close(ph["dv_pro"] / 1e3, 17.32, abs_=0.6),
          f"{ph['dv_retro']/1e3:.2f} + {ph['dv_pro']/1e3:.2f} km/s")


if __name__ == "__main__":
    from _util import summary
    run()
    raise SystemExit(summary())
