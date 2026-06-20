"""Audit 1 -- Alpha Centauri ephemeris, cross-checked against astropy.

The engine builds AC's 3-D ecliptic state from a hand-rolled spherical->Cartesian
transform. Here we rebuild it with astropy's independent coordinate machinery and
confirm position, space velocity, and the resulting closest approach agree.
"""

from __future__ import annotations

import numpy as np

from _util import check, rel_err, summary

from fermi_sim import constants as c
from fermi_sim.astro import (
    AC_DEC_DEG,
    AC_DIST_LY,
    AC_PMDEC_MASYR,
    AC_PMRA_MASYR,
    AC_RA_DEG,
    AC_RV_KMS,
    alpha_centauri_state,
    closest_approach,
)


def astropy_state():
    import astropy.units as u
    from astropy.coordinates import BarycentricMeanEcliptic, SkyCoord

    sc = SkyCoord(
        ra=AC_RA_DEG * u.deg,
        dec=AC_DEC_DEG * u.deg,
        distance=AC_DIST_LY * u.lightyear,
        pm_ra_cosdec=AC_PMRA_MASYR * u.mas / u.yr,
        pm_dec=AC_PMDEC_MASYR * u.mas / u.yr,
        radial_velocity=AC_RV_KMS * u.km / u.s,
        frame="icrs",
    )
    ecl = sc.transform_to(BarycentricMeanEcliptic())
    cart = ecl.cartesian
    r = cart.xyz.to(u.m).value
    v = cart.differentials["s"].d_xyz.to(u.m / u.s).value
    return np.array(r), np.array(v)


def run() -> None:
    print("== Audit 1: ephemeris vs astropy ==")
    st = alpha_centauri_state()
    r_ap, v_ap = astropy_state()

    # Distances and speeds (frame-independent magnitudes).
    d_engine = np.linalg.norm(st.r)
    d_ap = np.linalg.norm(r_ap)
    check("distance magnitude matches astropy (<0.5%)",
          rel_err(d_engine, d_ap) < 5e-3,
          f"engine {d_engine/c.LY:.4f} ly vs astropy {d_ap/c.LY:.4f} ly")

    s_engine = np.linalg.norm(st.v)
    s_ap = np.linalg.norm(v_ap)
    check("space-velocity magnitude matches astropy (<1%)",
          rel_err(s_engine, s_ap) < 1e-2,
          f"engine {s_engine/c.KMS:.3f} vs astropy {s_ap/c.KMS:.3f} km/s")

    # Velocity *direction* (angle between the two vectors).
    cosang = float(np.dot(st.v, v_ap) / (s_engine * s_ap))
    ang = np.degrees(np.arccos(np.clip(cosang, -1, 1)))
    check("velocity direction agrees (<1.5 deg)", ang < 1.5, f"{ang:.3f} deg apart")

    # Radial velocity recovered from the engine state equals the catalogue input.
    v_rad = float(np.dot(st.r, st.v)) / d_engine
    check("recovered radial velocity == catalogue",
          rel_err(v_rad, AC_RV_KMS * c.KMS) < 1e-3,
          f"{v_rad/c.KMS:.3f} km/s vs {AC_RV_KMS} km/s")

    # Closest approach reproduced from each state independently.
    t_eng, d_close_eng = closest_approach(st)

    def closest(r0, v):
        t = -np.dot(r0, v) / np.dot(v, v)
        return t, np.linalg.norm(r0 + v * t)

    t_ap, d_close_ap = closest(r_ap, v_ap)
    check("closest-approach time ~28 kyr and matches astropy",
          abs(t_eng / c.YEAR - 28000) < 2500 and rel_err(t_eng, t_ap) < 0.05,
          f"engine {t_eng/c.YEAR:,.0f} yr, astropy {t_ap/c.YEAR:,.0f} yr")
    check("closest-approach distance ~3.0 ly and matches astropy",
          abs(d_close_eng / c.LY - 3.0) < 0.3 and rel_err(d_close_eng, d_close_ap) < 0.05,
          f"engine {d_close_eng/c.LY:.3f} ly, astropy {d_close_ap/c.LY:.3f} ly")


if __name__ == "__main__":
    run()
    raise SystemExit(summary())
