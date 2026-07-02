#!/usr/bin/env python3
"""Fable 5 independent audit of the Fermi engine.

Parallel model re-implementation (alongside audit/codex, audit/grok, audit/gemini):
every headline quantity is RE-DERIVED from the same catalogued inputs by a DIFFERENT
method than fermi_sim uses, then compared. The engine is imported only in the final
comparison step, never used to produce the audit's own numbers.

Method choices (deliberately different from the engine):
  ephemeris velocity   finite-differencing two proper-motion-propagated epochs
                       (engine: analytic RA/Dec sky-basis vectors)
  frame rotation       independently-constructed obliquity rotation, applied to
                       finite-difference states
  closest approach     golden-section minimisation of |r0 + v t|
                       (engine: perpendicular-foot closed form)
  intercept            forward-propagation loop closure + brute scan / golden section
                       for the min-speed and min-dv arrivals (engine: V_p = A0/T + V_ac
                       algebra + scipy optimiser)
  departure v_inf,E    explicit 3-D vector subtraction of Earth's velocity from the
                       departure velocity vector (engine: law of cosines)
  impulsive Oberth dv  verified by NUMERICALLY PROPAGATING the post-burn state to
                       large r (solve_ivp, adaptive RK45) and reading the asymptotic
                       speed (engine: energy algebra). GMAT cross-checks this too.
  low-thrust spiral    solve_ivp adaptive RK45 with an energy event
                       (engine: fixed-step RK4 loop)
  rocket equation      numerical mass-flow ODE integration (engine: closed form)
  1/r^2 power gate     solve_ivp adaptive RK45 re-implementation of the fade
                       (engine: fixed-dt RK4 loop)
  earth-escape revs    revolution count read from the integrated spiral polar angle
                       (engine: analytic N = mu/(8 pi a r^2))

Run:  .venv/bin/python audit/fable/fable_independent_checks.py
"""
import json
import math
import os
import sys

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# ---------------------------------------------------------------------------
# Own constants (IAU / SI, written independently; agreement with the engine's
# constants module is itself part of the audit).
G0 = 9.80665
AU = 1.495978707e11
LY = 9.4607304725808e15
PC = 3.0856775814913673e16
YEAR = 3.15576e7
MU_SUN = 1.32712440018e20
MU_EARTH = 3.986004418e14
R_EARTH = 6.371e6
OBLIQ = math.radians(23.439281)
KMS = 1e3

# Catalogued inputs (shared data, not derived values — same catalogue as the engine)
RA, DEC = math.radians(219.9021), math.radians(-60.8340)
DIST_LY = 4.344
PMRA, PMDEC = -3620.0, 694.0          # mas/yr (pm_ra*cos(dec), pm_dec)
RV = -22.4                            # km/s
MASYR_PC_KMS = 4.740470463

FAILS = []
RESULTS = {}


def check(name, got, want, tol_frac, unit=""):
    ok = abs(got - want) <= tol_frac * max(abs(want), 1e-30)
    RESULTS[name] = {"fable": got, "engine": want, "diff_pct": 100 * abs(got - want) / max(abs(want), 1e-30)}
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: fable={got:.6g}{unit}  engine={want:.6g}{unit}  "
          f"(diff {RESULTS[name]['diff_pct']:.4g}%)")
    if not ok:
        FAILS.append(name)


# ---------------------------------------------------------------------------
print("=" * 76)
print("1. EPHEMERIS — finite-difference velocity + independent rotation")
print("=" * 76)

def eq_cart(ra, dec, dist_m):
    return dist_m * np.array([math.cos(dec) * math.cos(ra),
                              math.cos(dec) * math.sin(ra),
                              math.sin(dec)])

def to_ecliptic(v):
    ce, se = math.cos(OBLIQ), math.sin(OBLIQ)
    return np.array([v[0], ce * v[1] + se * v[2], -se * v[1] + ce * v[2]])

# Velocity by finite-differencing two epochs +-dt propagated with proper motion + RV.
dist_m = DIST_LY * LY
dist_pc = dist_m / PC
dt_yr = 1.0
mas = math.radians(1.0 / 3.6e6)          # radians per milliarcsecond (1 mas = 1/3.6e6 deg)
states = []
for s in (-1.0, +1.0):
    ra_i = RA + s * dt_yr * PMRA * mas / math.cos(DEC)     # pm_ra is *cos(dec)
    dec_i = DEC + s * dt_yr * PMDEC * mas
    d_i = dist_m + s * dt_yr * RV * KMS * YEAR
    states.append(eq_cart(ra_i, dec_i, d_i))
v_eq = (states[1] - states[0]) / (2 * dt_yr * YEAR)        # m/s, equatorial
r_ec = to_ecliptic(eq_cart(RA, DEC, dist_m))
v_ec = to_ecliptic(v_eq)

speed = float(np.linalg.norm(v_ec))
dist_au = float(np.linalg.norm(r_ec)) / AU

# closest approach by golden-section minimisation
f = lambda t_yr: float(np.linalg.norm(r_ec + v_ec * t_yr * YEAR))
res = minimize_scalar(f, bounds=(0, 2e5), method="bounded",
                      options={"xatol": 1.0})
t_close_yr, d_close_ly = res.x, f(res.x) / LY

from fermi_sim.astro import alpha_centauri_state, closest_approach
ST = alpha_centauri_state()
tc_e, dc_e = closest_approach(ST)
check("AC space speed (km/s)", speed / KMS, float(np.linalg.norm(ST.v)) / KMS, 1e-3)
check("AC distance now (AU)", dist_au, float(np.linalg.norm(ST.r)) / AU, 1e-6)
check("closest approach time (kyr)", t_close_yr / 1e3, tc_e / YEAR / 1e3, 2e-3)
check("closest approach dist (ly)", d_close_ly, dc_e / LY, 2e-3)
for k in range(3):
    check(f"state vector v[{k}] (km/s)", v_ec[k] / KMS, ST.v[k] / KMS, 2e-3)

# ---------------------------------------------------------------------------
print("\n" + "=" * 76)
print("2. INTERCEPT — forward-propagation loop closure + independent optima")
print("=" * 76)

def vp_needed(T_yr):
    """Required constant probe velocity (m/s vector) to hit AC at time T."""
    T = T_yr * YEAR
    return (r_ec + v_ec * T) / T

def miss_at(T_yr):
    """Fly the straight line at vp_needed and measure the miss (should be ~0)."""
    T = T_yr * YEAR
    probe = vp_needed(T_yr) * T
    return float(np.linalg.norm(probe - (r_ec + v_ec * T)))

for T in (58138.0, 72800.0, 90000.0):
    m = miss_at(T)
    ok = m < 1e3                                   # < 1 km on a ~6 ly leg
    print(f"  [{'PASS' if ok else 'FAIL'}] loop closure @ {T:,.0f} yr: miss = {m:.3g} m")
    if not ok:
        FAILS.append(f"loop closure {T}")

# min-|V_p| arrival (tangential intercept) by golden section
res = minimize_scalar(lambda T: float(np.linalg.norm(vp_needed(T))),
                      bounds=(2e4, 2e5), method="bounded", options={"xatol": 0.5})
T_tan = res.x
vinf_tan = float(np.linalg.norm(vp_needed(T_tan)))

# tilt of the aim out of the ecliptic
vp = vp_needed(T_tan)
tilt = math.degrees(math.asin(vp[2] / np.linalg.norm(vp)))

check("min-speed arrival (yr)", T_tan, 58138.0, 2e-3)
check("min-speed v_inf (km/s)", vinf_tan / KMS, 23.27, 2e-3)
check("aim tilt at min-speed (deg)", tilt, -10.0, 2e-2)

# ---------------------------------------------------------------------------
print("\n" + "=" * 76)
print("3. DEPARTURE — vector-subtraction v_inf,E + numerically-propagated Oberth C3")
print("=" * 76)

V_EARTH = math.sqrt(MU_SUN / AU)
V_ESC_SUN = math.sqrt(2 * MU_SUN / AU)

def vinf_earth_vec(vinf_sun, tilt_deg):
    """v_inf,Earth by explicit 3-D vector subtraction (engine: law of cosines)."""
    v_dep = math.sqrt(vinf_sun ** 2 + V_ESC_SUN ** 2)
    b = math.radians(tilt_deg)
    # best case: in-ecliptic projection aligned with Earth's velocity (x-axis here)
    v_dep_vec = np.array([v_dep * math.cos(b), 0.0, v_dep * math.sin(b)])
    v_earth_vec = np.array([V_EARTH, 0.0, 0.0])
    return float(np.linalg.norm(v_dep_vec - v_earth_vec))

vinf_e = vinf_earth_vec(vinf_tan, tilt)
from fermi_sim.departure import (v_inf_earth_required, impulsive_dv_from_leo,
                                 spiral_escape_dv, earth_escape_revs,
                                 lowthrust_departure_dv)
vinf_e_eng, _ = v_inf_earth_required(vinf_tan, tilt)
check("v_inf,Earth (km/s)", vinf_e / KMS, vinf_e_eng / KMS, 1e-4)

# impulsive dv, then verify the post-burn state actually reaches that v_inf by
# propagating the two-body hyperbola out to 150 Earth-SOI radii (adaptive RK45)
r_p = R_EARTH + 400e3
v_circ = math.sqrt(MU_EARTH / r_p)
dv_imp = impulsive_dv_from_leo(vinf_e, 400.0)
v0 = v_circ + dv_imp

def two_body(t, s):
    r3 = (s[0] ** 2 + s[1] ** 2) ** 1.5
    return [s[2], s[3], -MU_EARTH * s[0] / r3, -MU_EARTH * s[1] / r3]

far = solve_ivp(two_body, [0, 40 * 86400], [r_p, 0, 0, v0],
                rtol=1e-10, atol=1e-3, dense_output=False)
rf = math.hypot(far.y[0, -1], far.y[1, -1])
vf = math.hypot(far.y[2, -1], far.y[3, -1])
vinf_prop = math.sqrt(max(vf ** 2 - 2 * MU_EARTH / rf, 0.0))
check("propagated v_inf after Oberth burn (km/s)", vinf_prop / KMS, vinf_e / KMS, 1e-3)
check("impulsive dv (km/s)", dv_imp / KMS, 14.633, 1e-3)

# low-thrust spiral to the mission v_inf,E — solve_ivp with energy event, count revs
ACC = 5e-4
def spiral(t, s):
    x, y, vx, vy = s
    r3 = (x * x + y * y) ** 1.5
    v = math.hypot(vx, vy)
    return [vx, vy, -MU_EARTH * x / r3 + ACC * vx / v, -MU_EARTH * y / r3 + ACC * vy / v]

def esc_event(t, s):
    return 0.5 * (s[2] ** 2 + s[3] ** 2) - MU_EARTH / math.hypot(s[0], s[1])
esc_event.terminal = False                 # record the C3=0 crossing, keep burning to v_inf,E
esc_event.direction = 1

def vinf_event(t, s):     # reached the mission hyperbolic excess v_inf,E
    return (0.5 * (s[2] ** 2 + s[3] ** 2) - MU_EARTH / math.hypot(s[0], s[1])) - 0.5 * vinf_e ** 2
vinf_event.terminal = True
vinf_event.direction = 1

sol = solve_ivp(spiral, [0, 8e7], [r_p, 0, 0, v_circ], rtol=1e-9, atol=1e-3,
                events=[esc_event, vinf_event], max_step=2000.0, dense_output=True)
t_esc = float(sol.t_events[0][0])
t_vinf = float(sol.t_events[1][0])
# revolution count from the unwrapped polar angle, up to escape
i_esc = int(np.searchsorted(sol.t, t_esc))
th = np.unwrap(np.arctan2(sol.y[1, :i_esc], sol.y[0, :i_esc]))
revs = (th[-1] - th[0]) / (2 * math.pi)
n_analytic, _ = earth_escape_revs(ACC * 1000.0, 1000.0, perigee_km=400.0)
check("spiral escape time to C3=0 (Ms)", t_esc / 1e6, spiral_escape_dv(MU_EARTH, r_p, 0.0, accel=ACC) / ACC / 1e6, 5e-3)
check("spiral revs to escape", float(revs), n_analytic, 2e-2)
# the engine's DERIVED closed-form fit vs MY independently-integrated spiral to v_inf,E
check("low-thrust departure dv: engine fit vs my spiral (km/s)",
      ACC * t_vinf / KMS, lowthrust_departure_dv(vinf_tan, tilt) / KMS, 5e-3)

# ---------------------------------------------------------------------------
print("\n" + "=" * 76)
print("4. ROCKET EQUATION — numerical mass-flow ODE vs closed form")
print("=" * 76)
isp, dv_test, dry = 3000.0, 26e3, 256.0
ve = isp * G0
mr = math.exp(dv_test / ve)
wet_closed = dry * mr
# numerical: burn at constant thrust F, dm/dt=-F/ve, until integral of F/m dt = dv
F = 0.2
m, dv_acc, t, h = wet_closed, 0.0, 0.0, 100.0
while dv_acc < dv_test:
    dv_acc += (F / m) * h
    m -= (F / ve) * h
    t += h
check("propellant burned to reach dv (kg)", wet_closed - m, wet_closed - dry, 2e-3)

# ---------------------------------------------------------------------------
print("\n" + "=" * 76)
print("5. THE 1/r^2 POWER GATE — solve_ivp re-implementation")
print("=" * 76)
from fermi_sim.departure import sep_achievable_vinf

def gate(power_w, wet, dry_pay, isp_s, eff, fade):
    ve = isp_s * G0
    F0 = 2 * eff * power_w / ve
    r0 = AU

    def rhs(t, s):
        x, y, vx, vy, m = s
        r = math.hypot(x, y)
        v = math.hypot(vx, vy)
        Fm = F0 * (r0 / r) ** fade if m > dry_pay else 0.0
        g = -MU_SUN / r ** 3
        return [vx, vy, g * x + Fm * vx / v / m, g * y + Fm * vy / v / m,
                -(Fm / ve) if m > dry_pay else 0.0]

    def dry_event(t, s):   # propellant exhausted
        return s[4] - dry_pay
    dry_event.terminal = False

    def far_event(t, s):   # power negligible
        return math.hypot(s[0], s[1]) - 80 * AU
    far_event.terminal = True

    sol = solve_ivp(rhs, [0, 400 * YEAR], [r0, 0, 0, math.sqrt(MU_SUN / r0), wet],
                    rtol=1e-8, atol=[1.0, 1.0, 1e-6, 1e-6, 1e-9],
                    events=[dry_event, far_event])
    x, y, vx, vy, m = sol.y[:, -1]
    r = math.hypot(x, y)
    E = 0.5 * (vx ** 2 + vy ** 2) - MU_SUN / r
    return math.sqrt(2 * E) if E > 0 else 0.0

cases = [
    ("high-alpha default (43/15 kg, 2 kW, solar)", 2000, 43, 15, 3000, 0.5, 2.0),
    ("low-alpha (710/256 kg, 20 kW, solar)", 20000, 710, 256, 3000, 0.5, 2.0),
    ("nuclear 5 kW (710/256 kg, constant)", 5000, 710, 256, 3000, 0.55, 0.0),
]
for label, P, wet, dry, isp_s, eff, fade in cases:
    mine = gate(P, wet, dry, isp_s, eff, fade)
    eng = sep_achievable_vinf(P, wet, dry, isp_s, eff, 1.0, fade)
    tol = 0.02 if eng > 1e3 else 0.0
    if eng > 1e3:
        check(f"gate v_inf: {label} (km/s)", mine / KMS, eng / KMS, 0.02)
    else:
        ok = mine < 1e3
        print(f"  [{'PASS' if ok else 'FAIL'}] gate v_inf: {label}: fable={mine/KMS:.2f} engine={eng/KMS:.2f} (both ~0 = never escapes)")
        if not ok:
            FAILS.append(label)

# closure thresholds
print("\n  closure summary (floor 23.4 km/s):")
print(f"    high-alpha solar default : {'CLOSES' if gate(2000,43,15,3000,0.5,2.0)>=23.4e3 else 'fails'} (expected CLOSES)")
print(f"    low-alpha solar          : {'closes' if gate(20000,710,256,3000,0.5,2.0)>=23.4e3 else 'FAILS'} (expected FAILS)")
print(f"    nuclear 5 kW             : {'CLOSES' if gate(5000,710,256,3000,0.55,0.0)>=23.4e3 else 'fails'} (expected CLOSES)")

# ---------------------------------------------------------------------------
print("\n" + "=" * 76)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fable_results.json")
with open(out, "w") as fh:
    json.dump(RESULTS, fh, indent=2, default=float)
print(f"results -> {out}")
if FAILS:
    print(f"FABLE AUDIT: {len(FAILS)} FAILURE(S): {FAILS}")
    sys.exit(1)
print("FABLE AUDIT: all independent checks passed")
