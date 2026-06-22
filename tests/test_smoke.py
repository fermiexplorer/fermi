"""Smoke / regression tests for the fermi_sim engine.

Run:  .venv/bin/pytest    (or .venv/bin/python -m pytest)
For the full independent cross-checks see audit/calcs/run_audits.py.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from fermi_sim import constants as c
from fermi_sim.astro import alpha_centauri_state, closest_approach
from fermi_sim.departure import departure_budget
from fermi_sim.intercept import (
    ecliptic_crossing_time,
    min_speed_arrival,
    solve_intercept,
)
from fermi_sim.spacecraft import FuelCellArchitecture, SolarArchitecture, propellant_mass
from fermi_sim.trajectory import solar_oberth_vinf, time_to_ac


def test_closest_approach():
    st = alpha_centauri_state()
    t, d = closest_approach(st)
    assert 26_000 < t / c.YEAR < 30_000
    assert 2.8 < d / c.LY < 3.3


def test_tangential_and_ecliptic_times():
    st = alpha_centauri_state()
    assert abs(min_speed_arrival(st).arrival_time_yr - 58_138) < 50
    assert abs(ecliptic_crossing_time(st) / c.YEAR - 79_252) < 50


def test_min_vinf_equals_tangential_speed():
    st = alpha_centauri_state()
    d = np.linalg.norm(st.r)
    v_rad = float(np.dot(st.r, st.v)) / d
    v_tan = np.sqrt(np.dot(st.v, st.v) - v_rad**2)
    assert abs(min_speed_arrival(st).v_inf - v_tan) / v_tan < 1e-3


def test_min_departure_dv_near_75k():
    st = alpha_centauri_state()
    best = min(
        (departure_budget(solve_intercept(st, y * c.YEAR).v_inf,
                          solve_intercept(st, y * c.YEAR).plane_angle_deg).dv_impulsive, y)
        for y in range(60_000, 95_000, 1000)
    )
    assert 70_000 <= best[1] <= 80_000
    assert 13.5e3 < best[0] < 14.5e3


def test_solar_propellant_fraction_reasonable():
    s = SolarArchitecture(dry_mass=255, dv=20e3, isp_s=3000).summary()
    assert 0.45 < s["prop_mass_kg"] / s["wet_mass_kg"] < 0.55


def test_fuelcell_is_catastrophic():
    fc = FuelCellArchitecture(dry_mass=255, dv=20e3, isp_s=3000).summary()
    assert fc["reactant_mass_kg"] > 10_000  # tonnes -> infeasible


def test_time_to_ac_within_budget():
    st = alpha_centauri_state()
    assert time_to_ac(st, 24e3) / c.YEAR < 100_000


def test_oberth_leverage():
    # ~1-2 km/s burn at 6 R_sun should give a large v_inf
    assert solar_oberth_vinf(6, 2_000) / c.KMS > 25
