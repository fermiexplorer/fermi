"""Codex v4 independent checks for audit prompt 10.

This script intentionally avoids importing ``fermi_sim``. It re-derives the
58 kyr minimum-speed intercept, patched-conic departure chain, propellant
loads, and dry-mass closure from catalogue constants and standard equations.

Run from the repository root:

    .venv/bin/python audit/codex/v4_prompt10_checks.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar


AU = 1.495978707e11
LY = 9.4607304725808e15
PC = 3.0856775814913673e16
YEAR = 3.15576e7
KMS = 1000.0
G0 = 9.80665
MU_SUN = 1.32712440018e20
MU_EARTH = 3.986004418e14
R_EARTH = 6.371e6
OBLIQUITY = math.radians(23.439281)
V_EARTH = math.sqrt(MU_SUN / AU)
V_ESC_SUN_1AU = math.sqrt(2.0 * MU_SUN / AU)

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


def alpha_centauri_state() -> State:
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
    pos_eq = dist_m * r_hat
    return State(equatorial_to_ecliptic(pos_eq), equatorial_to_ecliptic(vel_eq))


def tangential_arrival_yr(st: State) -> float:
    return float(np.dot(st.r, st.r)) / -float(np.dot(st.r, st.v)) / YEAR


def intercept_terms(st: State, arrival_yr: float) -> dict:
    t = arrival_yr * YEAR
    aim = st.r / t
    lead = st.v
    vinf = aim + lead
    in_plane = float(np.hypot(vinf[0], vinf[1]))
    return {
        "arrival_yr": arrival_yr,
        "aim_term_kms": (aim / KMS).tolist(),
        "lead_term_kms": (lead / KMS).tolist(),
        "vinf_vector_kms": (vinf / KMS).tolist(),
        "bare_r_over_t_kms": float(np.linalg.norm(aim) / KMS),
        "vinf_kms": float(np.linalg.norm(vinf) / KMS),
        "tilt_deg": math.degrees(math.atan2(float(vinf[2]), in_plane)),
    }


def v_inf_earth(vinf_sun: float, tilt_deg: float) -> tuple[float, float]:
    v_dep = math.sqrt(vinf_sun**2 + V_ESC_SUN_1AU**2)
    beta = math.radians(tilt_deg)
    vinf_e_sq = v_dep**2 + V_EARTH**2 - 2.0 * v_dep * V_EARTH * math.cos(beta)
    return math.sqrt(max(vinf_e_sq, 0.0)), v_dep


def leo_speeds(alt_km: float = 400.0) -> tuple[float, float]:
    r = R_EARTH + alt_km * 1000.0
    return math.sqrt(MU_EARTH / r), math.sqrt(2.0 * MU_EARTH / r)


def departure_for_terms(terms: dict, alt_km: float = 400.0) -> dict:
    vinf_sun = terms["vinf_kms"] * KMS
    vinf_e, v_dep = v_inf_earth(vinf_sun, terms["tilt_deg"])
    v_circ, v_esc = leo_speeds(alt_km)
    dv_imp = math.sqrt(vinf_e**2 + v_esc**2) - v_circ
    return {
        "v_dep_1au_kms": v_dep / KMS,
        "earth_orbital_kms": V_EARTH / KMS,
        "vinf_earth_kms": vinf_e / KMS,
        "leo_circular_kms": v_circ / KMS,
        "leo_escape_kms": v_esc / KMS,
        "dv_impulsive_kms": dv_imp / KMS,
        "post_burn_perigee_kms": (v_circ + dv_imp) / KMS,
    }


def departure_for_arrival(st: State, arrival_yr: float) -> dict:
    terms = intercept_terms(st, arrival_yr)
    return {**terms, **departure_for_terms(terms)}


def spiral_escape_dv(vinf_e: float, accel: float = 5.0e-4) -> dict:
    r0 = R_EARTH + 400.0e3
    vc = math.sqrt(MU_EARTH / r0)
    target_energy = 0.5 * vinf_e**2

    def rhs(_t: float, y: np.ndarray) -> list[float]:
        x, yy, vx, vy = y
        r = math.hypot(x, yy)
        v = math.hypot(vx, vy)
        inv_r3 = 1.0 / (r * r * r)
        return [
            vx,
            vy,
            -MU_EARTH * x * inv_r3 + accel * vx / v,
            -MU_EARTH * yy * inv_r3 + accel * vy / v,
        ]

    def escaped(_t: float, y: np.ndarray) -> float:
        x, yy, vx, vy = y
        r = math.hypot(x, yy)
        v2 = vx * vx + vy * vy
        return 0.5 * v2 - MU_EARTH / r - target_energy

    escaped.terminal = True
    escaped.direction = 1

    sol = solve_ivp(
        rhs,
        (0.0, 200.0 * YEAR),
        [r0, 0.0, 0.0, vc],
        method="DOP853",
        rtol=2.0e-8,
        atol=1.0e-4,
        max_step=1800.0,
        events=escaped,
    )
    if not sol.t_events or len(sol.t_events[0]) == 0:
        raise RuntimeError("low-thrust spiral did not reach target energy")
    burn_s = float(sol.t_events[0][0])
    return {
        "accel_m_s2": accel,
        "burn_years": burn_s / YEAR,
        "dv_low_thrust_kms": accel * burn_s / KMS,
        "solver_steps": int(sol.t.size),
    }


def propellant_mass(dry_mass: float, dv: float, isp_s: float) -> float:
    ve = isp_s * G0
    return dry_mass * (math.exp(dv / ve) - 1.0)


def mass_table(dv_values_kms: dict[str, float]) -> dict:
    rows = {}
    for label, dv_kms in dv_values_kms.items():
        for isp in (3000.0, 4000.0):
            dry = 255.0
            mp = propellant_mass(dry, dv_kms * KMS, isp)
            wet = dry + mp
            rows[f"{label}_isp{int(isp)}"] = {
                "dv_kms": dv_kms,
                "isp_s": isp,
                "propellant_kg": mp,
                "wet_kg": wet,
                "propellant_fraction": mp / wet,
                "mass_ratio": wet / dry,
            }
    return rows


def dry_mass_closure(prop_kg: float) -> dict:
    power_w = 5000.0
    array_area = power_w / (1361.0 * 0.20)
    array_mass = array_area * 3.0
    engine_ppu = 6.0 * power_w / 1000.0
    tank_mass = 0.08 * prop_kg
    subsystems = array_mass + engine_ppu + tank_mass
    return {
        "array_area_m2": array_area,
        "array_mass_kg": array_mass,
        "engine_ppu_kg": engine_ppu,
        "tank_mass_kg": tank_mass,
        "subsystems_kg": subsystems,
        "dry_remainder_kg": 255.0 - subsystems,
    }


def distance_at(st: State, arrival_yr: float) -> dict:
    d = float(np.linalg.norm(st.position_at(arrival_yr * YEAR)))
    vinf = intercept_terms(st, arrival_yr)["vinf_kms"] * KMS
    travel = vinf * arrival_yr * YEAR
    return {
        "target_distance_ly": d / LY,
        "cruise_distance_ly": travel / LY,
        "closure_error_au": (travel - d) / AU,
    }


def main() -> int:
    st = alpha_centauri_state()
    tan_yr = tangential_arrival_yr(st)
    tan = departure_for_arrival(st, tan_yr)
    at_58000 = departure_for_arrival(st, 58_000.0)

    opt = minimize_scalar(
        lambda y: departure_for_arrival(st, y)["dv_impulsive_kms"],
        bounds=(58_000.0, 100_000.0),
        method="bounded",
        options={"xatol": 1e-4},
    )
    opt_dep = departure_for_arrival(st, float(opt.x))
    dep_20_budget_kms = 20.0
    spiral = spiral_escape_dv(tan["vinf_earth_kms"] * KMS)

    masses = mass_table(
        {
            "tangential_impulsive_floor": tan["dv_impulsive_kms"],
            "min_dv_impulsive_floor": opt_dep["dv_impulsive_kms"],
            "design_sep_budget": dep_20_budget_kms,
            "tangential_spiral_bound": spiral["dv_low_thrust_kms"],
        }
    )
    closure = {
        label: dry_mass_closure(row["propellant_kg"])
        for label, row in masses.items()
        if label.endswith("isp3000")
    }

    results = {
        "alpha_centauri": {
            "distance_now_au": float(np.linalg.norm(st.r) / AU),
            "distance_now_ly": float(np.linalg.norm(st.r) / LY),
            "space_speed_kms": float(np.linalg.norm(st.v) / KMS),
            "state_r_km": (st.r / KMS).tolist(),
            "state_v_kms": (st.v / KMS).tolist(),
        },
        "tangential_min_speed": tan,
        "slider_58000": at_58000,
        "min_departure_dv": opt_dep,
        "low_thrust_spiral_for_tangential": spiral,
        "propellant_masses": masses,
        "dry_mass_closure_isp3000": closure,
        "distance_checks": {
            "tangential": distance_at(st, tan_yr),
            "min_dv": distance_at(st, opt_dep["arrival_yr"]),
            "seventy_five_kyr": distance_at(st, 75_000.0),
        },
    }

    checks = [
        (58_100.0 < tan["arrival_yr"] < 58_180.0, "tangential year"),
        (23.20 < tan["vinf_kms"] < 23.35, "tangential vinf"),
        (-10.5 < tan["tilt_deg"] < -9.7, "tangential tilt"),
        (14.5 < tan["dv_impulsive_kms"] < 14.8, "tangential impulsive dv"),
        (72_700.0 < opt_dep["arrival_yr"] < 72_900.0, "min-dv year"),
        (13.86 < opt_dep["dv_impulsive_kms"] < 13.89, "min-dv floor"),
        (tan["dv_impulsive_kms"] > opt_dep["dv_impulsive_kms"], "min-speed costs more dv"),
        (25.0 < spiral["dv_low_thrust_kms"] < 27.0, "tangential spiral bound"),
        (160.0 < masses["tangential_impulsive_floor_isp3000"]["propellant_kg"] < 170.0, "floor xenon"),
        (240.0 < masses["design_sep_budget_isp3000"]["propellant_kg"] < 255.0, "20 km/s xenon"),
        (350.0 < masses["tangential_spiral_bound_isp3000"]["propellant_kg"] < 380.0, "spiral xenon"),
        (
            closure["design_sep_budget_isp3000"]["dry_remainder_kg"] > 140.0,
            "default dry-mass closure",
        ),
    ]
    failed = [name for ok, name in checks if not ok]
    print(json.dumps(results, indent=2, sort_keys=True))
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("V4 prompt 10 checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
