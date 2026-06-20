"""Cruise time to Alpha Centauri and gravity-assist options.

Cruise is ballistic at the heliocentric excess speed v_inf. Because the burn
(or flyby) phase lasts years against an ~80,000-year coast, transit time is set
almost entirely by v_inf and the intercept geometry -- not by the propulsion.
"""

from __future__ import annotations

import math

import numpy as np

from . import constants as c
from .astro import StateVector


def time_to_ac(state: StateVector, v_inf: float) -> float | None:
    """Earliest arrival time (s) achievable with cruise speed |v_inf|.

    Solve |A0 + V_ac*T|^2 / T^2 = v_inf^2 for T (quadratic in u = 1/T); take the
    largest positive u -> smallest positive T. Returns None if v_inf is below the
    tangential minimum (no real intercept).
    """
    r0, v = state.r, state.v
    a = float(np.dot(r0, r0))
    b = float(np.dot(r0, v))
    cc = float(np.dot(v, v)) - v_inf**2
    disc = b * b - a * cc
    if disc < 0:
        return None
    sqrt_disc = math.sqrt(disc)
    roots = [(-b + sqrt_disc) / a, (-b - sqrt_disc) / a]  # values of u = 1/T
    positive = [u for u in roots if u > 0]
    if not positive:
        return None
    u = max(positive)  # largest u -> smallest T -> earliest arrival
    return 1.0 / u


# --- Jupiter gravity assist ---
V_JUPITER_ORBITAL = math.sqrt(c.MU_SUN / (5.2028 * c.AU))  # ~13.06 km/s
MU_JUPITER = 1.26687e17  # m^3/s^2
R_JUPITER = 7.1492e7  # m


def jupiter_assist_max_gain(v_inf_in_rel: float, flyby_alt_km: float = 200_000.0) -> float:
    """Maximum heliocentric speed gain from a single Jupiter flyby (m/s).

    A flyby rotates the incoming v_inf (relative to Jupiter) by up to 2*delta,
    where sin(delta) = 1 / (1 + r_p v_inf_rel^2 / mu_J). Best case the turn adds
    up to 2*v_inf_in_rel*sin(delta) to the heliocentric speed.
    """
    r_p = R_JUPITER + flyby_alt_km * 1e3
    sin_delta = 1.0 / (1.0 + r_p * v_inf_in_rel**2 / MU_JUPITER)
    return 2.0 * v_inf_in_rel * sin_delta


# --- Solar Oberth maneuver (powered perihelion) ---
def solar_oberth_vinf(perihelion_solar_radii: float, burn_dv: float) -> float:
    """Heliocentric v_inf after a burn ``burn_dv`` at a close solar perihelion.

    Arriving near-parabolic, perihelion speed ~ local escape speed. A burn there
    is hugely leveraged (Oberth): v_inf = sqrt((v_peri + dv)^2 - v_esc^2).
    """
    r_sun = 6.957e8  # m
    r_p = perihelion_solar_radii * r_sun
    v_esc = math.sqrt(2.0 * c.MU_SUN / r_p)
    v_peri = v_esc  # near-parabolic arrival
    v_after = v_peri + burn_dv
    return math.sqrt(max(v_after**2 - v_esc**2, 0.0))


def solar_oberth_burn_for_vinf(perihelion_solar_radii: float, v_inf_target: float) -> float:
    """Burn delta-v at perihelion needed to reach a target v_inf."""
    r_sun = 6.957e8
    r_p = perihelion_solar_radii * r_sun
    v_esc = math.sqrt(2.0 * c.MU_SUN / r_p)
    v_after = math.sqrt(v_inf_target**2 + v_esc**2)
    return v_after - v_esc
