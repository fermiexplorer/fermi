"""Parameter sweeps for the Fermi mission design space.

Independent of fermi_sim — uses local astrodynamics helpers only.
Writes ``audit/grok/sweep_results.json``.

Run:  .venv/bin/python audit/grok/grok_sensitivity_sweeps.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord

OUT = Path(__file__).resolve().parent / "sweep_results.json"

AU = 1.495978707e11
LY = 9.4607304725808e15
YEAR = 3.15576e7
KMS = 1.0e3
G0 = 9.80665
MU_EARTH = 3.986004418e14
R_EARTH = 6.371e6
V_EARTH = math.sqrt(1.32712440018e20 / AU)
V_ESC_SUN_1AU = math.sqrt(2.0 * 1.32712440018e20 / AU)
OBLIQUITY = math.radians(23.439281)

AC_RA_DEG = 219.9021
AC_DEC_DEG = -60.8340
AC_DIST_LY = 4.344
AC_PMRA_MASYR = -3620.0
AC_PMDEC_MASYR = 694.0
AC_RV_KMS = -22.4


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


def ac_state() -> tuple[np.ndarray, np.ndarray]:
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
    return equatorial_to_ecliptic(pos_eq), equatorial_to_ecliptic(vel_eq)


def intercept(r0: np.ndarray, v_ac: np.ndarray, t_yr: float) -> tuple[float, float]:
    t = t_yr * YEAR
    pos = r0 + v_ac * t
    v = pos / t
    v_in = float(np.hypot(v[0], v[1]))
    return float(np.linalg.norm(v) / KMS), math.degrees(math.atan2(float(v[2]), v_in))


def v_inf_earth(vinf_sun: float, tilt_deg: float) -> float:
    v_dep = math.sqrt(vinf_sun**2 + V_ESC_SUN_1AU**2)
    beta = math.radians(tilt_deg)
    v_inf_e_sq = v_dep**2 + V_EARTH**2 - 2.0 * v_dep * V_EARTH * math.cos(beta)
    return math.sqrt(max(v_inf_e_sq, 0.0))


def impulsive_dv(vinf_e: float) -> float:
    r = R_EARTH + 400e3
    v_circ = math.sqrt(MU_EARTH / r)
    v_esc = math.sqrt(2.0 * MU_EARTH / r)
    return math.sqrt(vinf_e**2 + v_esc**2) - v_circ


def prop_mass(dry: float, dv: float, isp: float) -> float:
    return dry * (math.exp(dv / (isp * G0)) - 1.0)


def main() -> None:
    r0, vac = ac_state()

    # Sweep 1: departure dv vs arrival time
    dv_curve = []
    for t_yr in range(58_000, 100_001, 500):
        vinf, tilt = intercept(r0, vac, float(t_yr))
        dv = impulsive_dv(v_inf_earth(vinf * KMS, tilt)) / KMS
        dv_curve.append({"t_yr": t_yr, "dv_impulsive_kms": round(dv, 4), "vinf_kms": round(vinf, 4), "tilt_deg": round(tilt, 3)})

    min_pt = min(dv_curve, key=lambda x: x["dv_impulsive_kms"])

    # Sweep 2: wet mass vs dry mass at fixed 20 km/s, Isp 3000
    mass_trade = []
    for dry in range(150, 401, 25):
        prop = prop_mass(dry, 20_000.0, 3000.0)
        mass_trade.append({
            "dry_kg": dry,
            "prop_kg": round(prop, 1),
            "wet_kg": round(dry + prop, 1),
            "prop_frac": round(prop / (dry + prop), 3),
        })

    # Sweep 3: minimum cruise speed for 100k yr deadline
    deadline = []
    for vinf in np.linspace(19.0, 26.0, 71):
        # Solve |r0 + vac*T|/T = vinf  -> quadratic in u=1/T
        a = float(np.dot(r0, r0))
        b = float(np.dot(r0, vac))
        cc = float(np.dot(vac, vac)) - (vinf * KMS) ** 2
        disc = b * b - a * cc
        if disc < 0:
            t_yr = None
        else:
            u = max(((-b + math.sqrt(disc)) / a, (-b - math.sqrt(disc)) / a))
            t_yr = 1.0 / u / YEAR if u > 0 else None
        deadline.append({"vinf_kms": round(float(vinf), 2), "arrival_yr": round(t_yr, 0) if t_yr else None})

    # Find minimum vinf that still arrives within 100k yr
    feasible = [d for d in deadline if d["arrival_yr"] is not None and d["arrival_yr"] <= 100_000]
    min_vinf_100k = min(feasible, key=lambda x: x["vinf_kms"]) if feasible else None

    # Sweep 4: solar array mass vs cell efficiency (5 kW, 3 kg/m2)
    solar_eff = []
    for eff in np.linspace(0.12, 0.30, 19):
        area = 5000.0 / (1361.0 * eff)
        solar_eff.append({
            "cell_efficiency": round(float(eff), 3),
            "array_area_m2": round(area, 2),
            "array_mass_kg": round(area * 3.0, 1),
        })

    payload = {
        "dv_vs_arrival": {
            "min_point": min_pt,
            "flat_region_13_9_to_14_0_kms": [
                p for p in dv_curve
                if 13.9 <= p["dv_impulsive_kms"] <= 14.0
            ],
        },
        "mass_trade_20kms_isp3000": mass_trade,
        "deadline_100k_yr": {
            "min_vinf_within_100k": min_vinf_100k,
            "curve": deadline,
        },
        "solar_efficiency_sweep_5kw": solar_eff,
    }

    OUT.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT}")
    print(f"Min dv: {min_pt['dv_impulsive_kms']:.4f} km/s at {min_pt['t_yr']:,} yr")
    if min_vinf_100k:
        print(
            f"Min cruise v_inf for <=100k yr: {min_vinf_100k['vinf_kms']:.2f} km/s"
            f" -> arrives {min_vinf_100k['arrival_yr']:,.0f} yr"
        )
    flat = payload["dv_vs_arrival"]["flat_region_13_9_to_14_0_kms"]
    if flat:
        print(f"Flat dv band 13.9-14.0 km/s spans {flat[0]['t_yr']:,} - {flat[-1]['t_yr']:,} yr")


if __name__ == "__main__":
    main()