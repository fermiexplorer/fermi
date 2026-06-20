"""Independent Codex v3 numerical checks for Project Fermi.

This script intentionally does not import ``fermi_sim``. It re-implements the
small set of equations needed for a cross-check from catalog constants and
standard astrodynamics, then prints a JSON summary. It is meant to be run from
the repository root:

    .venv/bin/python audit/codex/v3_independent_checks.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize_scalar


# Fundamental constants, SI unless noted.
AU = 1.495978707e11
LY = 9.4607304725808e15
PC = 3.0856775814913673e16
YEAR = 3.15576e7
KMS = 1.0e3
G0 = 9.80665
MU_SUN = 1.32712440018e20
MU_EARTH = 3.986004418e14
R_EARTH = 6.371e6
OBLIQUITY = math.radians(23.439281)
V_EARTH = math.sqrt(MU_SUN / AU)
V_ESC_SUN_1AU = math.sqrt(2.0 * MU_SUN / AU)

# Alpha Centauri AB barycentre catalog values used by the project.
AC_RA_DEG = 219.9021
AC_DEC_DEG = -60.8340
AC_DIST_LY = 4.344
AC_PMRA_MASYR = -3620.0
AC_PMDEC_MASYR = 694.0
AC_RV_KMS = -22.4
MASYR_PC_TO_KMS = 4.740470463


@dataclass(frozen=True)
class State:
    r: np.ndarray
    v: np.ndarray

    def position_at(self, t_s: float) -> np.ndarray:
        return self.r + self.v * t_s


def equatorial_to_ecliptic(vec: np.ndarray) -> np.ndarray:
    eps = OBLIQUITY
    rot = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, math.cos(eps), math.sin(eps)],
            [0.0, -math.sin(eps), math.cos(eps)],
        ]
    )
    return rot @ vec


def alpha_centauri_state_hand() -> State:
    ra = math.radians(AC_RA_DEG)
    dec = math.radians(AC_DEC_DEG)
    dist_m = AC_DIST_LY * LY
    dist_pc = dist_m / PC

    r_hat = np.array(
        [math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)]
    )
    ra_hat = np.array([-math.sin(ra), math.cos(ra), 0.0])
    dec_hat = np.array(
        [-math.sin(dec) * math.cos(ra), -math.sin(dec) * math.sin(ra), math.cos(dec)]
    )

    v_ra = MASYR_PC_TO_KMS * (AC_PMRA_MASYR / 1000.0) * dist_pc
    v_dec = MASYR_PC_TO_KMS * (AC_PMDEC_MASYR / 1000.0) * dist_pc
    vel_eq = (AC_RV_KMS * r_hat + v_ra * ra_hat + v_dec * dec_hat) * KMS
    return State(equatorial_to_ecliptic(dist_m * r_hat), equatorial_to_ecliptic(vel_eq))


def closest_approach(st: State) -> tuple[float, float]:
    t = -float(np.dot(st.r, st.v)) / float(np.dot(st.v, st.v))
    return t, float(np.linalg.norm(st.position_at(t)))


def required_vinf_vec(st: State, arrival_yr: float) -> np.ndarray:
    t = arrival_yr * YEAR
    return st.position_at(t) / t


def intercept_solution(st: State, arrival_yr: float) -> dict[str, float | list[float]]:
    v = required_vinf_vec(st, arrival_yr)
    v_in = float(np.hypot(v[0], v[1]))
    return {
        "arrival_yr": arrival_yr,
        "vinf_kms": float(np.linalg.norm(v) / KMS),
        "tilt_deg": math.degrees(math.atan2(float(v[2]), v_in)),
        "vector_m_s": v.tolist(),
    }


def v_inf_earth_required(vinf_sun: float, tilt_deg: float) -> tuple[float, float]:
    v_dep = math.sqrt(vinf_sun**2 + V_ESC_SUN_1AU**2)
    beta = math.radians(tilt_deg)
    v_inf_e_sq = v_dep**2 + V_EARTH**2 - 2.0 * v_dep * V_EARTH * math.cos(beta)
    return math.sqrt(max(v_inf_e_sq, 0.0)), v_dep


def leo_speeds(alt_km: float = 400.0) -> tuple[float, float]:
    r = R_EARTH + alt_km * 1000.0
    return math.sqrt(MU_EARTH / r), math.sqrt(2.0 * MU_EARTH / r)


def impulsive_dv_from_leo(vinf_e: float, alt_km: float = 400.0) -> float:
    v_circ, v_esc = leo_speeds(alt_km)
    return math.sqrt(vinf_e**2 + v_esc**2) - v_circ


def departure_for_arrival(st: State, arrival_yr: float) -> dict[str, float]:
    sol = intercept_solution(st, arrival_yr)
    vinf_sun = float(sol["vinf_kms"]) * KMS
    vinf_e, v_dep = v_inf_earth_required(vinf_sun, float(sol["tilt_deg"]))
    dv = impulsive_dv_from_leo(vinf_e)
    return {
        "arrival_yr": arrival_yr,
        "vinf_sun_kms": vinf_sun / KMS,
        "tilt_deg": float(sol["tilt_deg"]),
        "vinf_earth_kms": vinf_e / KMS,
        "vdep_1au_kms": v_dep / KMS,
        "dv_impulsive_kms": dv / KMS,
    }


def propellant_mass(dry_mass: float, dv: float, isp_s: float) -> float:
    ve = isp_s * G0
    return dry_mass * (math.exp(dv / ve) - 1.0)


def solar_architecture() -> dict[str, float]:
    dry, dv, isp = 255.0, 20_000.0, 3000.0
    prop = propellant_mass(dry, dv, isp)
    power = 5000.0
    eff = 0.20
    areal = 3.0
    area = power / (1361.0 * eff)
    array_mass = area * areal
    engine_ppu = 6.0 * power / 1000.0
    tank = 0.08 * prop
    return {
        "prop_kg": prop,
        "wet_kg": dry + prop,
        "array_area_m2": area,
        "array_mass_kg": array_mass,
        "array_specific_power_w_kg": power / array_mass,
        "engine_ppu_kg": engine_ppu,
        "tank_kg": tank,
        "bus_payload_margin_kg": dry - array_mass - engine_ppu - tank,
    }


def fuelcell_case() -> dict[str, float]:
    dry, dv, eta_thruster, eta_fc = 255.0, 20_000.0, 0.6, 0.6
    e_chem_raw = 8.0e6

    def totals(isp_s: float) -> tuple[float, float, float]:
        ve = isp_s * G0
        prop = propellant_mass(dry, dv, isp_s)
        energy = 0.5 * prop * ve**2 / eta_thruster
        react = energy / (eta_fc * e_chem_raw)
        return prop, react, prop + react

    res = minimize_scalar(lambda x: totals(x)[2], bounds=(200.0, 4000.0), method="bounded")
    prop_3000, react_3000, consum_3000 = totals(3000.0)
    prop_opt, react_opt, consum_opt = totals(float(res.x))
    return {
        "prop_3000_kg": prop_3000,
        "reactant_3000_kg": react_3000,
        "consumables_3000_kg": consum_3000,
        "opt_isp_s": float(res.x),
        "opt_prop_kg": prop_opt,
        "opt_reactant_kg": react_opt,
        "opt_consumables_kg": consum_opt,
        "self_powered_cap_kms": math.sqrt(2.0 * eta_thruster * eta_fc * e_chem_raw) / KMS,
    }


def galactic_tide_curvature_au(duration_yr: float = 100_000.0) -> float:
    # Conservative first-order differential acceleration across the AC separation:
    # a_tide ~ (v_circ^2 / R_gal) * (separation / R_gal).
    v_gal = 220_000.0
    r_gal = 8.2e3 * PC
    sep = AC_DIST_LY * LY
    a_tide = (v_gal**2 / r_gal) * (sep / r_gal)
    return 0.5 * a_tide * (duration_yr * YEAR) ** 2 / AU


def main() -> int:
    st = alpha_centauri_state_hand()
    t_close, d_close = closest_approach(st)

    opt = minimize_scalar(
        lambda y: departure_for_arrival(st, y)["dv_impulsive_kms"],
        bounds=(58_000.0, 100_000.0),
        method="bounded",
        options={"xatol": 1e-3},
    )
    dep_opt = departure_for_arrival(st, float(opt.x))
    dep_75 = departure_for_arrival(st, 75_000.0)
    dep_70 = departure_for_arrival(st, 70_000.0)

    v75 = np.array(intercept_solution(st, 75_000.0)["vector_m_s"])
    rel75 = float(np.linalg.norm(v75 - st.v))
    half_window_yr = 2600.0 * AU / rel75 / YEAR

    solar = solar_architecture()
    fuel = fuelcell_case()
    fuel["reactant_to_array_ratio_3000"] = fuel["reactant_3000_kg"] / solar["array_mass_kg"]
    fuel["opt_consumables_to_array_ratio"] = fuel["opt_consumables_kg"] / solar["array_mass_kg"]

    v_circ, v_esc_leo = leo_speeds()
    chain_75 = {
        "leo_circular_kms": v_circ / KMS,
        "post_burn_perigee_kms": v_circ / KMS + dep_75["dv_impulsive_kms"],
        "leo_escape_kms": v_esc_leo / KMS,
        "vinf_earth_kms": dep_75["vinf_earth_kms"],
        "earth_orbital_kms": V_EARTH / KMS,
        "vdep_1au_kms": dep_75["vdep_1au_kms"],
        "solar_escape_1au_kms": V_ESC_SUN_1AU / KMS,
        "cruise_vinf_kms": dep_75["vinf_sun_kms"],
    }

    results = {
        "alpha_centauri": {
            "distance_now_ly": float(np.linalg.norm(st.r) / LY),
            "space_speed_kms": float(np.linalg.norm(st.v) / KMS),
            "closest_approach_yr": t_close / YEAR,
            "closest_approach_ly": d_close / LY,
        },
        "departure": {
            "optimum": dep_opt,
            "at_75000_yr": dep_75,
            "at_70000_yr": dep_70,
            "penalty_75k_over_opt_m_s": (dep_75["dv_impulsive_kms"] - dep_opt["dv_impulsive_kms"]) * KMS,
            "miss_tolerance_half_window_yr": half_window_yr,
            "energy_chain_75k": chain_75,
        },
        "solar": solar,
        "fuel_cell": fuel,
        "galactic_curvature_100k_au": galactic_tide_curvature_au(),
    }

    checks = [
        (72_700.0 < dep_opt["arrival_yr"] < 72_900.0, "departure optimum year"),
        (13.86 < dep_opt["dv_impulsive_kms"] < 13.89, "departure optimum dv"),
        (9.0 < results["departure"]["penalty_75k_over_opt_m_s"] < 12.0, "75k penalty"),
        (700.0 < half_window_yr < 720.0, "2600 AU time window at 75k"),
        (54.0 < solar["array_mass_kg"] < 56.0, "default array mass"),
        (149.0 < solar["bus_payload_margin_kg"] < 151.0, "dry mass closure"),
        (1300.0 < fuel["opt_isp_s"] < 1400.0, "fuel-cell optimum isp"),
        (600.0 < fuel["reactant_to_array_ratio_3000"] < 750.0, "fuel-cell mass ratio"),
        (results["galactic_curvature_100k_au"] < 10.0, "galactic curvature"),
    ]
    failed = [name for ok, name in checks if not ok]
    print(json.dumps(results, indent=2, sort_keys=True))
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("V3 independent checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
