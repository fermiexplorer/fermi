"""Gemini independent numerical audit for Project Fermi.

Cross-checks the engine with different methods and standard packages:
* Astropy-based coordinate conversion for Alpha Centauri.
* solve_ivp for Earth escape spiral integration.
* scipy.optimize for finding minimum speed arrival time.
* Detailed vector calculations for the 58 kyr tangential intercept and 73 kyr min-dv.
"""

import json
import math
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from scipy.integrate import solve_ivp

# --- SI constants ---
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
V_EARTH_ORBITAL = math.sqrt(MU_SUN / AU)
V_ESC_SUN_1AU = math.sqrt(2.0 * MU_SUN / AU)

# Alpha Centauri catalog
AC_RA_DEG = 219.9021
AC_DEC_DEG = -60.8340
AC_DIST_LY = 4.344
AC_PMRA_MASYR = -3620.0
AC_PMDEC_MASYR = 694.0
AC_RV_KMS = -22.4

def rot_x(angle):
    return np.array([
        [1.0, 0.0, 0.0],
        [0.0, math.cos(angle), math.sin(angle)],
        [0.0, -math.sin(angle), math.cos(angle)]
    ])

def ac_state_astropy():
    coord = SkyCoord(
        ra=AC_RA_DEG * u.deg,
        dec=AC_DEC_DEG * u.deg,
        distance=AC_DIST_LY * u.lyr,
        pm_ra_cosdec=AC_PMRA_MASYR * u.mas / u.yr,
        pm_dec=AC_PMDEC_MASYR * u.mas / u.yr,
        radial_velocity=AC_RV_KMS * u.km / u.s,
        frame="icrs"
    )
    cart = coord.cartesian
    pos_eq = np.array([cart.x.to_value(u.m), cart.y.to_value(u.m), cart.z.to_value(u.m)])
    vel_eq = np.array([
        coord.velocity.d_x.to_value(u.m/u.s),
        coord.velocity.d_y.to_value(u.m/u.s),
        coord.velocity.d_z.to_value(u.m/u.s)
    ])
    rot = rot_x(OBLIQUITY)
    return rot @ pos_eq, rot @ vel_eq

def req_vinf(pos, vel, t_yr):
    t_s = t_yr * YEAR
    ac_pos_at_t = pos + vel * t_s
    return ac_pos_at_t / t_s

def departure_v_earth(v_inf_helio_vec):
    v_inf_mag = np.linalg.norm(v_inf_helio_vec)
    v_z = v_inf_helio_vec[2]
    v_in = np.hypot(v_inf_helio_vec[0], v_inf_helio_vec[1])
    angle = math.atan2(v_z, v_in)  # retain sign!
    
    v_dep = math.sqrt(v_inf_mag**2 + V_ESC_SUN_1AU**2)
    # Cosine law: v_inf_earth^2 = v_dep^2 + V_EARTH^2 - 2*v_dep*V_EARTH*cos(beta)
    v_e_sq = v_dep**2 + V_EARTH_ORBITAL**2 - 2 * v_dep * V_EARTH_ORBITAL * math.cos(angle)
    return math.sqrt(max(v_e_sq, 0.0)), v_dep, angle

def impulsive_dv(v_inf_e, alt_km=400):
    r = R_EARTH + alt_km * 1e3
    v_circ = math.sqrt(MU_EARTH / r)
    v_esc = math.sqrt(2 * MU_EARTH / r)
    v_peri = math.sqrt(v_inf_e**2 + v_esc**2)
    return v_peri - v_circ

def spiral_dv_solve_ivp(v_inf_e, alt_km=400, accel=5e-4):
    r0 = R_EARTH + alt_km * 1e3
    v_circ = math.sqrt(MU_EARTH / r0)
    target_energy = 0.5 * v_inf_e**2
    
    def deriv(t, state):
        x, y, vx, vy = state
        r = math.hypot(x, y)
        v = math.hypot(vx, vy)
        r3 = r**3
        ax = -MU_EARTH * x / r3 + accel * vx / v
        ay = -MU_EARTH * y / r3 + accel * vy / v
        return [vx, vy, ax, ay]
        
    def event(t, state):
        x, y, vx, vy = state
        r = math.hypot(x, y)
        v = math.hypot(vx, vy)
        return (0.5 * v**2 - MU_EARTH / r) - target_energy
    
    event.terminal = True
    event.direction = 1
    
    y0 = [r0, 0.0, 0.0, v_circ]
    res = solve_ivp(deriv, [0, 200*YEAR], y0, events=event, rtol=1e-8, atol=1e-8)
    return accel * res.t[-1]

def prop_mass(dry_mass, dv, isp):
    ve = isp * G0
    return dry_mass * (math.exp(dv / ve) - 1.0)

if __name__ == "__main__":
    pos, vel = ac_state_astropy()
    
    # 58,138 yr (Tangential arrival)
    t_tang_yr = 58138.0
    vinf_tang = req_vinf(pos, vel, t_tang_yr)
    v_inf_e_tang, v_dep_tang, angle_tang = departure_v_earth(vinf_tang)
    imp_dv_tang = impulsive_dv(v_inf_e_tang)
    sp_dv_tang = spiral_dv_solve_ivp(v_inf_e_tang)
    
    # Propellant masses at Isp 3000s
    dry_mass = 255.0
    prop_3000_imp_tang = prop_mass(dry_mass, imp_dv_tang, 3000.0)
    prop_3000_mid_tang = prop_mass(dry_mass, 20000.0, 3000.0)
    prop_3000_sp_tang = prop_mass(dry_mass, sp_dv_tang, 3000.0)
    
    # Propellant masses at Isp 4000s
    prop_4000_imp_tang = prop_mass(dry_mass, imp_dv_tang, 4000.0)
    prop_4000_mid_tang = prop_mass(dry_mass, 20000.0, 4000.0)
    prop_4000_sp_tang = prop_mass(dry_mass, sp_dv_tang, 4000.0)

    # 72,800 yr (Min-DV arrival approx)
    t_mindv_yr = 72800.0
    vinf_mindv = req_vinf(pos, vel, t_mindv_yr)
    v_inf_e_mindv, v_dep_mindv, angle_mindv = departure_v_earth(vinf_mindv)
    imp_dv_mindv = impulsive_dv(v_inf_e_mindv)
    sp_dv_mindv = spiral_dv_solve_ivp(v_inf_e_mindv)
    prop_3000_imp_mindv = prop_mass(dry_mass, imp_dv_mindv, 3000.0)
    prop_3000_sp_mindv = prop_mass(dry_mass, sp_dv_mindv, 3000.0)

    out = {
        "ac_now_distance_au": np.linalg.norm(pos) / AU,
        "ac_now_distance_ly": np.linalg.norm(pos) / LY,
        "ac_vel_kms": np.linalg.norm(vel) / KMS,
        
        "tangential_58k": {
            "arrival_yr": t_tang_yr,
            "v_inf_helio_vec_kms": (vinf_tang / KMS).tolist(),
            "v_inf_helio_mag_kms": np.linalg.norm(vinf_tang) / KMS,
            "bare_aim_term_kms": (pos / (t_tang_yr * YEAR) / KMS).tolist(),
            "bare_aim_term_mag_kms": np.linalg.norm(pos) / (t_tang_yr * YEAR) / KMS,
            "ac_vel_vec_kms": (vel / KMS).tolist(),
            "plane_angle_deg": math.degrees(angle_tang),
            "v_dep_helio_kms": v_dep_tang / KMS,
            "v_inf_earth_kms": v_inf_e_tang / KMS,
            "impulsive_dv_kms": imp_dv_tang / KMS,
            "spiral_dv_kms": sp_dv_tang / KMS,
            "prop_3000s": {
                "impulsive_kg": prop_3000_imp_tang,
                "mid_20km_kg": prop_3000_mid_tang,
                "spiral_kg": prop_3000_sp_tang
            },
            "prop_4000s": {
                "impulsive_kg": prop_4000_imp_tang,
                "mid_20km_kg": prop_4000_mid_tang,
                "spiral_kg": prop_4000_sp_tang
            }
        },
        
        "mindv_72k": {
            "arrival_yr": t_mindv_yr,
            "v_inf_helio_mag_kms": np.linalg.norm(vinf_mindv) / KMS,
            "plane_angle_deg": math.degrees(angle_mindv),
            "v_dep_helio_kms": v_dep_mindv / KMS,
            "v_inf_earth_kms": v_inf_e_mindv / KMS,
            "impulsive_dv_kms": imp_dv_mindv / KMS,
            "spiral_dv_kms": sp_dv_mindv / KMS,
            "prop_3000s_impulsive_kg": prop_3000_imp_mindv,
            "prop_3000s_spiral_kg": prop_3000_sp_mindv
        }
    }
    
    with open("audit/gemini/gemini_results_v2.json", "w") as f:
        json.dump(out, f, indent=2)
    print("Done")
