"""Departure energetics: LEO -> required heliocentric v_inf.

Two regimes:

* Impulsive (chemical-like): a single burn at LEO perigee gets the full Oberth
  benefit. This is the theoretical *floor* on departure delta-v.

* Low-thrust (ion): thrust is spread over many revolutions, so the Oberth
  benefit is largely lost and the vehicle must spiral out of Earth's gravity
  well. We quantify this penalty by numerically integrating a constant-
  tangential-thrust spiral, rather than assuming a fudge factor.

Both regimes start from the same patched-conic requirement: to leave on a
heliocentric hyperbola with excess speed ``v_inf_sun`` (in a direction tilted
``plane_angle`` out of the ecliptic), the vehicle needs heliocentric speed
``v_dep = sqrt(v_inf_sun^2 + v_esc_sun^2)`` at 1 AU. Earth supplies 29.8 km/s of
that *in the ecliptic plane only*; the out-of-plane part must be paid in full.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import constants as c


def leo_speeds(altitude_km: float) -> tuple[float, float]:
    """Circular and escape speed at the given LEO altitude (m/s)."""
    r = c.R_EARTH + altitude_km * 1e3
    v_circ = math.sqrt(c.MU_EARTH / r)
    v_esc = math.sqrt(2.0 * c.MU_EARTH / r)
    return v_circ, v_esc


def v_inf_earth_required(v_inf_sun: float, plane_angle_deg: float) -> float:
    """Hyperbolic excess speed *relative to Earth* needed at departure.

    Best-case launch geometry: the in-ecliptic projection of the departure
    velocity is aligned with Earth's orbital motion, so Earth's 29.8 km/s is
    fully borrowed in-plane. The out-of-plane tilt ``beta`` cannot be borrowed.
    """
    v_dep = math.sqrt(v_inf_sun**2 + c.V_ESC_SUN_1AU**2)  # helio speed at 1 AU
    beta = math.radians(plane_angle_deg)
    # Law of cosines with the angle between V_dep and Earth's (in-plane) velocity
    # minimised to beta (align the in-plane projection with Earth's motion), in the
    # cancellation-free half-angle form:
    #   v² + V² − 2vV·cosβ  ==  (v − V)² + 4vV·sin²(β/2)
    # (both terms non-negative, so no near-equal subtraction for small β).
    s = math.sin(0.5 * beta)
    v_inf_e_sq = (v_dep - c.V_EARTH_ORBITAL) ** 2 + 4.0 * v_dep * c.V_EARTH_ORBITAL * s * s
    return math.sqrt(v_inf_e_sq), v_dep


# --- Derived low-thrust departure fit (Plan 02, Phase A: naïve constant-tangential spiral) ---
# Closed form for the integrated `spiral_escape_dv` so the web tool evaluates it instantly
# (no live integration) while staying DERIVED, not a hand-set penalty. Generated and validated
# by `tools/fit_spiral.py`: Δv = v_circ(alt) + C0 + C1·v∞,E  (SI, m/s). The (Δv − v_circ)
# curve is altitude-independent to 0.8 m/s, and this fit matches the integration to 0.5 m/s
# (<0.01%) over v∞,E ∈ [8, 32] km/s — the only band that occurs for feasible interstellar aims.
_SPIRAL_FIT_C0 = -1173.491  # m/s
_SPIRAL_FIT_C1 = 0.999997
# Starting-orbit generalisation (Plan 02 follow-up): the spiral Δv depends on the orbit ENERGY,
# i.e. the semi-major axis a — v_circ → sqrt(mu/a) — plus a small eccentricity correction (zero
# for circular). Δv = sqrt(mu/a) + C0 + C1·v∞,E + CE1·e + CE2·e²; matches the integrated spiral
# to ~25 m/s up to e=0.7 (validated in audit_departure.py; coefficients from tools/fit_spiral.py).
_SPIRAL_FIT_CE1 = 85.4   # m/s
_SPIRAL_FIT_CE2 = 284.8  # m/s
# Fraction of the circular speed the constant-tangential spiral actually spends to reach C3=0
# (parabolic escape), vs the r→∞ Edelbaum asymptote of v_circ. Mildly acceleration-dependent
# (~0.95 at a≈1e-4, ~0.94 at the design band, ~0.87 at a≈5e-3); 0.93 holds the SEP band to ≲1 %.
_C3_ESCAPE_FRAC = 0.93
# Lower edge (m/s) of the corridor where pumped_departure_dv's flat 2 km/s tax is honest —
# below this the integrated campaign overhead is ~8-13 km/s and the flat tax underprices,
# so the function refuses (see its docstring). The AC aim geometry never goes below the
# 23.27 km/s tangential floor, so shipped callers sit comfortably inside.
PUMP_TAX_VINF_MIN = 20.0e3


def lowthrust_departure_dv(
    v_inf_sun: float, plane_angle_deg: float, perigee_km: float = 400.0,
    apogee_km: float | None = None,
) -> float:
    """Derived naïve low-thrust Earth-escape Δv (m/s) from a starting orbit — the design budget.

    Circular start: apogee_km defaults to perigee_km (reduces exactly to the Phase A fit). For an
    elliptical start a higher apogee carries more orbital energy, so the ion has less to spiral:
    v_circ → sqrt(mu/a), plus a small eccentricity correction. Closed form of the integrated
    constant-tangential spiral (`spiral_escape_dv`); the audit suite re-checks it vs integration.
    """
    if apogee_km is None:
        apogee_km = perigee_km
    apogee_km = max(apogee_km, perigee_km)
    v_inf_e, _ = v_inf_earth_required(v_inf_sun, plane_angle_deg)
    r_p = c.R_EARTH + perigee_km * 1e3
    r_a = c.R_EARTH + apogee_km * 1e3
    a = 0.5 * (r_p + r_a)
    e = (r_a - r_p) / (r_a + r_p)
    v_a = math.sqrt(c.MU_EARTH / a)        # circular speed at the semi-major axis (energy proxy)
    return (v_a + _SPIRAL_FIT_C0 + _SPIRAL_FIT_C1 * v_inf_e
            + _SPIRAL_FIT_CE1 * e + _SPIRAL_FIT_CE2 * e * e)


def earth_escape_revs(thrust_n: float, mass_kg: float, perigee_km: float = 590.0):
    """Revolutions and time to spiral from a circular LEO to Earth-escape (C3=0) under constant
    tangential thrust at acceleration a = thrust/mass. ANALYTIC near-circular result (derived; see
    tmp/ro/revcount.py, audit_departure.py):

        N = mu / (8·pi·a·r_p²)        t_escape ≈ 0.93·v_circ(r_p) / a

    The revolution count matches the geocentric RK integration to ~0.2 %. The time is the C3=0
    (parabolic) escape, which the constant-tangential spiral reaches at a Δv of ~0.93·v_circ — NOT
    the full v_circ (that is the r→∞ Edelbaum asymptote, which overstates the escape time by ~7.6 %
    and disagrees with the engine's own spiral_escape_dv and the GMAT column). The 0.93 fraction is
    mildly acceleration-dependent (~0.95 at a≈1×10⁻⁴, ~0.94 at the a≈3×10⁻⁴ design band, ~0.87 at
    a≈5×10⁻³); 0.93 holds the SEP band to ≲1 %. Design-responsive (a = thrust/wet mass) and instant.
    """
    a = thrust_n / max(mass_kg, 1.0)
    if a <= 0.0:
        return 0.0, 0.0
    r_p = c.R_EARTH + perigee_km * 1e3
    n = c.MU_EARTH / (8.0 * math.pi * a * r_p * r_p)
    t_yr = (_C3_ESCAPE_FRAC * math.sqrt(c.MU_EARTH / r_p) / a) / c.YEAR
    return n, t_yr


def sun_escape_revs(thrust_n: float, mass_kg: float, r0_au: float = 1.0) -> float:
    """Revolutions around the Sun while the ion spirals the heliocentric orbit out from r0 (≈1 AU)
    to solar escape under constant tangential thrust (a = thrust/mass) — the same near-circular
    result with the Sun's gravity:  N = mu_sun / (8·pi·a·r0²).  The interstellar coast that follows
    is a straight cruise (no orbiting), so this is effectively the total number of turns around the
    Sun — typically < 1, in stark contrast to the ~hundreds of revolutions to climb out of Earth.
    """
    a = thrust_n / max(mass_kg, 1.0)
    if a <= 0.0:
        return 0.0
    r0 = r0_au * c.AU
    return c.MU_SUN / (8.0 * math.pi * a * r0 * r0)


def earth_soi_radius(r_sun_au: float = 1.0) -> float:
    """Earth's sphere-of-influence radius (m):  r_SOI = a · (m_earth/m_sun)^(2/5), with a the
    Earth–Sun distance and the mass ratio taken from the GM ratio (μ⊕/μ☉). This is the orbit the
    low-thrust spiral must reach to leave Earth's gravity — i.e. the physical RADIUS of the
    escape disk (≈ 9.24×10⁵ km ≈ 145 R⊕; diameter ≈ 290 R⊕ ≈ 0.0124 AU).
    """
    a = r_sun_au * c.AU
    return a * (c.MU_EARTH / c.MU_SUN) ** 0.4


def injection_pointing_dv(sigma_deg: float, alt_km: float = 590.0) -> float:
    """Correction Δv (m/s) for an RMS pointing error in the LEO injection velocity. A direction
    error σ at the circular parking-orbit speed must be re-aimed onto the departure asymptote;
    the velocity-vector correction of magnitude σ at speed v_circ is Δv = 2·v_circ·sin(σ/2).
    """
    if sigma_deg <= 0.0:
        return 0.0
    v_circ = math.sqrt(c.MU_EARTH / (c.R_EARTH + alt_km * 1e3))
    return 2.0 * v_circ * math.sin(math.radians(sigma_deg) / 2.0)


def gnc_steering_factor(sigma_deg: float) -> float:
    """Cosine steering-loss factor for an RMS thrust-pointing error σ during the orbit-raising
    spiral & escape: only cos σ of the thrust is useful, so the required Δv inflates by sec σ.
    Returns the multiplier (≥ 1) to apply to the ideal spiral Δv.
    """
    return 1.0 / math.cos(math.radians(max(0.0, min(89.0, sigma_deg))))


def perihelion_pumped_vinf(
    a0: float, v_inf_target: float, isp_s: float = 2800.0,
    rp_min_au: float = 0.42, power_cap: float = 4.0, max_yr: float = 60.0,
):
    """Multi-revolution PERIHELION-PUMPING escape from a 1 AU circular heliocentric orbit.
    The conventional outward spiral saturates below the cruise floor because solar power
    fades 1/r²; pumping inverts the logic:
    retrograde thrust arcs near apoapsis shed angular momentum until perihelion reaches
    ``rp_min_au`` (where the thermal cap engages), then prograde arcs concentrate at
    perihelion where power is `power_cap`× the 1-AU rating and the Oberth effect is
    strongest. Successive revolutions staircase the orbit energy up to the target.

    Power model:  P(r) = P1 · min((1 AU/r)², power_cap); thrust ∝ P at fixed
    Isp, so accel = a0 · min((1/r)², cap) · (m0/m).  ``a0`` is the initial thrust
    acceleration at 1 AU and full mass (m/s²) — the single sizing parameter.

    Bang-bang policy, exactly as implemented below (an optimised burn schedule does ~7%
    better on Δv): (1) BOOTSTRAP — from near-circular (ecc < 0.05) burn retrograde only on
    one inertial side (x > 0), which builds eccentricity instead of spiralling down
    symmetrically; (2) PUMP-DOWN — retrograde only near apoapsis (||ν|−π| < 60°) until the
    osculating perihelion reaches ``rp_min_au``, then a one-way latch holds the phase;
    (3) STAIRCASE — prograde only near periapsis (|ν| < 70°) and only while comfortably
    bound (E < −30 km²/s²; the escape guard — tipping past E=0 mid-staircase strands the
    probe below target); (4) FINISHER — once near-parabolic, burn continuously.

    CAUTION — the policy's success is NOT monotonic in ``a0`` (burn phasing relative to
    periapsis matters): the contiguous working region starts at a0 ≈ 2.24×10⁻⁴ m/s² (for
    the 23.64 km/s target), but there is a success island near 1.75–1.88×10⁻⁴, a strand
    band at 1.9–2.2×10⁻⁴, and a stall window near 2.9–3.1×10⁻⁴. Gate designs by CALLING
    this function at the design a0 (and remember a stronger vehicle can always throttle
    to a working profile); do not treat 2.25×10⁻⁴ as a simple threshold.

    Returns (v_inf_achieved m/s, dv m/s, years, revs). Succeeds if the specific energy
    reaches v_inf_target²/2 within ``max_yr``. Achieved v∞ can overshoot the target by up
    to ~1% of v∞ (one time-step of thrust); the overshoot is discretisation, not physics.
    """
    for nm, val in (("a0", a0), ("v_inf_target", v_inf_target), ("isp_s", isp_s),
                    ("rp_min_au", rp_min_au), ("power_cap", power_cap), ("max_yr", max_yr)):
        if not math.isfinite(val):
            raise ValueError(f"perihelion_pumped_vinf: {nm} must be finite, got {val!r}")
    if a0 <= 0.0 or v_inf_target <= 0.0 or isp_s <= 0.0 or max_yr <= 0.0:
        raise ValueError("perihelion_pumped_vinf: a0, v_inf_target, isp_s and max_yr must be positive")
    if not 0.0 < rp_min_au < 1.0:
        raise ValueError("perihelion_pumped_vinf: rp_min_au must be in (0, 1) AU — the campaign starts at 1 AU")
    if power_cap < 1.0:
        raise ValueError("perihelion_pumped_vinf: power_cap is a multiple of the 1-AU rating and must be >= 1")
    mu, AU = c.MU_SUN, c.AU
    ve = isp_s * c.G0
    target_E = 0.5 * v_inf_target ** 2
    x, y = AU, 0.0
    vx, vy = 0.0, math.sqrt(mu / AU)
    m = 1.0                                     # mass fraction; F0/m0 = a0
    t = 0.0
    dv = 0.0
    ang_prev = 0.0
    revs = 0.0
    max_t = max_yr * c.YEAR
    pumped_down = False                          # one-way latch: once periapsis reaches
                                                 # rp_min, stay in the energy-staircase
                                                 # phase (else the policy dithers)

    def accel_mag(r):
        return a0 * min((AU / r) ** 2, power_cap) / m

    while t < max_t:
        r = math.hypot(x, y)
        v2 = vx * vx + vy * vy
        E = 0.5 * v2 - mu / r
        if E >= target_E:
            return math.sqrt(2.0 * E), dv, t / c.YEAR, revs
        # osculating elements
        h = x * vy - y * vx
        ecc = math.sqrt(max(0.0, 1.0 + 2.0 * E * h * h / (mu * mu)))
        p_sl = h * h / mu
        rp = p_sl / (1.0 + ecc)
        # true anomaly from the orbit geometry (sign from the radial velocity)
        rdot_sign = 1.0 if (x * vx + y * vy) >= 0.0 else -1.0
        if ecc > 1e-6:
            cnu = max(-1.0, min(1.0, (p_sl / r - 1.0) / ecc))
            nu = rdot_sign * math.acos(cnu)                # (-pi, pi], 0 = periapsis
        else:
            nu = 0.0
        if rp <= rp_min_au * AU:
            pumped_down = True
        if not pumped_down:
            if ecc < 0.05:
                # bootstrap from near-circular: fire retrograde on one inertial side only,
                # which builds eccentricity instead of spiralling down symmetrically
                thrust_dir = -1.0 if x > 0.0 else 0.0
            else:
                # retrograde only near APOAPSIS (|nu - pi| < 60 deg): lowers periapsis,
                # keeps apoapsis — the pump-down arc
                thrust_dir = -1.0 if abs(abs(nu) - math.pi) < math.radians(60.0) else 0.0
        elif E < -3.0e7:
            # energy staircase with an ESCAPE GUARD: prograde only near periapsis
            # (|nu| < 70 deg), and only while E stays comfortably bound (< -30 km²/s²) —
            # tipping past E=0 mid-staircase strands the probe below the target
            thrust_dir = +1.0 if abs(nu) < math.radians(70.0) else 0.0
        else:
            # FINISHER: near-parabolic — one full-power pass through periapsis (plus the
            # fading outward tail) delivers the remaining excess; burn continuously
            thrust_dir = +1.0
        amag = accel_mag(r) if thrust_dir else 0.0
        period = 2.0 * math.pi * math.sqrt(max(r, 0.1 * AU) ** 3 / mu)
        dt = min(max(600.0, 0.002 * period), 5.0 * 86400.0)

        def deriv(s):
            X, Y, VX, VY = s
            rr = math.hypot(X, Y)
            vv = math.hypot(VX, VY) or 1.0
            am = (accel_mag(rr) * thrust_dir) if thrust_dir else 0.0
            g = -mu / rr ** 3
            return (VX, VY, g * X + am * VX / vv, g * Y + am * VY / vv)

        s = (x, y, vx, vy)
        k1 = deriv(s)
        k2 = deriv(tuple(s[i] + 0.5 * dt * k1[i] for i in range(4)))
        k3 = deriv(tuple(s[i] + 0.5 * dt * k2[i] for i in range(4)))
        k4 = deriv(tuple(s[i] + dt * k3[i] for i in range(4)))
        x += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        y += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        vx += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        vy += dt / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
        if thrust_dir:
            dv += amag * dt
            m = max(0.05, m - (a0 * min((AU / r) ** 2, power_cap) / ve) * dt)
        ang = math.atan2(y, x)
        d_ang = ang - ang_prev
        if d_ang > math.pi:
            d_ang -= 2 * math.pi
        elif d_ang < -math.pi:
            d_ang += 2 * math.pi
        revs += abs(d_ang) / (2 * math.pi)
        ang_prev = ang
        t += dt
    r = math.hypot(x, y)
    E = 0.5 * (vx * vx + vy * vy) - mu / r
    return (math.sqrt(2.0 * E) if E > 0 else 0.0), dv, t / c.YEAR, revs


def synchrotron_escape(
    rp_rsun: float, dv_pass: float, v_inf_target: float, max_passes: int = 10000,
) -> dict:
    """PERIHELION SYNCHROTRON — an externally powered recirculating accelerator. A station
    (itself Sun-orbiting, circular at radius ``rp_rsun`` solar radii — it cannot hover)
    applies one impulsive prograde kick of ``dv_pass`` (m/s) per probe pass through
    perihelion; between kicks the probe flies an EXACT Kepler
    ellipse (the probe itself is passive — no onboard propellant or power; continuing the
    synchrotron analogy, the Sun's gravity stands in for the bending magnets that curve the
    path back to the accelerating station). It is not a true synchrotron even by analogy:
    the apoapsis and period GROW after every kick, so it is a recirculating "linac" whose
    return path balloons.

    Two corrections that kill the naive equal-kick arithmetic (both enforced here):
      1. Orbit periods are NOT constant — t = Σ Pᵢ over each bound orbit; as v_p → v_esc
         the period diverges, so the LAST bound orbit can dominate the schedule.
      2. Escape TERMINATES recirculation — once a kick makes the orbit hyperbolic the
         probe leaves and never returns, so the final kick must jump from bound directly
         to ≥ v_p,target = √(v∞² + v_esc²). A kick that clears escape but lands BELOW
         v_p,target means the probe is gone too slow → INFEASIBLE (``escaped_below``).

    Starts from the circular orbit at the station radius. Returns a dict with passes,
    accel-phase time, max single period, Δv_final_min = v_target − v_esc, the station↔probe
    rendezvous speed ≈ (√2−1)·v_circ(r_p), and the feasibility verdict.
    """
    for nm, val in (("rp_rsun", rp_rsun), ("dv_pass", dv_pass), ("v_inf_target", v_inf_target)):
        if not math.isfinite(val):
            raise ValueError(f"synchrotron_escape: {nm} must be finite, got {val!r}")
    if rp_rsun <= 0.0 or dv_pass <= 0.0 or v_inf_target <= 0.0 or max_passes < 1:
        raise ValueError("synchrotron_escape: rp_rsun, dv_pass and v_inf_target must be "
                         "positive and max_passes >= 1")
    r_p = rp_rsun * c.R_SUN
    v_esc = math.sqrt(2.0 * c.MU_SUN / r_p)
    v_target = math.sqrt(v_inf_target ** 2 + v_esc ** 2)
    dv_final_min = v_target - v_esc
    v = math.sqrt(c.MU_SUN / r_p)                  # circular start at the station
    passes, t, e_station, max_period = 0, 0.0, 0.0, 0.0
    escaped_below = False
    left_at_target = False
    while passes < max_passes:
        v2 = v + dv_pass
        e_station += 0.5 * (v2 * v2 - v * v)       # specific energy the station delivers
        passes += 1
        v = v2
        if v >= v_target:                          # leaves at ≥ target v∞ → feasible
            left_at_target = True
            break
        if v >= v_esc:                             # hyperbolic but slow → gone forever
            escaped_below = True
            break
        eps = 0.5 * v * v - c.MU_SUN / r_p         # still bound → fly the return ellipse
        a = -c.MU_SUN / (2.0 * eps)
        period = 2.0 * math.pi * math.sqrt(a ** 3 / c.MU_SUN)
        t += period
        max_period = max(max_period, period)
    v_inf_final = math.sqrt(max(v * v - v_esc * v_esc, 0.0))
    v_circ = math.sqrt(c.MU_SUN / r_p)
    return dict(
        passes=passes, time_yr=t / c.YEAR, max_period_yr=max_period / c.YEAR,
        v_peri_final=v, v_inf_final=v_inf_final, v_esc=v_esc, v_target=v_target,
        dv_final_min=dv_final_min, energy_spec=e_station,
        rendezvous_vel=(math.sqrt(2.0) - 1.0) * v_circ,   # worst case: the near-escape pass
        escaped_below=escaped_below,
        # reached only when the loop actually left at >= v_target — a max_passes
        # exhaustion inside a tolerance window must NOT count as success
        reached=left_at_target and not escaped_below,
    )


def pumped_departure_dv(v_inf: float, tilt_deg: float, peri_alt_km: float,
                        apo_alt_km: float | None = None, pump_tax: float = 2000.0) -> float:
    """First-order total departure Δv (m/s) for the PERIHELION-PUMPED architecture, as a
    two-leg budget: (1) low-thrust Earth escape to C3 ≈ 0, costed at the orbit-energy speed
    √(μ⊕/a) of the starting orbit (the classic Edelbaum spiral-to-escape result; ~7.7 km/s
    from 400 km LEO, ~4.0 km/s from a GTO-like ellipse — conservative vs the integrated
    spiral by ~0.25–0.45 km/s), then (2) the heliocentric pumping campaign, priced
    v∞ + v∞·|sin β| + ``pump_tax``: the campaign is integrated in-plane, so the
    out-of-plane component of the aim (tilt β) is charged separately as a first-order
    plane change v∞·|sin β| (~1 km/s at the 73 kyr aim, ~4 km/s at the 58 kyr tangential
    aim), and the tax covers the in-plane overhead (pump-down arcs + gravity losses),
    calibrated against :func:`perihelion_pumped_vinf` at the design corridor
    (Δv − v∞ ≈ 2.0 km/s at a₀ = 2.5×10⁻⁴, v∞ ≈ 23.6 km/s). The flat tax is exact ONLY near
    the AC corridor (v∞ ≈ 23–25 km/s): re-integrating the policy at the design a₀, the true
    campaign overhead (Δv − v∞) is ~13.5 km/s at v∞=8, ~11.7 at v∞=10, ~7.8 at v∞=15, falling
    through 2.0 at v∞≈23.6 and to ≈0 by v∞=30. So this two-leg budget UNDERPRICES low-v∞
    targets by ~10 km/s. The corridor is therefore ENFORCED: v_inf below
    ``PUMP_TAX_VINF_MIN`` (20 km/s) raises ValueError — price such targets by integrating
    :func:`perihelion_pumped_vinf` at the target (its returned dv IS the campaign leg,
    v∞ + true overhead). Above the corridor the flat tax overprices slightly
    (conservative), so no upper guard. Unlike the outward-spiral budget this does NOT
    borrow Earth's orbital velocity — v∞ is built heliocentrically at perihelion.
    """
    for nm, val in (("v_inf", v_inf), ("tilt_deg", tilt_deg), ("peri_alt_km", peri_alt_km),
                    ("pump_tax", pump_tax)):
        if not math.isfinite(val):
            raise ValueError(f"pumped_departure_dv: {nm} must be finite, got {val!r}")
    if v_inf < PUMP_TAX_VINF_MIN:
        raise ValueError(
            f"pumped_departure_dv: v_inf {v_inf/1e3:.1f} km/s is below the calibrated corridor "
            f"({PUMP_TAX_VINF_MIN/1e3:.0f} km/s) — the flat {pump_tax/1e3:.1f} km/s tax underprices the "
            "campaign there (true overhead ~8-13 km/s). Integrate perihelion_pumped_vinf at this "
            "target instead; its returned dv is the correctly-priced campaign leg.")
    r_p = c.R_EARTH + peri_alt_km * 1e3
    r_a = c.R_EARTH + max(apo_alt_km if apo_alt_km is not None else peri_alt_km, peri_alt_km) * 1e3
    a = 0.5 * (r_p + r_a)
    plane = v_inf * abs(math.sin(math.radians(tilt_deg)))
    return math.sqrt(c.MU_EARTH / a) + v_inf + plane + pump_tax


def sep_achievable_vinf(power_w: float, wet_kg: float, dry_pay_kg: float, isp_s: float,
                        eff: float = 0.5, r0_au: float = 1.0, fade_exp: float = 2.0) -> float:
    """Maximum heliocentric excess speed v∞ (m/s) a solar-electric probe can actually reach from a
    1-AU circular heliocentric orbit, accounting for the 1/r² SOLAR-POWER FADE that throttles the
    thrust as the probe recedes. This is the decisive conservative feasibility quantity: because
    power ∝ 1/r², the achievable v∞ SATURATES — extra propellant burnt far out adds little, so
    practical SEP masses fall below the ~23.4 km/s cruise floor.

    F(r) = 2·η·P0/(v_e·r²) (thrust prograde), ṁ = F/v_e, RK4 in SI. Integrate from 1-AU circular
    until the propellant is spent OR the probe coasts far enough that power is negligible, then
    v∞ = sqrt(2·E) for the specific orbital energy E (0 if it never reaches escape).
    """
    for nm, val in (("power_w", power_w), ("wet_kg", wet_kg), ("dry_pay_kg", dry_pay_kg),
                    ("isp_s", isp_s), ("eff", eff), ("r0_au", r0_au), ("fade_exp", fade_exp)):
        if not math.isfinite(val):
            raise ValueError(f"sep_achievable_vinf: {nm} must be finite, got {val!r}")
    if not 0.0 < eff <= 1.0 or r0_au <= 0.0 or fade_exp < 0.0:
        raise ValueError("sep_achievable_vinf: need 0 < eff <= 1, r0_au > 0, fade_exp >= 0")
    ve = isp_s * c.G0
    m_p = wet_kg - dry_pay_kg
    if m_p <= 0.0 or power_w <= 0.0 or ve <= 0.0:
        return 0.0                     # physical sentinel: no propellant/power/exhaust -> v_inf 0
    mu, r0 = c.MU_SUN, r0_au * c.AU
    F0 = 2.0 * eff * power_w / ve            # thrust at 1 AU (N)
    rx, ry = r0, 0.0
    vx, vy = 0.0, math.sqrt(mu / r0)         # circular at 1 AU
    m = wet_kg
    dt = 5.0e4                                # s
    t = 0.0
    R_FAR = 80.0 * c.AU                       # beyond here power is negligible — stop, read v∞
    T_CAP = 400.0 * c.YEAR

    def deriv(state, mass):
        x, y, vxx, vyy = state
        r = math.hypot(x, y) or 1.0
        sp = math.hypot(vxx, vyy) or 1.0
        # fade_exp=2 → solar 1/r² power fade; fade_exp=0 → constant power (nuclear-electric)
        Fm = F0 * (r0 / r) ** fade_exp if mass > dry_pay_kg else 0.0
        ag = -mu / (r * r * r)
        return [vxx, vyy, ag * x + Fm * vxx / sp / mass, ag * y + Fm * vyy / sp / mass]

    while t < T_CAP:
        r = math.hypot(rx, ry)
        if r > R_FAR:
            break
        s = [rx, ry, vx, vy]
        k1 = deriv(s, m)
        s2 = [s[i] + 0.5 * dt * k1[i] for i in range(4)]
        k2 = deriv(s2, m)
        s3 = [s[i] + 0.5 * dt * k2[i] for i in range(4)]
        k3 = deriv(s3, m)
        s4 = [s[i] + dt * k3[i] for i in range(4)]
        k4 = deriv(s4, m)
        rx += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        ry += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        vx += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        vy += dt / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
        if m > dry_pay_kg:
            Fm = F0 * (r0 / math.hypot(rx, ry)) ** fade_exp
            m -= (Fm / ve) * dt
            if m < dry_pay_kg:
                m = dry_pay_kg
        else:                                  # propellant spent — decide the outcome and stop
            rr = math.hypot(rx, ry)
            ee = 0.5 * (vx * vx + vy * vy) - mu / rr
            if ee < 0.0 or rr > 8.0 * c.AU:
                break                          # bound (never escapes) OR escaped & coasting — settled
        t += dt
    r = math.hypot(rx, ry)
    energy = 0.5 * (vx * vx + vy * vy) - mu / r
    return math.sqrt(2.0 * energy) if energy > 0.0 else 0.0


@dataclass
class DepartureResult:
    v_inf_sun: float
    v_dep_helio: float
    v_inf_earth: float
    dv_impulsive: float
    dv_low_thrust: float
    spiral_penalty: float


def impulsive_dv_from_leo(
    v_inf_earth: float, perigee_km: float, apogee_km: float | None = None
) -> float:
    """Single Oberth kick at perigee from the (possibly elliptical) starting orbit.

    Circular start (apogee_km defaults to perigee_km) reduces to the LEO floor v_peri - v_circ.
    """
    if apogee_km is None:
        apogee_km = perigee_km
    apogee_km = max(apogee_km, perigee_km)
    r_p = c.R_EARTH + perigee_km * 1e3
    r_a = c.R_EARTH + apogee_km * 1e3
    a = 0.5 * (r_p + r_a)
    v_p = math.sqrt(c.MU_EARTH * (2.0 / r_p - 1.0 / a))   # perigee speed of the starting orbit
    v_esc = math.sqrt(2.0 * c.MU_EARTH / r_p)
    return math.sqrt(v_inf_earth**2 + v_esc**2) - v_p


def spiral_escape_dv(
    mu: float, r0: float, v_inf_target: float, accel: float = 5e-4,
    apogee_r: float | None = None,
) -> float:
    """Delta-v to spiral from a starting orbit (perigee radius ``r0``, optional ``apogee_r``)
    to hyperbolic excess ``v_inf_target``, under constant tangential thrust acceleration.

    Circular start when ``apogee_r`` is None/equal to r0. Integrated with scalar RK4 in 2-D,
    timestep adapting to the local orbital period. For low ``accel`` the result converges to
    the thrust-free 'low-thrust limit'; delta-v = accel * t.
    """
    target_energy = 0.5 * v_inf_target**2  # specific orbital energy at escape

    def deriv(x, y, vx, vy):
        r = math.hypot(x, y)
        v = math.hypot(vx, vy)
        inv_r3 = 1.0 / (r * r * r)
        ax = -mu * x * inv_r3 + accel * vx / v
        ay = -mu * y * inv_r3 + accel * vy / v
        return vx, vy, ax, ay

    a0 = r0 if apogee_r is None else 0.5 * (r0 + max(apogee_r, r0))
    v_start = math.sqrt(mu * (2.0 / r0 - 1.0 / a0))   # perigee speed of the starting orbit
    x, y, vx, vy = r0, 0.0, 0.0, v_start
    t = 0.0
    max_t = 200.0 * c.YEAR
    while t < max_t:
        r = math.hypot(x, y)
        v = math.hypot(vx, vy)
        if 0.5 * v * v - mu / r >= target_energy:
            break
        # Timestep ~0.5% of the local circular period, floored and *capped* so
        # we never take an inaccurate multi-revolution leap once far out.
        period = 2.0 * math.pi * math.sqrt(r * r * r / mu)
        dt = min(max(2.0, 0.005 * period), 1800.0)
        k1 = deriv(x, y, vx, vy)
        k2 = deriv(x + 0.5 * dt * k1[0], y + 0.5 * dt * k1[1],
                   vx + 0.5 * dt * k1[2], vy + 0.5 * dt * k1[3])
        k3 = deriv(x + 0.5 * dt * k2[0], y + 0.5 * dt * k2[1],
                   vx + 0.5 * dt * k2[2], vy + 0.5 * dt * k2[3])
        k4 = deriv(x + dt * k3[0], y + dt * k3[1],
                   vx + dt * k3[2], vy + dt * k3[3])
        x += (dt / 6.0) * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        y += (dt / 6.0) * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        vx += (dt / 6.0) * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        vy += (dt / 6.0) * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
        t += dt
    return accel * t


def perigee_biased_escape_dv(
    mu: float, r0: float, v_inf_target: float, gate: float = 2.0,
    accel: float = 5e-4, max_t_yr: float = 400.0
):
    """Perigee-biased low-thrust escape (Plan 02, Phase B). Thrust only while r <= gate * (the
    osculating perigee radius), coast otherwise, to recover the Oberth benefit lost by the naïve
    always-on spiral. Returns (dv, escaped, years).

    FINDING (see audit_departure.py): at this vehicle's ~milli-g thrust the perigee-biased escape
    is *time-divergent* — the pre-escape orbits have periods → ∞ and the gate coasts through them,
    so escape is not reached within a practical horizon (centuries). A loose gate degenerates to
    the always-on spiral. Hence the naïve spiral (`spiral_escape_dv` / `lowthrust_departure_dv`)
    remains the realistic departure budget; perigee-biasing pays off only at much higher T/W.
    """
    target_E = 0.5 * v_inf_target**2
    vc = math.sqrt(mu / r0)
    x, y, vx, vy = r0, 0.0, 0.0, vc
    t = 0.0
    thrust_t = 0.0
    max_t = max_t_yr * c.YEAR

    def acc(x, y, vx, vy, thr):
        r = math.hypot(x, y); v = math.hypot(vx, vy) or 1.0
        g = -mu / (r * r * r)
        return vx, vy, g * x + thr * vx / v, g * y + thr * vy / v

    escaped = False
    while t < max_t:
        r = math.hypot(x, y); v2 = vx * vx + vy * vy
        if 0.5 * v2 - mu / r >= target_E:
            escaped = True
            break
        h = x * vy - y * vx
        eps = 0.5 * v2 - mu / r
        e = math.sqrt(max(0.0, 1.0 + 2.0 * eps * h * h / (mu * mu)))
        r_peri = (h * h / mu) / (1.0 + e)            # osculating perigee radius
        thr = accel if r <= gate * r_peri else 0.0
        period = 2.0 * math.pi * math.sqrt(max(r, r0) ** 3 / mu)
        dt = min(max(2.0, 0.004 * period), 3600.0)
        k1 = acc(x, y, vx, vy, thr)
        k2 = acc(x + .5*dt*k1[0], y + .5*dt*k1[1], vx + .5*dt*k1[2], vy + .5*dt*k1[3], thr)
        k3 = acc(x + .5*dt*k2[0], y + .5*dt*k2[1], vx + .5*dt*k2[2], vy + .5*dt*k2[3], thr)
        k4 = acc(x + dt*k3[0], y + dt*k3[1], vx + dt*k3[2], vy + dt*k3[3], thr)
        x += dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0]); y += dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1])
        vx += dt/6*(k1[2]+2*k2[2]+2*k3[2]+k4[2]); vy += dt/6*(k1[3]+2*k2[3]+2*k3[3]+k4[3])
        t += dt
        if thr:
            thrust_t += dt
    return accel * thrust_t, escaped, t / c.YEAR


def departure_budget(
    v_inf_sun: float, plane_angle_deg: float, altitude_km: float = 400.0
) -> DepartureResult:
    """Full LEO departure budget for both impulsive and low-thrust regimes."""
    v_inf_e, v_dep = v_inf_earth_required(v_inf_sun, plane_angle_deg)
    dv_imp = impulsive_dv_from_leo(v_inf_e, altitude_km)

    # Low-thrust: the single perigee burn becomes an Earth-escape spiral that
    # delivers the same v_inf_earth (hence the same heliocentric v_inf_sun).
    r_leo = c.R_EARTH + altitude_km * 1e3
    dv_spiral = spiral_escape_dv(c.MU_EARTH, r_leo, v_inf_e)

    return DepartureResult(
        v_inf_sun=v_inf_sun,
        v_dep_helio=v_dep,
        v_inf_earth=v_inf_e,
        dv_impulsive=dv_imp,
        dv_low_thrust=dv_spiral,
        spiral_penalty=dv_spiral - dv_imp,
    )
