"""Schedule-PARAMETERIZED perihelion-pumping campaign integrator (issue #4).

The bang-bang policy in :func:`fermi_sim.departure.perihelion_pumped_vinf` hard-codes
its burn-arc geometry (retrograde within 60 deg of apoapsis, prograde within 70 deg of
periapsis, staircase energy guard -30 km^2/s^2, latch at the 0.42 AU thermal floor).
This module integrates the SAME physics with that geometry as free parameters, and with
switch boundaries located by BISECTION inside the step (the per-step switch quantization
measured as external finding F5l does not apply to scheduled_pumped_vinf; NOTE that
campaign_overhead_curve below keeps per-step switching — its knots carry the engine dt's
first-order truncation, ~+20-35 m/s at the top of the aim range, conservative direction).

The optimiser (tools/optimize_pump_schedule.py) searches the parameter space per a0 and
bakes its results into OPTIMIZED_SCHEDULES below; :func:`optimized_pumped_vinf` replays
a baked schedule through this integrator at the engine's dt convention, so every published
number remains the output of a direct integration, never of the optimiser's own bookkeeping.
The bang-bang policy stays untouched in departure.py as the independent cross-check
(the optimum must never lose to it).

Physics (identical to the bang-bang integrator): P(r)/P(1 AU) is the selected
power model — power_model="thermal" (the DERIVED cap_eff(r) curve from
fermi_sim.thermal, the shipped default since issue #5) or "cap" (the legacy
min((1 AU/r)^2, power_cap) step, the PSI-comparable audit comparator) — with
accel = a0 * factor(r) * (m0/m), thrust tangential (+-), 2-D heliocentric,
5-state RK4 (mass coupled), adaptive dt = min(max(600, 0.002*period_r), 5 d).

Schedule parameters (angles in degrees, energies J/kg, radii AU):
    th_retro  retrograde pump-down arc half-width about apoapsis
    th_pro    prograde staircase arc half-width about periapsis
    e_guard   staircase stops when E >= e_guard (escape guard; finisher above)
    rp_latch  osculating-perihelion latch that ends pump-down (>= the 0.42 AU floor)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import constants as c

RP_FLOOR_AU = 0.42          # thermal floor — rp_latch may not go below this
_BOOT_ECC = 0.05            # bootstrap ends when eccentricity exceeds this (as bang-bang)


@dataclass(frozen=True)
class Schedule:
    th_retro: float = 60.0
    th_pro: float = 70.0
    e_guard: float = -3.0e7
    rp_latch: float = RP_FLOOR_AU

    def validate(self) -> None:
        if not (0.0 < self.th_retro <= 180.0 and 0.0 < self.th_pro <= 180.0):
            raise ValueError(f"Schedule: arc half-widths must be in (0, 180] deg, got {self}")
        if not (RP_FLOOR_AU - 1e-9 <= self.rp_latch < 1.0):
            raise ValueError(f"Schedule: rp_latch must be in [{RP_FLOOR_AU}, 1) AU, got {self}")
        if not (-3.0e8 < self.e_guard < 0.0):
            raise ValueError(f"Schedule: e_guard must be a bound (negative) energy, got {self}")


# Default schedule == the bang-bang policy's geometry (the cross-check anchor).
BANG_BANG = Schedule()

# ---------------------------------------------------------------------------
# BAKED OPTIMISED SCHEDULES (tools/optimize_pump_schedule.py, issue #4).
# Per-a0 Nelder-Mead winners, each re-integrated at the ENGINE'S dt convention
# (min(max(600 s, 0.002*period_r), 5 d)); the tuple is that result (v_inf m/s,
# dv m/s, years, revs) — never the optimiser's own bookkeeping. NOTE the dv
# values carry the engine dt's first-order truncation (~+20-35 m/s vs a
# dt-refined run at the top of the aim range — conservative direction; see
# audit/EXTERNAL_AUDIT_SCOPE.md section 8). Audit coverage (audit_pumping):
# the 2.5e-4 design entry is replayed full-tuple; 1.9e-4 (coarse dt) and
# 3.0e-4 are replayed reach-only; the other entries are baked records.
#
# The 2.5e-4 entry is THE SHIPPED DEFAULT CAMPAIGN — the 12-yr-custody optimum
# (owner decision: publish the frontier, anchor the default at the 12-yr /
# PSI-comparable point). It beats PSI's published 12-yr optimum (23.97 km/s) by
# 3.5% under identical physics assumptions; the unconstrained frontier point is
# 22.84 km/s at 28.5 yr. The other entries prove MONOTONE CLOSURE: bang-bang's
# strand band (1.9e-4) and stall window (3.0e-4) both close under per-a0
# optimised schedules — the islands were fixed-arc phasing artifacts.
# ---------------------------------------------------------------------------
OPTIMIZED_SCHEDULES = {
    1.6e-4: (Schedule(28.55044210896581, 77.31160170324938, -56475251.33402688, 0.42),
             (23640.9, 24507.0, 34.9, 10.0)),
    1.9e-4: (Schedule(15.0, 94.6364531840166, -48429757.61410839, 0.42),
             (23657.0, 24287.0, 21.3, 12.8)),
    2.24e-4: (Schedule(15.0, 81.25071985935298, -38959524.36068589, 0.47138705290121186),
              (23670.0, 23186.0, 21.9, 9.8)),
    2.5e-4: (Schedule(31.357722220958863, 67.12243839049353, -60452731.70963464,
                      0.4740166735677317),
             (23640.0, 23136.0, 12.0, 5.9)),
    3.0e-4: (Schedule(25.77044785200091, 88.78773305684481, -73763298.35824955, 0.42),
             (23680.0, 24306.0, 5.7, 5.8)),
}
DESIGN_A0 = 2.5e-4

# Overhead (dv - v_inf, m/s) of the ANCHORED design schedule at en-route targets
# (campaign_overhead_curve; tmp/ro/i4_overhead.py). Monotone declining; NEGATIVE
# past ~23 km/s — the Oberth signature: the campaign buys the cruise for less dv
# than the cruise speed. Validity [8, 26] km/s (the anchored campaign tops out
# at 26 within 60 yr); the page's aim range peaks at 25.1.
TAX_OPT_TABLE = (
    (8000.0, 10562.0), (9000.0, 9704.0), (10000.0, 8863.0), (11000.0, 8038.0),
    (12000.0, 7229.0), (13000.0, 6439.0), (14000.0, 5665.0), (15000.0, 4911.0),
    (16000.0, 4176.0), (17000.0, 3462.0), (18000.0, 2770.0), (19000.0, 2104.0),
    (20000.0, 1467.0), (21000.0, 864.0), (22000.0, 300.0), (23000.0, -213.0),
    (23640.0, -509.0), (24000.0, -661.0), (25000.0, -1014.0), (26000.0, -1223.0),
)


# Per-target campaign under the ANCHORED design schedule across the page's aim range
# (campaign_overhead_curve; tmp/ro/i4_display_table.py): (v_target m/s, overhead m/s,
# years, revs). Nearly flat — every aim in 23.0–26.0 km/s is crossed near the end of
# the same ~12-yr campaign. audit_pumping replays the THERMAL sibling table's knots
# against a fresh campaign_overhead_curve integration; this cap-model table is a
# baked record guarded by the anchor knot only.
OPT_CAMPAIGN_TABLE = (
    (23000.0, -213.2, 12.004, 5.842),
    (23250.0, -332.1, 12.014, 5.850),
    (23500.0, -446.5, 12.026, 5.858),
    (23640.0, -508.5, 12.036, 5.863),
    (23750.0, -556.1, 12.042, 5.867),
    (24000.0, -660.6, 12.061, 5.876),
    (24250.0, -759.3, 12.083, 5.884),
    (24500.0, -851.7, 12.113, 5.894),
    (24750.0, -937.0, 12.149, 5.903),
    (25000.0, -1014.3, 12.202, 5.913),
    (25250.0, -1082.5, 12.279, 5.923),
    (25500.0, -1140.4, 12.408, 5.935),
    (25750.0, -1187.6, 12.641, 5.946),
    (26000.0, -1222.5, 13.188, 5.959),
)


# ---------------------------------------------------------------------------
# THERMAL power model (issue #5): the same optimisation repeated under the
# DERIVED cap_eff(r) curve (fermi_sim/thermal.py; cap_eff(0.42 AU) = 3.54 for
# the GaAs defaults, vs the assumed 4.0x step). Under the derived curve the
# fixed-geometry campaigns STRAND at the design a0 (bang-bang reaches only
# 20.1 km/s, the cap4-optimised schedule 16.0) — but per-a0 re-optimisation
# closes the design point and the whole tested grid again, re-confirming that
# the closure gaps are schedule-phasing artifacts, not physics. These tables
# are THE SHIPPED DEFAULT since issue #5; the cap-model tables above remain
# the PSI-comparable working point and the audit comparator.
#
# Thermal custody frontier at the design a0 (tmp/ro/i5_frontier.py):
#   <=10 yr -> 24.83 km/s; <=12 yr -> 24.44 (ANCHOR — same 12-yr custody
#   policy as issue #4); <=15 yr -> 24.18; <=30 yr -> 23.41; ~60 yr -> 23.08.
# ---------------------------------------------------------------------------
ANCHORED_THERMAL = Schedule(23.095223778657733, 84.43328139555737,
                            -25134228.462172244, 0.42)
OPTIMIZED_SCHEDULES_THERMAL = {
    1.6e-4: (Schedule(15.0, 101.4162518335059, -24998194.8755305, 0.42),
             (23617.4, 25554.2, 60.004, 15.957)),
    1.9e-4: (Schedule(21.47079760431209, 85.09319776015022, -24160816.362550657, 0.42),
             (23646.9, 24219.2, 56.192, 10.871)),
    2.24e-4: (Schedule(20.734042270919232, 72.14808273560996, -25615253.582493924, 0.42),
              (23688.0, 23434.8, 53.518, 9.826)),
    2.5e-4: (ANCHORED_THERMAL, (23651.0, 24436.6, 12.003, 7.886)),
    3.0e-4: (Schedule(15.0, 63.41161854875453, -31665055.80569147, 0.6881837234531991),
             (23665.5, 21905.2, 56.794, 6.857)),
}

# Overhead (dv - v_inf, m/s) of the ANCHORED THERMAL schedule at en-route
# targets (campaign_overhead_curve, power_model="thermal"; tmp/ro/i5_bake.py).
# Monotone declining but POSITIVE everywhere — the thermal derate removes the
# cap-model's Oberth-negative signature (+0.785 km/s at the AC anchor).
# Validity [8, 26] km/s (27 km/s is not reached within 60 yr).
TAX_OPT_THERMAL_TABLE = (
    (8000.0, 11634.6), (9000.0, 10771.2), (10000.0, 9924.1), (11000.0, 9093.6),
    (12000.0, 8280.2), (13000.0, 7484.8), (14000.0, 6708.4), (15000.0, 5952.5),
    (16000.0, 5218.9), (17000.0, 4510.1), (18000.0, 3829.1), (19000.0, 3179.7),
    (20000.0, 2567.3), (21000.0, 1998.3), (22000.0, 1482.0), (23000.0, 1031.2),
    (23640.0, 785.3), (24000.0, 664.5), (25000.0, 410.2), (26000.0, 299.6),
)

# DERIVED out-of-plane (tilt) cost of the anchored THERMAL campaign at the
# 23.64 km/s design aim (tools/derive_plane_tax.py, issue #9): the 3-D integrator
# (scheduled_pumped_vinf_3d) steers thrust out of plane on the hyperbolic leg with
# the per-beta optimal tilt angle gamma*, and the knot is
# dv_3d(beta, gamma*) - dv_3d(0), both at dt/8 with the residual v_inf-overshoot
# corrected (d(dv)/d(v_inf) = 0.64 along the campaign). The curve is ~QUADRATIC
# near zero (~95 m/s * beta_deg^2 — steering inside existing burns is
# second-order), reaching only half the far-field bound v_inf*sin(beta) at the
# 2.48 deg direct-optimum aim. VALIDITY [0, 4] deg: above ~4 deg the 1/r^2-faded
# hyperbolic-leg impulse can no longer buy the tilt within custody (the 6 deg
# probe needs 23 yr), so consumers continue with the far-field marginal slope,
# tax(4) + v_inf*(sin(beta) - sin(4 deg)) — measured 1953 m/s at 6 deg vs 1944
# continued. Cross-check: the same derivation under the CAP model prices 2.48 deg
# at 606 m/s vs PSI's independently measured 578 m/s (their final assessment,
# 3-D re-optimization) — 5% apart, inside their +-0.2 km/s search scatter.
# Consumers scale knots by (v_inf / 23640). NOTE (adversarial-audit finding 4):
# the TRUE tilt cost falls slightly with v_inf (a faster escape leg spends less
# time under the fade), so this linear scaling has the wrong trend sign and
# OVERCHARGES by up to ~20-30% at the top of the [23, 26] km/s aim band —
# conservative direction, and <=1% at the AC anchors where every shipped number
# lives. Re-derive at multiple v_inf anchors before using the curve far off
# 23.64 km/s. Applied by fermi_sim.departure.plane_tax_for and mirrored in
# web/physics.js.
PLANE_TAX_THERMAL_TABLE = (
    (0.0, 0.0),
    (0.1, 1.2), (0.25, 6.7), (0.5, 24.3), (0.75, 54.0), (1.0, 94.2),
    (1.5, 205.2), (2.0, 350.8), (2.48, 512.1), (3.0, 708.7), (4.0, 1123.4),
)
PLANE_TAX_BETA_MAX = 4.0     # deg — table validity; far-field marginal slope beyond
PLANE_TAX_V_REF = 23640.0    # m/s — the aim the table was derived at

# Per-target campaign under the ANCHORED THERMAL schedule across the page's
# aim range (tmp/ro/i5_bake.py): (v_target m/s, overhead m/s, years, revs).
OPT_CAMPAIGN_THERMAL_TABLE = (
    (23000.0, 1031.2, 11.975, 7.869),
    (23250.0, 930.7, 11.999, 7.877),
    (23500.0, 835.8, 12.02, 7.883),
    (23640.0, 785.3, 12.038, 7.887),
    (23750.0, 746.9, 12.051, 7.89),
    (24000.0, 664.5, 12.094, 7.899),
    (24250.0, 589.1, 12.148, 7.906),
    (24500.0, 521.4, 12.214, 7.913),
    (24750.0, 461.8, 12.307, 7.921),
    (25000.0, 410.2, 12.458, 7.929),
    (25250.0, 367.3, 12.704, 7.938),
    (25500.0, 333.9, 13.156, 7.946),
    (25750.0, 311.0, 14.306, 7.954),
    (26000.0, 299.6, 20.603, 7.963),
)


def campaign_at(v_inf_target: float, power_model: str = "thermal"):
    """Anchored-schedule campaign at an arbitrary aim in [23.0, 26.0] km/s.

    Linear interpolation over the anchored campaign table of the requested
    power model ("thermal" — the shipped default — or "cap", the
    PSI-comparable comparator); returns a dict {vinf, dv, years, revs}
    (vinf = the target — the campaign is read off at the exact crossing) or
    None outside the table's range (callers fall back to the bang-bang
    integrator).
    """
    tables = {"thermal": OPT_CAMPAIGN_THERMAL_TABLE, "cap": OPT_CAMPAIGN_TABLE}
    if power_model not in tables:
        raise ValueError(f"campaign_at: power_model must be 'thermal' or 'cap', got {power_model!r}")
    table = tables[power_model]
    if not (table[0][0] <= v_inf_target <= table[-1][0]):
        return None
    for i in range(len(table) - 1):
        x0, o0, y0, r0 = table[i]
        x1, o1, y1, r1 = table[i + 1]
        if v_inf_target <= x1:
            f = (v_inf_target - x0) / (x1 - x0)
            return {"vinf": v_inf_target, "dv": v_inf_target + o0 + f * (o1 - o0),
                    "years": y0 + f * (y1 - y0), "revs": r0 + f * (r1 - r0)}
    return None


def optimized_pumped_vinf(a0: float, v_inf_target: float = 23.64e3,
                          power_model: str = "thermal"):
    """Baked optimised-campaign result for an exactly-baked a0 (see the tables).

    Returns (v_inf m/s, dv m/s, years, revs) from the baked fine-grained
    integration under the requested power model, or None if a0 is not a baked
    key (callers fall back to integrating at the vehicle's own a0).
    """
    tables = {"thermal": OPTIMIZED_SCHEDULES_THERMAL, "cap": OPTIMIZED_SCHEDULES}
    if power_model not in tables:
        raise ValueError(
            f"optimized_pumped_vinf: power_model must be 'thermal' or 'cap', got {power_model!r}")
    table = tables[power_model]
    for k, (sch, res) in table.items():
        if abs(a0 - k) <= 1e-9 and abs(v_inf_target - 23.64e3) < 1.0:
            return res
    return None


def _decide(x, y, vx, vy, latched, sch, mu, AU):
    """Thrust mode (-1 retro / 0 coast / +1 prograde) + osculating rp for the latch."""
    r = math.hypot(x, y)
    v2 = vx * vx + vy * vy
    E = 0.5 * v2 - mu / r
    h = x * vy - y * vx
    ecc = math.sqrt(max(0.0, 1.0 + 2.0 * E * h * h / (mu * mu)))
    p_sl = h * h / mu
    rp = p_sl / (1.0 + ecc) if ecc < 1.0 or p_sl > 0 else 0.0
    rd = 1.0 if (x * vx + y * vy) >= 0.0 else -1.0
    if ecc > 1e-6:
        nu = rd * math.acos(max(-1.0, min(1.0, (p_sl / r - 1.0) / ecc)))
    else:
        nu = 0.0
    if not latched:
        if ecc < _BOOT_ECC:
            return (-1.0 if x > 0.0 else 0.0), rp
        return (-1.0 if abs(abs(nu) - math.pi) < math.radians(sch.th_retro) else 0.0), rp
    if E < sch.e_guard:
        return (+1.0 if abs(nu) < math.radians(sch.th_pro) else 0.0), rp
    return +1.0, rp


def scheduled_pumped_vinf(a0: float, v_inf_target: float, sch: Schedule = BANG_BANG,
                          isp_s: float = 2800.0, power_cap: float = 4.0,
                          max_yr: float = 60.0, _dt_scale: float = 1.0,
                          power_model: str = "cap",
                          return_diag: bool = False):
    """Integrate the pumping campaign under an explicit :class:`Schedule`.

    Returns (v_inf_achieved m/s, dv m/s, years, revs) exactly like
    perihelion_pumped_vinf — plus a diagnostics dict (min_r_au, thrust work,
    energy gain, final mass fraction) as a fifth element when ``return_diag``.
    Switch boundaries (mode changes and the pump-down latch) are located by
    bisection within the step to ~1e-3 dt, so the arc edges are continuous
    rather than step-quantized.
    """
    for nm, val in (("a0", a0), ("v_inf_target", v_inf_target), ("isp_s", isp_s),
                    ("power_cap", power_cap), ("max_yr", max_yr)):
        if not math.isfinite(val):
            raise ValueError(f"scheduled_pumped_vinf: {nm} must be finite, got {val!r}")
    if a0 <= 0.0 or v_inf_target <= 0.0 or isp_s <= 0.0 or max_yr <= 0.0 or power_cap < 1.0:
        raise ValueError("scheduled_pumped_vinf: a0, v_inf_target, isp_s, max_yr must be "
                         "positive and power_cap >= 1")
    if not (math.isfinite(_dt_scale) and _dt_scale > 0.0):
        raise ValueError(f"scheduled_pumped_vinf: _dt_scale must be positive, got {_dt_scale!r}"
                         " (0 would freeze the integration loop)")
    sch.validate()
    from .departure import _pump_power_factor
    pf = _pump_power_factor(power_model, power_cap)

    mu, AU = c.MU_SUN, c.AU
    ve = isp_s * c.G0
    target_E = 0.5 * v_inf_target ** 2
    x, y, vx, vy, m = AU, 0.0, 0.0, math.sqrt(mu / AU), 1.0
    t, dv, revs, ang_prev = 0.0, 0.0, 0.0, 0.0
    latched = False
    max_t = max_yr * c.YEAR
    E0 = 0.5 * (mu / AU) - mu / AU                 # circular-start specific energy (-mu/2AU)
    min_r, work = AU, 0.0

    def step(state, dt, d):
        """One 5-state RK4 step under fixed thrust mode d; returns (state', dv_inc)."""
        def deriv(s):
            X, Y, VX, VY, M = s
            rr = math.hypot(X, Y)
            vv = math.hypot(VX, VY) or 1.0
            am = (a0 * pf(rr) / max(M, 0.05) * d) if d else 0.0
            md = (-(a0 * pf(rr)) / ve) if d else 0.0
            g = -mu / rr ** 3
            return (VX, VY, g * X + am * VX / vv, g * Y + am * VY / vv, md)
        s = state
        k1 = deriv(s)
        k2 = deriv(tuple(s[i] + 0.5 * dt * k1[i] for i in range(5)))
        k3 = deriv(tuple(s[i] + 0.5 * dt * k2[i] for i in range(5)))
        k4 = deriv(tuple(s[i] + dt * k3[i] for i in range(5)))
        out = tuple(s[i] + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(5))
        out = (out[0], out[1], out[2], out[3], max(out[4], 0.05))
        if d:
            rr = math.hypot(s[0], s[1])
            return out, (a0 * pf(rr) / max(s[4], 0.05)) * dt
        return out, 0.0

    def _result(E):
        v_out = math.sqrt(2.0 * E) if E > 0.0 else 0.0
        if not return_diag:
            return v_out, dv, t / c.YEAR, revs
        diag = {"min_r_au": min_r / AU, "work": work, "E_gain": E - E0, "m": m}
        return v_out, dv, t / c.YEAR, revs, diag

    while t < max_t:
        r = math.hypot(x, y)
        min_r = min(min_r, r)
        E = 0.5 * (vx * vx + vy * vy) - mu / r
        if E >= target_E:
            return _result(E)
        d0, rp0 = _decide(x, y, vx, vy, latched, sch, mu, AU)
        if not latched and rp0 <= sch.rp_latch * AU:
            latched = True
            d0, rp0 = _decide(x, y, vx, vy, latched, sch, mu, AU)
        period = 2.0 * math.pi * math.sqrt(max(r, 0.1 * AU) ** 3 / mu)
        dt = min(max(600.0, 0.002 * period), 5.0 * 86400.0) * _dt_scale

        s0 = (x, y, vx, vy, m)
        s1, dv1 = step(s0, dt, d0)
        d1, rp1 = _decide(s1[0], s1[1], s1[2], s1[3], latched, sch, mu, AU)
        crossed_latch = (not latched) and rp1 <= sch.rp_latch * AU
        if d1 != d0 or crossed_latch:
            # a switch boundary lies inside this step — bisect to it (~1e-3 dt), take the
            # sub-step under the OLD mode, and let the next loop iteration re-decide there
            lo, hi = 0.0, dt
            for _ in range(10):
                mid = 0.5 * (lo + hi)
                sm, _dv = step(s0, mid, d0)
                dm, rpm = _decide(sm[0], sm[1], sm[2], sm[3], latched, sch, mu, AU)
                if dm != d0 or ((not latched) and rpm <= sch.rp_latch * AU):
                    hi = mid
                else:
                    lo = mid
            sub = max(hi, 1e-6 * dt)
            s1, dv1 = step(s0, sub, d0)
            dt = sub
        if d0:
            # thrust work dE = a·v dt (first-order at the step head — audit-grade bookkeeping);
            # the thrust is along ±v̂ so a·v = d·|a|·|v|: retrograde arcs REMOVE energy
            r_h = math.hypot(s0[0], s0[1])
            am_h = a0 * pf(r_h) / max(s0[4], 0.05)
            work += d0 * am_h * math.hypot(s0[2], s0[3]) * dt
        x, y, vx, vy, m = s1
        dv += dv1
        ang = math.atan2(y, x)
        d_ang = (ang - ang_prev + math.pi) % (2.0 * math.pi) - math.pi
        revs += abs(d_ang) / (2.0 * math.pi)
        ang_prev = ang
        t += dt

    r = math.hypot(x, y)
    E = 0.5 * (vx * vx + vy * vy) - mu / r
    return _result(E)


def _decide3(x, y, z, vx, vy, vz, latched, sch, mu):
    """3-D osculating thrust-mode decision — reduces EXACTLY to :func:`_decide` when
    z = vz = 0 (the planar-embedding property audit_pumping pins). Same contract:
    returns (mode -1/0/+1, osculating perihelion radius)."""
    r = math.hypot(x, y, z)
    v2 = vx * vx + vy * vy + vz * vz
    E = 0.5 * v2 - mu / r
    hx = y * vz - z * vy
    hy = z * vx - x * vz
    hz = x * vy - y * vx
    h2 = hx * hx + hy * hy + hz * hz
    ecc = math.sqrt(max(0.0, 1.0 + 2.0 * E * h2 / (mu * mu)))
    p_sl = h2 / mu
    rp = p_sl / (1.0 + ecc) if ecc < 1.0 or p_sl > 0 else 0.0
    rd = 1.0 if (x * vx + y * vy + z * vz) >= 0.0 else -1.0
    if ecc > 1e-6:
        nu = rd * math.acos(max(-1.0, min(1.0, (p_sl / r - 1.0) / ecc)))
    else:
        nu = 0.0
    if not latched:
        if ecc < _BOOT_ECC:
            return (-1.0 if x > 0.0 else 0.0), rp
        return (-1.0 if abs(abs(nu) - math.pi) < math.radians(sch.th_retro) else 0.0), rp
    if E < sch.e_guard:
        return (+1.0 if abs(nu) < math.radians(sch.th_pro) else 0.0), rp
    return +1.0, rp


def _asymptote_latitude(x, y, z, vx, vy, vz, mu):
    """Outgoing-asymptote latitude (deg) of the osculating orbit; None if not hyperbolic."""
    r = math.sqrt(x * x + y * y + z * z)
    v2 = vx * vx + vy * vy + vz * vz
    rv = x * vx + y * vy + z * vz
    ex = ((v2 - mu / r) * x - rv * vx) / mu
    ey = ((v2 - mu / r) * y - rv * vy) / mu
    ez = ((v2 - mu / r) * z - rv * vz) / mu
    e = math.sqrt(ex * ex + ey * ey + ez * ez)
    if e <= 1.0:
        return None
    hx = y * vz - z * vy
    hy = z * vx - x * vz
    hz = x * vy - y * vx
    h = math.sqrt(hx * hx + hy * hy + hz * hz)
    # in-plane basis: e_hat (toward perihelion) and p_hat = h_hat x e_hat
    exh, eyh, ezh = ex / e, ey / e, ez / e
    hxh, hyh, hzh = hx / h, hy / h, hz / h
    px = hyh * ezh - hzh * eyh
    py = hzh * exh - hxh * ezh
    pz = hxh * eyh - hyh * exh
    nu_inf = math.acos(max(-1.0, min(1.0, -1.0 / e)))
    uz = math.cos(nu_inf) * ezh + math.sin(nu_inf) * pz
    return math.degrees(math.asin(max(-1.0, min(1.0, uz))))


def scheduled_pumped_vinf_3d(a0: float, v_inf_target: float, beta_deg: float,
                             sch: Schedule = ANCHORED_THERMAL, isp_s: float = 2800.0,
                             power_cap: float = 4.0, max_yr: float = 30.0,
                             steer_gamma_deg: float = 0.0, _dt_scale: float = 1.0,
                             power_model: str = "thermal"):
    """THREE-DIMENSIONAL pumping campaign with out-of-plane steering (issue #9).

    Same physics, schedule geometry, power models, stepping and switch-bisection as
    :func:`scheduled_pumped_vinf`, generalised to a 7-state (x, y, z, v, m) RK4. The
    departure-asymptote tilt beta (deg, BELOW the ecliptic — the AC geometry) is
    acquired by steering thrust out of plane on the HYPERBOLIC leg, where the plane
    change is cheapest (buying it at perihelion would price the tilt at the ~69 km/s
    perihelion speed; buying it late prices it near v_inf — the same reason the
    far-field bound is v_inf*sin(beta)):

      - while the osculating orbit is hyperbolic (E > 0) and the outgoing-asymptote
        latitude still sits above the -beta target, burn-mode thrust is tilted by
        ``steer_gamma_deg`` toward -z (magnitude unchanged — steering redirects
        thrust, it never adds any);
      - once the ENERGY target is met but the tilt is not, thrust goes pure -z (the
        endgame buys only the remaining out-of-plane velocity, throttled by the same
        1/r^2 power fade as everything else);
      - the campaign ends when both the energy target and the asymptote-latitude
        target are met (feedback cutoff — no overshoot beyond one step).

    With ``beta_deg = 0`` the z-equations carry exact zeros and the integration
    REPRODUCES the planar integrator (the embedding property the audits pin).

    MIRROR FOLD (adversarial-audit finding 3, documented): ``beta_deg`` is the
    MAGNITUDE of the aim tilt; the integrator always steers toward -z. Aims ABOVE
    the ecliptic (post-crossing epochs, positive tilt) are priced by passing
    |beta| — exact by the z-mirror symmetry of the two-body problem (the planar
    initial state and dynamics are z-equivariant, so the +z and -z campaigns are
    mirror images with identical Δv). Callers fold the sign (abs), as
    plane_tax_for and the epoch tools do.

    Returns (v_inf m/s, dv m/s, years, revs, asymptote_latitude_deg-or-None); the
    tilt COST is dv(beta) - dv(0) under the same gamma-optimisation, and the achieved
    latitude gates any published value (|lat + beta| <= 0.05 deg — enforced by the
    derivation tool tools/derive_plane_tax.py).
    """
    for nm, val in (("a0", a0), ("v_inf_target", v_inf_target), ("beta_deg", beta_deg),
                    ("isp_s", isp_s), ("power_cap", power_cap), ("max_yr", max_yr),
                    ("steer_gamma_deg", steer_gamma_deg)):
        if not math.isfinite(val):
            raise ValueError(f"scheduled_pumped_vinf_3d: {nm} must be finite, got {val!r}")
    if a0 <= 0.0 or v_inf_target <= 0.0 or isp_s <= 0.0 or max_yr <= 0.0 or power_cap < 1.0:
        raise ValueError("scheduled_pumped_vinf_3d: a0, v_inf_target, isp_s, max_yr must be "
                         "positive and power_cap >= 1")
    if beta_deg < 0.0 or beta_deg >= 90.0:
        raise ValueError(f"scheduled_pumped_vinf_3d: beta_deg must be in [0, 90), got {beta_deg!r}")
    if not (0.0 <= steer_gamma_deg < 90.0):
        raise ValueError(f"scheduled_pumped_vinf_3d: steer_gamma_deg must be in [0, 90), "
                         f"got {steer_gamma_deg!r}")
    if not (math.isfinite(_dt_scale) and _dt_scale > 0.0):
        raise ValueError(f"scheduled_pumped_vinf_3d: _dt_scale must be positive, got {_dt_scale!r}")
    sch.validate()
    from .departure import _pump_power_factor
    pf = _pump_power_factor(power_model, power_cap)

    mu, AU = c.MU_SUN, c.AU
    ve = isp_s * c.G0
    target_E = 0.5 * v_inf_target ** 2
    lat_target = -beta_deg
    tang = math.tan(math.radians(steer_gamma_deg)) if beta_deg > 0.0 else 0.0
    x, y, z = AU, 0.0, 0.0
    vx, vy, vz = 0.0, math.sqrt(mu / AU), 0.0
    m = 1.0
    t, dv, revs, ang_prev = 0.0, 0.0, 0.0, 0.0
    latched = False
    max_t = max_yr * c.YEAR

    def step(state, dt, d, smode):
        """RK4 step under fixed thrust mode d and steer mode smode
        (0 none / 1 tilt-by-gamma / 2 pure -z)."""
        def deriv(s):
            X, Y, Z, VX, VY, VZ, M = s
            rr = math.hypot(X, Y, Z)
            vv = math.hypot(VX, VY, VZ) or 1.0
            g = -mu / rr ** 3
            if d:
                am = a0 * pf(rr) / max(M, 0.05)
                md = -(a0 * pf(rr)) / ve
                if smode == 2:
                    ux, uy, uz = 0.0, 0.0, -1.0
                else:
                    ux, uy, uz = d * VX / vv, d * VY / vv, d * VZ / vv
                    if smode == 1:
                        uz -= tang
                        un = math.sqrt(ux * ux + uy * uy + uz * uz)
                        ux, uy, uz = ux / un, uy / un, uz / un
                return (VX, VY, VZ, g * X + am * ux, g * Y + am * uy, g * Z + am * uz, md)
            return (VX, VY, VZ, g * X, g * Y, g * Z, 0.0)
        s = state
        k1 = deriv(s)
        k2 = deriv(tuple(s[i] + 0.5 * dt * k1[i] for i in range(7)))
        k3 = deriv(tuple(s[i] + 0.5 * dt * k2[i] for i in range(7)))
        k4 = deriv(tuple(s[i] + dt * k3[i] for i in range(7)))
        out = tuple(s[i] + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(7))
        out = out[:6] + (max(out[6], 0.05),)
        if d:
            rr = math.hypot(s[0], s[1], s[2])
            return out, (a0 * pf(rr) / max(s[6], 0.05)) * dt
        return out, 0.0

    def _result(E):
        v_out = math.sqrt(2.0 * E) if E > 0.0 else 0.0
        lat = _asymptote_latitude(x, y, z, vx, vy, vz, mu)
        return v_out, dv, t / c.YEAR, revs, lat

    while t < max_t:
        r = math.hypot(x, y, z)
        E = 0.5 * (vx * vx + vy * vy + vz * vz) - mu / r
        lat_now = _asymptote_latitude(x, y, z, vx, vy, vz, mu) if E > 0.0 else None
        tilt_needed = (beta_deg > 0.0
                       and (lat_now is None or lat_now > lat_target))
        if E >= target_E and (beta_deg == 0.0 or not tilt_needed):
            return _result(E)
        d0, rp0 = _decide3(x, y, z, vx, vy, vz, latched, sch, mu)
        if not latched and rp0 <= sch.rp_latch * AU:
            latched = True
            d0, rp0 = _decide3(x, y, z, vx, vy, vz, latched, sch, mu)
        if E >= target_E:
            # energy done, tilt not: endgame — thrust pure -z until the latitude gate
            d0, smode = 1.0, 2
        elif d0 and tang != 0.0 and lat_now is not None and tilt_needed:
            smode = 1                  # hyperbolic burn, asymptote still high: tilt by gamma
        else:
            smode = 0
        if E >= target_E and not d0:
            return _result(E)
        period = 2.0 * math.pi * math.sqrt(max(r, 0.1 * AU) ** 3 / mu)
        dt = min(max(600.0, 0.002 * period), 5.0 * 86400.0) * _dt_scale

        s0 = (x, y, z, vx, vy, vz, m)
        s1, dv1 = step(s0, dt, d0, smode)
        d1, rp1 = _decide3(s1[0], s1[1], s1[2], s1[3], s1[4], s1[5], latched, sch, mu)
        crossed_latch = (not latched) and rp1 <= sch.rp_latch * AU
        if smode != 2 and (d1 != d0 or crossed_latch):
            lo, hi = 0.0, dt
            for _ in range(10):
                mid = 0.5 * (lo + hi)
                sm, _dv = step(s0, mid, d0, smode)
                dm, rpm = _decide3(sm[0], sm[1], sm[2], sm[3], sm[4], sm[5], latched, sch, mu)
                if dm != d0 or ((not latched) and rpm <= sch.rp_latch * AU):
                    hi = mid
                else:
                    lo = mid
            sub = max(hi, 1e-6 * dt)
            s1, dv1 = step(s0, sub, d0, smode)
            dt = sub
        elif smode == 2:
            # bisect the LATITUDE gate inside the endgame step so the cutoff is
            # event-located, not step-quantized (same convention as the mode switches)
            latf = _asymptote_latitude(s1[0], s1[1], s1[2], s1[3], s1[4], s1[5], mu)
            if latf is not None and latf <= lat_target:
                lo, hi = 0.0, dt
                for _ in range(10):
                    mid = 0.5 * (lo + hi)
                    sm, _dv = step(s0, mid, d0, smode)
                    lm = _asymptote_latitude(sm[0], sm[1], sm[2], sm[3], sm[4], sm[5], mu)
                    if lm is not None and lm <= lat_target:
                        hi = mid
                    else:
                        lo = mid
                sub = max(hi, 1e-6 * dt)
                s1, dv1 = step(s0, sub, d0, smode)
                dt = sub
        x, y, z, vx, vy, vz, m = s1
        dv += dv1
        ang = math.atan2(y, x)
        d_ang = (ang - ang_prev + math.pi) % (2.0 * math.pi) - math.pi
        revs += abs(d_ang) / (2.0 * math.pi)
        ang_prev = ang
        t += dt

    r = math.hypot(x, y, z)
    E = 0.5 * (vx * vx + vy * vy + vz * vz) - mu / r
    return _result(E)


def campaign_overhead_curve(a0: float, sch: Schedule, v_targets, isp_s: float = 2800.0,
                            power_cap: float = 4.0, max_yr: float = 60.0,
                            power_model: str = "cap"):
    """Overhead (Δv − v∞) of ONE campaign under ``sch`` at every target in ``v_targets``.

    A single integration toward the highest target records, at the first upward
    crossing of each target's specific energy, the (Δv, time, revolutions) spent
    so far (Δv linearly interpolated within the crossing step). This is how a
    fixed schedule prices every en-route target — the basis of the pumped
    budget's tax(v∞) table and the per-target campaign display. Returns
    [(v_target, overhead, years, revs), ...]; targets above what the campaign
    reaches within ``max_yr`` are omitted.
    """
    targets = sorted(float(v) for v in v_targets)
    if not targets:
        return []
    top = targets[-1]
    from .departure import _pump_power_factor
    pf = _pump_power_factor(power_model, power_cap)
    mu, AU = c.MU_SUN, c.AU
    out = []
    idx = 0
    prev_E = None
    prev_dv = 0.0

    # re-run the integrator loop with crossing bookkeeping (same physics/stepping)
    ve = isp_s * c.G0
    x, y, vx, vy, m = AU, 0.0, 0.0, math.sqrt(mu / AU), 1.0
    t, dv, revs, ang_prev = 0.0, 0.0, 0.0, 0.0
    latched = False
    max_t = max_yr * c.YEAR

    def step(state, dt, d):
        def deriv(s):
            X, Y, VX, VY, M = s
            rr = math.hypot(X, Y)
            vv = math.hypot(VX, VY) or 1.0
            am = (a0 * pf(rr) / max(M, 0.05) * d) if d else 0.0
            md = (-(a0 * pf(rr)) / ve) if d else 0.0
            g = -mu / rr ** 3
            return (VX, VY, g * X + am * VX / vv, g * Y + am * VY / vv, md)
        s = state
        k1 = deriv(s)
        k2 = deriv(tuple(s[i] + 0.5 * dt * k1[i] for i in range(5)))
        k3 = deriv(tuple(s[i] + 0.5 * dt * k2[i] for i in range(5)))
        k4 = deriv(tuple(s[i] + dt * k3[i] for i in range(5)))
        o = tuple(s[i] + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(5))
        o = (o[0], o[1], o[2], o[3], max(o[4], 0.05))
        if d:
            rr = math.hypot(s[0], s[1])
            return o, (a0 * pf(rr) / max(s[4], 0.05)) * dt
        return o, 0.0

    while t < max_t and idx < len(targets):
        r = math.hypot(x, y)
        E = 0.5 * (vx * vx + vy * vy) - mu / r
        while idx < len(targets) and E >= 0.5 * targets[idx] ** 2:
            tE = 0.5 * targets[idx] ** 2
            if prev_E is not None and E > prev_E:
                f = (tE - prev_E) / (E - prev_E)
                dv_c = prev_dv + f * (dv - prev_dv)
            else:
                dv_c = dv
            out.append((targets[idx], dv_c - targets[idx], t / c.YEAR, revs))
            idx += 1
        if idx >= len(targets) or E >= 0.5 * top ** 2:
            break
        prev_E, prev_dv = E, dv
        d0, rp0 = _decide(x, y, vx, vy, latched, sch, mu, AU)
        if not latched and rp0 <= sch.rp_latch * AU:
            latched = True
            d0, rp0 = _decide(x, y, vx, vy, latched, sch, mu, AU)
        period = 2.0 * math.pi * math.sqrt(max(r, 0.1 * AU) ** 3 / mu)
        dt = min(max(600.0, 0.002 * period), 5.0 * 86400.0)
        (x, y, vx, vy, m), dv_inc = step((x, y, vx, vy, m), dt, d0)
        dv += dv_inc
        ang = math.atan2(y, x)
        d_ang = (ang - ang_prev + math.pi) % (2.0 * math.pi) - math.pi
        revs += abs(d_ang) / (2.0 * math.pi)
        ang_prev = ang
        t += dt
    return out
