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
    # minimised to beta (align the in-plane projection with Earth's motion).
    v_inf_e_sq = v_dep**2 + c.V_EARTH_ORBITAL**2 - 2 * v_dep * c.V_EARTH_ORBITAL * math.cos(beta)
    return math.sqrt(max(v_inf_e_sq, 0.0)), v_dep


# --- Derived low-thrust departure fit (Plan 02, Phase A: naïve constant-tangential spiral) ---
# Closed form for the integrated `spiral_escape_dv` so the web tool evaluates it instantly
# (no live integration) while staying DERIVED, not a hand-set penalty. Generated and validated
# by `tools/fit_spiral.py`: Δv = v_circ(alt) + C0 + C1·v∞,E  (SI, m/s). The (Δv − v_circ)
# curve is altitude-independent to 0.8 m/s, and this fit matches the integration to 0.5 m/s
# (<0.01%) over v∞,E ∈ [8, 32] km/s — the only band that occurs for feasible interstellar aims.
_SPIRAL_FIT_C0 = -1173.491  # m/s
_SPIRAL_FIT_C1 = 0.999997


def lowthrust_departure_dv(
    v_inf_sun: float, plane_angle_deg: float, altitude_km: float = 400.0
) -> float:
    """Derived naïve low-thrust Earth-escape Δv from LEO (m/s) — the design departure budget.

    Closed-form fit of the integrated constant-tangential-thrust spiral (`spiral_escape_dv`);
    see `tools/fit_spiral.py`. Used by both the engine and `web/physics.js` so they agree to
    machine precision; the audit suite re-checks this fit against a fresh integration.
    """
    v_inf_e, _ = v_inf_earth_required(v_inf_sun, plane_angle_deg)
    v_circ, _ = leo_speeds(altitude_km)
    return v_circ + _SPIRAL_FIT_C0 + _SPIRAL_FIT_C1 * v_inf_e


@dataclass
class DepartureResult:
    v_inf_sun: float
    v_dep_helio: float
    v_inf_earth: float
    dv_impulsive: float
    dv_low_thrust: float
    spiral_penalty: float


def impulsive_dv_from_leo(v_inf_earth: float, altitude_km: float) -> float:
    """Single-burn delta-v from circular LEO to hyperbolic excess v_inf_earth."""
    v_circ, v_esc = leo_speeds(altitude_km)
    v_peri = math.sqrt(v_inf_earth**2 + v_esc**2)
    return v_peri - v_circ


def spiral_escape_dv(
    mu: float, r0: float, v_inf_target: float, accel: float = 5e-4
) -> float:
    """Delta-v to spiral from a circular orbit (radius r0) to hyperbolic excess
    ``v_inf_target``, under constant tangential thrust acceleration.

    Integrated with scalar RK4 in 2-D, with a timestep that adapts to the local
    orbital period (small near periapsis, large far out). For low ``accel`` the
    result converges to the thrust-free 'low-thrust limit'; delta-v = accel * t.
    """
    target_energy = 0.5 * v_inf_target**2  # specific orbital energy at escape

    def deriv(x, y, vx, vy):
        r = math.hypot(x, y)
        v = math.hypot(vx, vy)
        inv_r3 = 1.0 / (r * r * r)
        ax = -mu * x * inv_r3 + accel * vx / v
        ay = -mu * y * inv_r3 + accel * vy / v
        return vx, vy, ax, ay

    v_circ = math.sqrt(mu / r0)
    x, y, vx, vy = r0, 0.0, 0.0, v_circ
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
