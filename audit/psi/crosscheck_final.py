"""Deep cross-check of the PSI final feasibility assessment (July 2026) against fermi_sim.

Re-derives every engine-comparable headline of
``PSI_FermiExplorerInterstellarPrecursor_FeasibilityAssessment.pdf`` (this directory)
with OUR code and prints measured deltas. Run from the repo root:

    .venv/bin/python audit/psi/crosscheck_final.py

Stages:

  0. Astrometry of the adopted AC state (d, |v|, vr, vt) vs their Kervella-based values.
  1. Their Table 14 arrival-epoch trade (55-85 kyr): v_inf, tilt, impulsive floor.
  2. Landmarks: departure-dv optimum, tangential intercept, ecliptic crossing,
     closest approach, 500-kyr horizon.
  3. Outward-spiral power wall: ceilings at a0 = 1.5, 5, 10 x 1e-4 m/s^2 vs 0/3.4/17.0.
  4. Pumped design point (a0 2.5e-4, Isp 2800): our bang-bang + schedule taxes vs their
     23.97-24.0 km/s 12-yr figure, and the thermal-model comparison.
  5. Their Appendix C mass-closure algebra, replayed independently (and via our
     minimal_dry_mass fixed point).
  6. Out-of-plane cost: our |sin(beta)| pricing vs their measured 0.58 km/s, and
     whether the 79.25-kyr corner minimum survives their measured (cheaper) tilt cost.
  7. Alternative targets from OUR web catalog states (LSPM J2146+3813, Lambda Serpentis)
     vs their Table 8 (perihelion, epoch, impulsive floor, cruise speed).
"""
import math
import sys

sys.path.insert(0, ".")
import numpy as np

from fermi_sim import constants as c
from fermi_sim.astro import alpha_centauri_state, closest_approach
from fermi_sim.intercept import solve_intercept, min_speed_arrival, ecliptic_crossing_time
from fermi_sim.departure import (
    v_inf_earth_required, impulsive_dv_from_leo, sep_achievable_vinf,
    perihelion_pumped_vinf, pump_tax_for, pumped_departure_dv,
)
from fermi_sim.spacecraft import minimal_dry_mass

STATE = alpha_centauri_state()
MISS = 2600.0 * c.AU


def floor_from(vinf, tilt_deg, alt_km=400.0):
    ve, _ = v_inf_earth_required(vinf, tilt_deg)
    return impulsive_dv_from_leo(ve, alt_km), ve


def geom(T_yr, shave=0.0):
    s = solve_intercept(STATE, T_yr * c.YEAR)
    v = max(0.0, s.v_inf - shave / (T_yr * c.YEAR))
    return v, s.plane_angle_deg


print("=" * 78)
print("STAGE 0 - adopted AC astrometry vs PSI (Kervella et al. barycentric)")
r0, v0 = STATE.r, STATE.v
d_ly = np.linalg.norm(r0) / c.LY
vmag = np.linalg.norm(v0)
rhat = r0 / np.linalg.norm(r0)
vr = float(np.dot(v0, rhat))
vt = float(np.linalg.norm(v0 - vr * rhat))
print(f"  distance      ours {d_ly:.4f} ly      PSI 4.365 ly")
print(f"  |v|           ours {vmag/1e3:.3f} km/s   PSI 32.38 km/s")
print(f"  v_r           ours {vr/1e3:+.3f} km/s   PSI -22.40 km/s")
print(f"  v_t           ours {vt/1e3:.3f} km/s   PSI 23.38 km/s")

print("=" * 78)
print("STAGE 1 - PSI Table 14 (55-85 kyr trade): v_inf / tilt / impulsive floor")
# (T yr, v_inf km/s, tilt deg, impulsive floor km/s) from the report, p.59
PSI_T14 = [
    (55000, 23.202, -12.33, 15.108), (56000, 23.185, -11.62, 14.939),
    (57000, 23.175, -10.94, 14.786), (58000, 23.173, -10.27, 14.649),
    (59000, 23.177, -9.63, 14.525), (60000, 23.187, -9.00, 14.415),
    (61000, 23.202, -8.40, 14.318), (62000, 23.222, -7.81, 14.232),
    (63000, 23.246, -7.25, 14.157), (64000, 23.273, -6.70, 14.092),
    (65000, 23.305, -6.17, 14.036), (66000, 23.339, -5.66, 13.990),
    (67000, 23.376, -5.16, 13.951), (68000, 23.415, -4.68, 13.919),
    (69000, 23.457, -4.21, 13.894), (70000, 23.500, -3.76, 13.876),
    (71000, 23.545, -3.32, 13.863), (72000, 23.592, -2.90, 13.856),
    (73000, 23.640, -2.48, 13.854), (74000, 23.689, -2.09, 13.856),
    (75000, 23.739, -1.70, 13.862), (76000, 23.790, -1.32, 13.872),
    (77000, 23.841, -0.96, 13.886), (78000, 23.893, -0.61, 13.902),
    (79000, 23.946, -0.26, 13.922), (80000, 23.999, +0.07, 13.944),
    (81000, 24.052, +0.39, 13.968), (82000, 24.105, +0.71, 13.994),
    (83000, 24.159, +1.01, 14.023), (84000, 24.212, +1.31, 14.053),
    (85000, 24.266, +1.60, 14.085),
]
dv_ex, dv_sh, dt_ex, df_ex, df_sh = [], [], [], [], []
for T, pvinf, ptilt, pfloor in PSI_T14:
    ve_ex, tilt = geom(T)
    ve_shv, _ = geom(T, shave=MISS)
    f_ex, _ = floor_from(ve_ex, tilt)
    f_sh, _ = floor_from(ve_shv, tilt)
    dv_ex.append(ve_ex / 1e3 - pvinf)
    dv_sh.append(ve_shv / 1e3 - pvinf)
    dt_ex.append(tilt - ptilt)
    df_ex.append(f_ex / 1e3 - pfloor)
    df_sh.append(f_sh / 1e3 - pfloor)


def stat(name, arr, unit):
    a = np.array(arr)
    print(f"  {name:<44s} mean {a.mean():+8.4f}  max|.| {np.abs(a).max():7.4f} {unit}")


stat("v_inf, exact intercept - PSI", dv_ex, "km/s")
stat("v_inf, 2600-AU max-shave - PSI", dv_sh, "km/s")
stat("aim tilt - PSI", dt_ex, "deg")
stat("impulsive floor, exact - PSI", df_ex, "km/s")
stat("impulsive floor, shaved - PSI", df_sh, "km/s")

print("=" * 78)
print("STAGE 2 - landmarks")
# departure-dv optimum (our floor argmin, 1-yr fine scan)
best = None
for T in range(66000, 82001, 25):
    v, t = geom(T, shave=MISS)
    f, ve = floor_from(v, t)
    if best is None or f < best[1]:
        best = (T, f, v, t, ve)
print(f"  floor argmin   ours T={best[0]} yr  floor {best[1]/1e3:.3f}  v_inf {best[2]/1e3:.3f}"
      f"  tilt {best[3]:+.2f}  v_infE {best[4]/1e3:.3f}")
print(f"                 PSI  T=73012 yr  floor 13.854  v_inf 23.640  tilt -2.48  v_infE 18.59")
lo, hi = geom(best[0] - 1000, shave=MISS), geom(best[0] + 1000, shave=MISS)
flo, _ = floor_from(*lo)
fhi, _ = floor_from(*hi)
print(f"  flatness: floor(+/-1 kyr) - min = {flo/1e3-best[1]/1e3:+.4f} / {fhi/1e3-best[1]/1e3:+.4f} km/s"
      f"   (PSI: <0.1 km/s across 66.9-80.4 kyr)")
ms = min_speed_arrival(STATE)
print(f"  tangential     ours T*={ms.arrival_time_yr:,.0f} yr  v_inf {ms.v_inf/1e3:.3f} km/s"
      f"   PSI T*=58,422 yr  v_inf 23.38 (= v_t)")
tcx = ecliptic_crossing_time(STATE) / c.YEAR
print(f"  ecliptic cross ours T={tcx:,.1f} yr   PSI T=79,786 yr")
# attribute the crossing offset to the tilt zero: slope of tilt vs T near the crossing
_, t1 = geom(78500)
_, t2 = geom(80500)
slope = (t2 - t1) / 2000.0  # deg per yr
dtilt = float(np.mean(np.abs(dt_ex)))  # measured tilt offset vs their Table 14
print(f"    tilt slope {slope*1000:.3f} deg/kyr; measured tilt offset {dtilt:.2f} deg ->"
      f" shifts the zero by ~{dtilt/slope:,.0f} yr (observed offset: 534 yr)")
tca, dca = closest_approach(STATE)
print(f"  closest appr.  ours t={tca/c.YEAR:,.0f} yr  d={dca/c.LY:.3f} ly   PSI 27,955 yr  3.152 ly")
v5, t5 = geom(500000)
f5, _ = floor_from(v5, t5)
v5s, _ = geom(500000, shave=MISS)
f5s, _ = floor_from(v5s, t5)
print(f"  500-kyr        ours v_inf {v5/1e3:.2f} (shaved {v5s/1e3:.2f})  floor {f5/1e3:.2f}"
      f" (shaved {f5s/1e3:.2f})   PSI v_inf 30.61  floor 19.93")

print("=" * 78)
print("STAGE 3 - outward-spiral power wall (PSI: v_inf ceilings 0 / 3.4 / 17.0 km/s"
      " at a0 = 1.5 / 5 / 10 x 1e-4 m/s^2, integrators agreeing to 2.7%)")
ISP, EFF, WET = 3000.0, 0.5, 100.0
for a0, psi_ceiling in ((1.5e-4, 0.0), (5.0e-4, 3.4), (1.0e-3, 17.0)):
    F = a0 * WET
    P = F * ISP * c.G0 / (2.0 * EFF)
    vv = sep_achievable_vinf(P, WET, 10.0, ISP, eff=EFF)
    print(f"  a0 {a0:.1e}: ours {vv/1e3:6.2f} km/s   PSI ~{psi_ceiling:.1f} km/s")

print("=" * 78)
print("STAGE 4 - perihelion pumping at the design point (a0 2.5e-4, Isp 2800)")
vb, dvb, yrb, revb = perihelion_pumped_vinf(2.5e-4, 23640.0, power_model="cap")
print(f"  bang-bang, 4x cap   : v_inf {vb/1e3:.2f}  dv {dvb/1e3:.2f} km/s  {yrb:.1f} yr  {revb} revs")
for sched, label in (("optimized", "optimised schedule, 4x cap (baked)"),
                     ("thermal", "optimised schedule, DERIVED thermal cap (baked)")):
    tax = pump_tax_for(23640.0, sched)
    print(f"  {label:<36s}: dv {(23640.0+tax)/1e3:.2f} km/s")
print("  PSI (4x cap assumption): best-found 23.97 km/s production / 23.985 quarter-step,"
      " carried 24.0; 12.0 yr; mass fraction 0.418")
print("  PSI cap sensitivity: cap 3 -> 24.10 km/s over 19.7 yr; cap 2 -> 25.88 over 15.1 yr")
print("  (our derived GaAs cap_eff(0.42 AU) = 3.54; our 12-yr thermal figure sits between"
      " their cap-4 and cap-3 rows without extending the powered horizon)")

print("=" * 78)
print("STAGE 5 - PSI Appendix C mass-closure algebra, independent replay")
VE = 2800.0 * c.G0
ALPHA, KAPPA, FT, MFIX, ETA, TB = 60.0, 6.0 / 1000.0, 0.12, 9.0, 0.55, 4.0 * c.YEAR
for label, dv_dep, frad, dv_hels in (("LEO", 7.6e3, 1.25, (22.9e3, 24.0e3)),
                                     ("GTO", 4.24e3, 1.15, (22.9e3, 24.0e3))):
    for dv_hel in dv_hels:
        dv_tot = dv_dep + dv_hel
        zeta = 1.0 - math.exp(-dv_tot / VE)
        zd = 1.0 - math.exp(-dv_dep / VE)
        zh = (1.0 - zd) * (1.0 - math.exp(-dv_hel / VE))
        a0 = (1.54 * zd + 1.84 * zh) * VE / TB
        phi = zeta * (1.0 + FT) + a0 * VE / (2.0 * ETA) * (frad / ALPHA + KAPPA) / 1.0
        mw = MFIX / (1.0 - phi) if phi < 1.0 else float("inf")
        print(f"  {label} dv_hel {dv_hel/1e3:.1f}: a0 {a0:.2e}  phi {phi:.3f}  min closing wet"
              f" {mw:7.1f} kg")
print("  PSI: LEO boundary 113.3 kg @30.5 -> 145.6 kg @31.6; GTO boundary 59-68 kg"
      " (every GTO case >= 80 kg closes)")
# our engine flavor: minimal_dry_mass fixed point with their component set (LEO, 31.6 km/s)
wet = 120.0
res = None
for _ in range(60):
    P = 2.5e-4 * wet * VE / (2.0 * ETA)
    active = P * (1.25 / ALPHA + KAPPA)
    res = minimal_dry_mass(active, MFIX, 31.6e3, 2800.0, FT, 0.0)
    if res is None:
        break
    if abs(res["wet"] - wet) < 1e-6:
        break
    wet = res["wet"]
if res is None:
    print("  our minimal_dry_mass fixed point: does NOT close (rocket-equation wall)")
else:
    print(f"  our minimal_dry_mass fixed point (LEO 31.6): wet {res['wet']:.1f} kg,"
          f" prop {res['m_prop']:.1f} kg ({res['m_prop']/res['wet']*100:.0f}%)")

print("=" * 78)
print("STAGE 6 - out-of-plane cost & the corner minimum")
v73, t73 = geom(73000, shave=MISS)
ours_tilt_cost = v73 * abs(math.sin(math.radians(t73)))
print(f"  our |sin(beta)| pricing at the 73-kyr aim: {ours_tilt_cost:.0f} m/s")
print(f"  PSI planar bracket [22, 1020] m/s; MEASURED 3-D increment 578 m/s (0.57x ours)")
scale = 578.0 / ours_tilt_cost
best_s = None
for T in range(70000, 90001, 50):
    v, t = geom(T)
    dv = pumped_departure_dv(v, 0.0, 400.0) + scale * v * abs(math.sin(math.radians(t)))
    if best_s is None or dv < best_s[1]:
        best_s = (T, dv)
print(f"  pumped-budget argmin with tilt cost SCALED by {scale:.3f} (PSI-measured pricing):"
      f" T={best_s[0]:,} yr  (unscaled argmin: 79,250 yr; corner survives iff unchanged)")

print("=" * 78)
print("STAGE 7 - alternative targets from OUR web catalog states vs PSI Table 8")
LYMYR = c.LY / (1e6 * c.YEAR)  # ly/Myr in m/s
CAT = {
    "LSPM J2146+3813": ([15.075, -3.466, 17.002], [-164.1954, 47.0558, -217.9116]),
    "lam Ser": ([-21.212, -27.549, 17.365], [84.7453, 171.8526, -119.6165]),
}
PSI_T8 = {  # (arrival kyr, impulsive floor km/s, published perihelion pc, epoch kyr)
    "LSPM J2146+3813": (78.0, 9.30, 0.568, 82.5),
    "lam Ser": (151.6, 11.38, 2.30, 167.0),
}
for name, (p, v) in CAT.items():
    r = np.array(p) * c.LY
    w = np.array(v) * LYMYR
    dnow = np.linalg.norm(r)
    tol = 0.01 * dnow  # PSI: miss tolerance 1% of current distance
    tca = -float(np.dot(r, w)) / float(np.dot(w, w))
    sca = float(np.linalg.norm(np.cross(r, w))) / float(np.linalg.norm(w))
    bestf = None
    T = 20000.0
    while T <= 500000.0:
        Ts = T * c.YEAR
        V = r / Ts + w
        vmag2 = max(0.0, float(np.linalg.norm(V)) - tol / Ts)
        tilt = math.degrees(math.atan2(V[2], math.hypot(V[0], V[1])))
        f, _ = floor_from(vmag2, tilt)
        if bestf is None or f < bestf[1]:
            bestf = (T, f, vmag2)
        T *= 1.005
    pa, pf, pperi, pep = PSI_T8[name]
    print(f"  {name:<16s} ours: peri {sca/c.PC:.3f} pc @ {tca/c.YEAR/1e3:.1f} kyr;"
          f" floor {bestf[1]/1e3:5.2f} km/s @ {bestf[0]/1e3:5.1f} kyr (cruise {bestf[2]/1e3:.2f})")
    print(f"  {'':16s} PSI : peri {pperi:.3f} pc @ {pep:.1f} kyr; floor {pf:5.2f} km/s"
          f" @ {pa:5.1f} kyr")
print("=" * 78)
print("done")
