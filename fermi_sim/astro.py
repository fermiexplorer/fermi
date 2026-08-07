"""Alpha Centauri ephemeris and coordinate transforms.

We build the 3-D heliocentric position and velocity of the Alpha Centauri AB
system in *ecliptic* Cartesian coordinates from its catalogued (RA, Dec,
distance, proper motion, radial velocity). The ecliptic frame is the natural
one for this mission because Earth's orbital velocity -- the "free" 29.8 km/s
we want to borrow at departure -- lies in the ecliptic plane.

Over the ~80,000-year flight we treat Alpha Centauri as moving in a straight
line at constant velocity. The curvature of its galactic orbit over that span
is negligible relative to the 2600 AU (1%) miss-distance target.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import constants as c


# --- Catalogued data for the Alpha Centauri AB barycentre (ICRS) ---
# One catalog end-to-end: the Akeson et al. 2021 (AJ 162, 14) barycenter
# solution at its NATIVE epoch J2019.5 — position, parallax 750.81 ± 0.38 mas,
# proper motion −3639.95 ± 0.42 / +700.40 ± 0.17 mas/yr. The radial velocity
# is carried in the KINEMATIC frame (true line-of-sight velocity of the
# barycenter): spectroscopic gamma V0 = −22.3796 ± 0.0020 km/s (Akeson 2021)
# plus the +61.4 ± 2.7 m/s gravitational-redshift zero-point correction
# (Kervella, Thévenin & Lovis 2017, A&A 598, L7). A and B individually wobble
# about the barycentre but that is irrelevant here. This exact state is the
# jointly-validated golden fixture (audit/psi/golden_v2/), gated on every
# audit run.
#
# CLOCK CONVENTION: all propagation times T (and every epoch label derived
# from them, e.g. the ecliptic crossing) run from the state epoch J2019.5.
# Departure-origin times subtract (DEPARTURE_EPOCH_JYEAR - AC_EPOCH_JYEAR);
# calendar dates add AC_EPOCH_JYEAR.
AC_EPOCH_JYEAR = 2019.5  # astrometric epoch of the state (and the T=0 clock)
DEPARTURE_EPOCH_JYEAR = 2029.0  # program departure target
AC_RA_DEG = 219.85892215
AC_DEC_DEG = -60.83163195
AC_PARALLAX_MAS = 750.81
AC_PMRA_MASYR = -3639.95  # mu_alpha * cos(dec), mas/yr
AC_PMDEC_MASYR = 700.40  # mu_delta, mas/yr
AC_RV_KMS = -22.3182  # kinematic-frame radial velocity, km/s (approaching)

# 1 mas/yr at 1 pc = 4.74047 km/s
_MASYR_PC_TO_KMS = 4.740470463

# Distance follows from the parallax exactly (no independently rounded copy).
AC_DIST_LY = (1000.0 / AC_PARALLAX_MAS) * (c.PC / c.LY)


@dataclass(frozen=True)
class StateVector:
    """Heliocentric state in ecliptic Cartesian coordinates, SI units."""

    r: np.ndarray  # position, m  (3,)
    v: np.ndarray  # velocity, m/s (3,)

    def position_at(self, t_seconds: float) -> np.ndarray:
        return self.r + self.v * t_seconds


def _equatorial_to_ecliptic(vec: np.ndarray) -> np.ndarray:
    """Rotate an equatorial (ICRS) Cartesian vector into ecliptic coordinates."""
    eps = c.OBLIQUITY
    rot = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, math.cos(eps), math.sin(eps)],
            [0.0, -math.sin(eps), math.cos(eps)],
        ]
    )
    return rot @ vec


def alpha_centauri_state() -> StateVector:
    """Return Alpha Centauri's current heliocentric ecliptic state vector."""
    ra = math.radians(AC_RA_DEG)
    dec = math.radians(AC_DEC_DEG)
    dist_m = AC_DIST_LY * c.LY
    dist_pc = dist_m / c.PC

    # Position unit vector (equatorial Cartesian) and the local sky basis.
    r_hat = np.array(
        [math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)]
    )
    ra_hat = np.array([-math.sin(ra), math.cos(ra), 0.0])  # +RA direction
    dec_hat = np.array(
        [-math.sin(dec) * math.cos(ra), -math.sin(dec) * math.sin(ra), math.cos(dec)]
    )  # +Dec direction

    # Tangential velocities from proper motion (km/s), radial from RV.
    v_ra = _MASYR_PC_TO_KMS * (AC_PMRA_MASYR / 1000.0) * dist_pc  # km/s
    v_dec = _MASYR_PC_TO_KMS * (AC_PMDEC_MASYR / 1000.0) * dist_pc  # km/s
    v_r = AC_RV_KMS  # km/s

    pos_eq = dist_m * r_hat
    vel_eq = (v_r * r_hat + v_ra * ra_hat + v_dec * dec_hat) * c.KMS  # m/s

    return StateVector(
        r=_equatorial_to_ecliptic(pos_eq), v=_equatorial_to_ecliptic(vel_eq)
    )


def closest_approach(state: StateVector) -> tuple[float, float]:
    """Time (s) and distance (m) of Alpha Centauri's closest approach to the Sun.

    Straight-line motion: the closest approach is the perpendicular foot from
    the origin onto the trajectory r(t) = r0 + v t.
    """
    r0, v = state.r, state.v
    t_close = -float(np.dot(r0, v)) / float(np.dot(v, v))
    d_close = float(np.linalg.norm(r0 + v * t_close))
    return t_close, d_close
