"""Interstellar intercept geometry.

A probe that has escaped the Sun coasts in a near-straight line at its
heliocentric hyperbolic-excess velocity v_inf. To pass through the point where
Alpha Centauri will be at arrival time T, the required heliocentric velocity is

    V_p(T) = A(T) / T = A0 / T + V_ac

where A0 is Alpha Centauri's current position and V_ac its velocity. (We take
the probe's origin as the Sun; the 1 AU launch offset is negligible against
~270,000 AU.) This is just "lead the moving target":

    A0 / T   -- the AIM term: point at where AC is now, shrinks as T grows.
    V_ac     -- the LEAD term: match AC's space velocity, fixed.

|V_p| is minimised at the *tangential intercept*, where the aim term exactly
cancels the radial part of V_ac and only the tangential part (~23 km/s) remains.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize_scalar

from . import constants as c
from .astro import StateVector


@dataclass
class InterceptSolution:
    arrival_time_s: float
    v_inf_vec: np.ndarray  # required heliocentric v_inf vector, m/s
    v_inf: float  # its magnitude, m/s
    v_inf_in_plane: float  # ecliptic-plane component magnitude, m/s
    v_inf_out_of_plane: float  # |z| component, m/s
    plane_angle_deg: float  # angle of v_inf above/below the ecliptic

    @property
    def arrival_time_yr(self) -> float:
        return self.arrival_time_s / c.YEAR


def required_v_inf(state: StateVector, arrival_time_s: float) -> np.ndarray:
    """Heliocentric v_inf vector needed to intercept AC at the given time."""
    return state.position_at(arrival_time_s) / arrival_time_s


def solve_intercept(state: StateVector, arrival_time_s: float) -> InterceptSolution:
    v = required_v_inf(state, arrival_time_s)
    v_mag = float(np.linalg.norm(v))
    v_z = float(v[2])
    v_in = float(np.hypot(v[0], v[1]))
    angle = np.degrees(np.arctan2(v_z, v_in))
    return InterceptSolution(
        arrival_time_s=arrival_time_s,
        v_inf_vec=v,
        v_inf=v_mag,
        v_inf_in_plane=v_in,
        v_inf_out_of_plane=abs(v_z),
        plane_angle_deg=float(angle),
    )


def min_speed_arrival(state: StateVector) -> InterceptSolution:
    """Arrival time that minimises the required heliocentric speed |v_inf|.

    This is the tangential intercept. Closed form:
        T* = |A0|^2 / (-A0 . V_ac)
    """
    r0, vac = state.r, state.v
    t_star = float(np.dot(r0, r0)) / (-float(np.dot(r0, vac)))
    return solve_intercept(state, t_star)


def ecliptic_crossing_time(state: StateVector) -> float:
    """Time at which AC's trajectory crosses the ecliptic plane (z = 0).

    Arriving here makes V_p purely in-plane, so the entire departure can borrow
    Earth's in-ecliptic orbital velocity -- no costly plane change.
    """
    return -state.r[2] / state.v[2]


def sweep_arrival_times(
    state: StateVector, t_min_yr: float, t_max_yr: float, n: int = 400
):
    """Return arrays (t_yr, v_inf_kms, out_of_plane_kms) over a span of arrivals."""
    times = np.linspace(t_min_yr, t_max_yr, n) * c.YEAR
    sols = [solve_intercept(state, t) for t in times]
    t_yr = np.array([s.arrival_time_yr for s in sols])
    v_inf = np.array([s.v_inf for s in sols]) / c.KMS
    oop = np.array([s.v_inf_out_of_plane for s in sols]) / c.KMS
    return t_yr, v_inf, oop
