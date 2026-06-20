"""Grok independent numerical audit for Project Fermi.

Does not import ``fermi_sim``. Cross-checks the engine with different methods
than ``audit/codex/v3_independent_checks.py``:

* Alpha Centauri state from astropy (not hand-built catalog algebra)
* Departure-dv minimum via coarse grid + parabolic refinement (not scipy)
* Earth escape spiral via a separate RK4 integrator (not fermi_sim departure)
* Fuel-cell optimum via golden-section search (codex uses scipy)
* Miss-distance tolerance from relative-velocity geometry

Run from repo root:

    .venv/bin/python audit/grok/grok_independent_checks.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord


# --- SI constants (match fermi_sim/constants.py) ---
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

# Project catalog (for comparison only — astropy is primary here).
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


def alpha_centauri_state_astropy() -> State:
    """Build AC state from astropy SkyCoord, then rotate to ecliptic."""
    coord = SkyCoord(
        ra=AC_RA_DEG * u.deg,
        dec=AC_DEC_DEG * u.deg,
        distance=AC_DIST_LY * u.lyr,
        pm_ra_cosdec=AC_PMRA_MASYR * u.mas / u.yr,
        pm_dec=AC_PMDEC_MASYR * u.mas / u.yr,
        radial_velocity=AC_RV_KMS * u.km / u.s,
        frame="icrs",
    )
    cart = coord.cartesian
    pos_eq = np.array([cart.x.to_value(u.m), cart.y.to_value(u.m), cart.z.to_value(u.m)])
    vel_eq = np.array(
        [
            coord.velocity.d_x.to_value(u.m / u.s),
            coord.velocity.d_y.to_value(u.m / u.s),
            coord.velocity.d_z.to_value(u.m / u.s),
        ]
    )
    return State(equatorial_to_ecliptic(pos_eq), equatorial_to_ecliptic(vel_eq))


def alpha_centauri_state_hand() -> State:
    """Hand-built catalog state (for astropy agreement check)."""
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


def intercept_at(st: State, arrival_yr: float) -> dict[str, float]:
    t = arrival_yr * YEAR
    v = st.position_at(t) / t
    v_in = float(np.hypot(v[0], v[1]))
    return {
        "arrival_yr": arrival_yr,
        "vinf_kms": float(np.linalg.norm(v) / KMS),
        "tilt_deg": math.degrees(math.atan2(float(v[2]), v_in)),
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


def departure_at(st: State, arrival_yr: float) -> dict[str, float]:
    sol = intercept_at(st, arrival_yr)
    vinf_sun = sol["vinf_kms"] * KMS
    vinf_e, v_dep = v_inf_earth_required(vinf_sun, sol["tilt_deg"])
    return {
        **sol,
        "vinf_earth_kms": vinf_e / KMS,
        "vdep_1au_kms": v_dep / KMS,
        "dv_impulsive_kms": impulsive_dv_from_leo(vinf_e) / KMS,
    }


def grid_refine_min_dv(st: State, lo: float, hi: float, coarse_step: float = 200.0) -> dict:
    """Find min impulsive dv via coarse grid + 3-point parabolic fit."""
    years = np.arange(lo, hi + coarse_step, coarse_step)
    dvs = []
    for y in years:
        dvs.append(departure_at(st, float(y))["dv_impulsive_kms"])
    dvs = np.array(dvs)
    i_min = int(np.argmin(dvs))
    if 0 < i_min < len(years) - 1:
        y0, y1, y2 = years[i_min - 1], years[i_min], years[i_min + 1]
        f0, f1, f2 = dvs[i_min - 1], dvs[i_min], dvs[i_min + 1]
        denom = f0 - 2.0 * f1 + f2
        if abs(denom) > 1e-12:
            y_opt = y1 + 0.5 * (f0 - f2) / denom * coarse_step
        else:
            y_opt = y1
    else:
        y_opt = float(years[i_min])
    y_opt = float(np.clip(y_opt, lo, hi))
    return {"method": "grid+parabolic", "optimum_yr": y_opt, "optimum": departure_at(st, y_opt)}


def spiral_escape_dv_grok(
    mu: float, r0: float, v_inf_target: float, accel: float = 5e-4
) -> float:
    """Independent constant-tangential-thrust spiral (RK4, different implementation)."""
    target_e = 0.5 * v_inf_target**2
    v_circ = math.sqrt(mu / r0)
    x, y, vx, vy = r0, 0.0, 0.0, v_circ
    t = 0.0
    max_t = 200.0 * YEAR

    def accel_vec(px, py, pvx, pvy):
        r = math.hypot(px, py)
        v = math.hypot(pvx, pvy)
        inv_r3 = 1.0 / (r**3)
        ax = -mu * px * inv_r3 + accel * pvx / v
        ay = -mu * py * inv_r3 + accel * pvy / v
        return ax, ay

    while t < max_t:
        r = math.hypot(x, y)
        v = math.hypot(vx, vy)
        if 0.5 * v * v - mu / r >= target_e:
            break
        period = 2.0 * math.pi * math.sqrt(r**3 / mu)
        dt = min(max(2.0, 0.005 * period), 1800.0)
        ax1, ay1 = accel_vec(x, y, vx, vy)
        ax2, ay2 = accel_vec(x + 0.5 * dt * vx, y + 0.5 * dt * vy, vx + 0.5 * dt * ax1, vy + 0.5 * dt * ay1)
        ax3, ay3 = accel_vec(x + 0.5 * dt * vx, y + 0.5 * dt * vy, vx + 0.5 * dt * ax2, vy + 0.5 * dt * ay2)
        ax4, ay4 = accel_vec(x + dt * vx, y + dt * vy, vx + dt * ax3, vy + dt * ay3)
        x += (dt / 6.0) * (vx + 2 * (vx + 0.5 * dt * ax1) + 2 * (vx + 0.5 * dt * ax2) + (vx + dt * ax3))
        y += (dt / 6.0) * (vy + 2 * (vy + 0.5 * dt * ay1) + 2 * (vy + 0.5 * dt * ay2) + (vy + dt * ay3))
        vx += (dt / 6.0) * (ax1 + 2 * ax2 + 2 * ax3 + ax4)
        vy += (dt / 6.0) * (ay1 + 2 * ay2 + 2 * ay3 + ay4)
        t += dt
    return accel * t


def golden_min(f, lo: float, hi: float, tol: float = 0.5) -> float:
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    c1 = b - gr * (b - a)
    c2 = a + gr * (b - a)
    f1, f2 = f(c1), f(c2)
    while b - a > tol:
        if f1 < f2:
            b, c2, f2 = c2, c1, f1
            c1 = b - gr * (b - a)
            f1 = f(c1)
        else:
            a, c1, f1 = c1, c2, f2
            c2 = a + gr * (b - a)
            f2 = f(c2)
    return 0.5 * (a + b)


def propellant_mass(dry_mass: float, dv: float, isp_s: float) -> float:
    ve = isp_s * G0
    return dry_mass * (math.exp(dv / ve) - 1.0)


def solar_summary(
    dry: float = 255.0,
    dv: float = 20_000.0,
    isp: float = 3000.0,
    power: float = 5000.0,
    eff: float = 0.20,
    areal: float = 3.0,
) -> dict[str, float]:
    prop = propellant_mass(dry, dv, isp)
    area = power / (1361.0 * eff)
    array_mass = area * areal
    engine = 6.0 * power / 1000.0
    tank = 0.08 * prop
    return {
        "prop_kg": prop,
        "wet_kg": dry + prop,
        "array_area_m2": area,
        "array_mass_kg": array_mass,
        "engine_ppu_kg": engine,
        "tank_kg": tank,
        "remainder_kg": dry - array_mass - engine - tank,
    }


def fuelcell_optimum() -> dict[str, float]:
    dry, dv, eta_t, eta_fc, e_raw = 255.0, 20_000.0, 0.6, 0.6, 8.0e6

    def consumables(isp: float) -> float:
        ve = isp * G0
        prop = propellant_mass(dry, dv, isp)
        energy = 0.5 * prop * ve**2 / eta_t
        react = energy / (eta_fc * e_raw)
        return prop + react

    isp_opt = golden_min(consumables, 200.0, 4000.0)
    return {
        "opt_isp_s": isp_opt,
        "opt_consumables_kg": consumables(isp_opt),
        "consumables_3000_kg": consumables(3000.0),
    }


def miss_half_window_yr(st: State, arrival_yr: float, miss_au: float = 2600.0) -> float:
    t = arrival_yr * YEAR
    v = st.position_at(t) / t
    rel = float(np.linalg.norm(v - st.v))
    return miss_au * AU / rel / YEAR


def distance_check(st: State, arrival_yr: float) -> dict[str, float]:
    t = arrival_yr * YEAR
    dist_ly = float(np.linalg.norm(st.position_at(t)) / LY)
    vinf = intercept_at(st, arrival_yr)["vinf_kms"]
    reach_ly = vinf * KMS * t / LY
    return {
        "ac_distance_ly": dist_ly,
        "straight_line_reach_ly": reach_ly,
        "closure_error_pct": 100.0 * abs(reach_ly - dist_ly) / dist_ly,
    }


def main() -> int:
    st_astro = alpha_centauri_state_astropy()
    st_hand = alpha_centauri_state_hand()

    astro_dist = float(np.linalg.norm(st_astro.r) / LY)
    hand_dist = float(np.linalg.norm(st_hand.r) / LY)
    astro_speed = float(np.linalg.norm(st_astro.v) / KMS)
    hand_speed = float(np.linalg.norm(st_hand.v) / KMS)

    opt = grid_refine_min_dv(st_astro, 58_000.0, 100_000.0)
    dep_75 = departure_at(st_astro, 75_000.0)
    dep_70 = departure_at(st_astro, 70_000.0)

    v_inf_e_75 = dep_75["vinf_earth_kms"] * KMS
    spiral_75 = spiral_escape_dv_grok(MU_EARTH, R_EARTH + 400e3, v_inf_e_75) / KMS

    solar = solar_summary()
    fuel = fuelcell_optimum()
    fuel["reactant_to_array_ratio_3000"] = (
        fuel["consumables_3000_kg"] - propellant_mass(255.0, 20_000.0, 3000.0)
    ) / solar["array_mass_kg"]

    t_close, d_close = closest_approach(st_astro)

    # Sensitivity: how much does 20 km/s SEP budget move with Isp?
    isp_sweep = {}
    for isp in (2000, 2500, 3000, 3500, 4000):
        s = solar_summary(isp=isp)
        isp_sweep[str(isp)] = {
            "prop_frac": s["prop_kg"] / s["wet_kg"],
            "wet_kg": s["wet_kg"],
            "remainder_kg": s["remainder_kg"],
        }

    # Power sensitivity: array mass vs burn power
    power_sweep = {}
    for p in (3000, 5000, 8000, 12000):
        s = solar_summary(power=float(p))
        power_sweep[str(p)] = {"array_mass_kg": s["array_mass_kg"], "remainder_kg": s["remainder_kg"]}

    results = {
        "astropy_vs_hand": {
            "distance_ly_err_pct": 100.0 * abs(astro_dist - hand_dist) / astro_dist,
            "speed_kms_err_pct": 100.0 * abs(astro_speed - hand_speed) / astro_speed,
        },
        "alpha_centauri": {
            "distance_now_ly": astro_dist,
            "space_speed_kms": astro_speed,
            "closest_approach_yr": t_close / YEAR,
            "closest_approach_ly": d_close / LY,
        },
        "departure_optimum": opt,
        "departure_75k": dep_75,
        "departure_70k": dep_70,
        "spiral_dv_75k_kms": spiral_75,
        "miss_tolerance": {
            "half_window_yr_at_75k": miss_half_window_yr(st_astro, 75_000.0),
            "half_window_yr_at_opt": miss_half_window_yr(st_astro, opt["optimum_yr"]),
        },
        "distance_closure": {
            "at_70k": distance_check(st_astro, 70_000.0),
            "at_75k": distance_check(st_astro, 75_000.0),
        },
        "solar_baseline": solar,
        "fuel_cell": fuel,
        "sensitivity_isp": isp_sweep,
        "sensitivity_power_w": power_sweep,
    }

    checks = [
        (results["astropy_vs_hand"]["distance_ly_err_pct"] < 0.01, "astropy/hand distance"),
        (results["astropy_vs_hand"]["speed_kms_err_pct"] < 0.01, "astropy/hand speed"),
        (72_700 < opt["optimum_yr"] < 72_900, "grid optimum year"),
        (13.86 < opt["optimum"]["dv_impulsive_kms"] < 13.89, "grid optimum dv"),
        (9.0 < (dep_75["dv_impulsive_kms"] - opt["optimum"]["dv_impulsive_kms"]) * 1000 < 12.0,
         "75k penalty m/s"),
        (700.0 < results["miss_tolerance"]["half_window_yr_at_75k"] < 720.0, "miss window 75k"),
        (results["distance_closure"]["at_75k"]["closure_error_pct"] < 0.01, "75k distance closure"),
        (24.0 < spiral_75 < 26.0, "spiral dv bracket"),
        (54.0 < solar["array_mass_kg"] < 56.0, "array mass"),
        (149.0 < solar["remainder_kg"] < 151.0, "dry mass closure"),
        (1300.0 < fuel["opt_isp_s"] < 1400.0, "fuel-cell opt isp"),
        (600.0 < fuel["reactant_to_array_ratio_3000"] < 750.0, "fuel-cell ratio"),
        (all(0.38 < v["prop_frac"] < 0.66 for v in isp_sweep.values()), "isp prop fraction range"),
        (all(v["remainder_kg"] > 100 for v in isp_sweep.values()), "isp mass closure"),
    ]

    failed = [name for ok, name in checks if not ok]
    print(json.dumps(results, indent=2, sort_keys=True))
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("Grok independent checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())