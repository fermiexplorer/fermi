"""Bake the curated star dataset for the page's 3D encounter map (web/stars.js).

Pipeline (all repo-root-relative; this script chdirs to the root so it can be run
from anywhere):
    tools/fetch_nearby.py      -> tmp/ro/nearby_stars.json   (SIMBAD TAP, 6-D kinematics)
    tools/fetch_rv_medians.py  -> tmp/ro/rv_medians.json     (all published RVs, per-star medians)
    tools/make_starmap_data.py -> web/stars.js               (the committed, shipped dump)
The two JSON inputs are SIMBAD query dumps (~22 MB) and are NOT committed — re-fetch
them with the scripts above; web/stars.js is the reviewed artifact of record.

Selection: (a) all naked-eye stars (V<=6) currently within 55 ly (map context),
(b) the 40 closest future approaches within 1.5 Myr, (c) the 'nice' approachers.
Data-quality: drop entries with |v| > 150 km/s (spurious SIMBAD RVs).
Positions in ecliptic ly; velocities in ly/Myr. Sun at origin.
"""
import json
import math
import os
import sys
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord, BarycentricMeanEcliptic

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)                       # data paths below are repo-root-relative
from fermi_sim.departure import lowthrust_departure_dv, sep_achievable_vinf
from fermi_sim.spacecraft import minimal_dry_mass

G0 = 9.80665
ISP = 3000.0
VE = ISP * G0

def prop_frac(dv_kms):
    """rocket-equation propellant fraction for the full budget at Isp 3000 s."""
    return 1.0 - math.exp(-dv_kms * 1e3 / VE)

L_SUN = 3.828e26   # W

def bolometric_correction(sp):
    """Fermi-grade BC by spectral class (mag). Late-M values are order-of-magnitude."""
    s = sp.strip().upper()
    if s.startswith("SD"):
        s = s[2:]
    elif s.startswith("D") and len(s) > 1 and s[1] in "MK":   # 'dM6' = dwarf M, not WD
        s = s[1:]
    elif s.startswith("D"):
        return -0.5                                            # white dwarf, rough
    for ch in s:
        if ch in "OBAFGKMLT":
            letter = ch
            i = s.index(ch)
            sub = 5.0
            for c2 in s[i + 1:i + 4]:
                if c2.isdigit():
                    sub = float(c2)
                    break
            break
    else:
        return None
    return {"O": -3.5, "B": -2.0, "A": -0.25, "F": -0.10, "G": -0.15,
            "K": -0.2 - 0.11 * sub, "M": -1.2 - 0.45 * sub,
            "L": -3.3, "T": -4.0}[letter]

def luminosity_w(V, d_ly, sp):
    """Bolometric luminosity in watts from V, distance and spectral type; None if V unknown."""
    if V is None:
        return None
    bc = bolometric_correction(sp)
    if bc is None:
        return None
    d_pc = d_ly * 9.4607e15 / 3.0857e16
    m_bol = V - 5.0 * math.log10(d_pc / 10.0) + bc
    lw = L_SUN * 10.0 ** ((4.74 - m_bol) / 2.5)
    return float(f"{lw:.2e}")                                  # 3 sig figs

# ---- the solar feasibility curve: achievable v_inf vs whole-vehicle alpha ----
# Same construction as run_analysis §7b, at the page defaults (Isp 3000, tank 2.5%,
# struct 10%, payload 1 kg, 2 kW, eff 0.5), sized for a representative ~20 km/s budget.
# Achievable v_inf is ~power-independent (alpha scales the probe, not the margin).
def _curve_point(active):
    r = minimal_dry_mass(active, 1.0, 20e3, ISP, 0.025, 0.10)
    if r is None:
        return None
    a = 2000.0 / r["dry_eff"]
    v = sep_achievable_vinf(2000.0, r["wet"], r["dry_eff"], ISP, 0.5, 1.0, 2.0)
    return (a, v / 1e3, active)

def alpha_curve():
    pts = [p for p in (_curve_point(m) for m in np.geomspace(1.2, 160.0, 24)) if p]
    pts.sort()
    # The curve is exactly v = 0 below the escape threshold, then rises continuously
    # from 0. Interpolating ACROSS that flat produced impossible sub-threshold min-α
    # values (audit finding, build 130): bisect the true first-escape α instead and
    # anchor the curve at (α_escape, 0), dropping all v = 0 grid points.
    zeros = [p for p in pts if p[1] <= 0.0]
    nonz = [p for p in pts if p[1] > 0.0]
    if zeros and nonz:
        act_hi, act_lo = zeros[-1][2], nonz[0][2]   # bigger active mass → lower α → v = 0
        for _ in range(24):
            mid = 0.5 * (act_hi + act_lo)
            p = _curve_point(mid)
            if p is None or p[1] > 0.0:
                act_lo = mid
            else:
                act_hi = mid
        edge = _curve_point(act_lo)
        pts = [(edge[0], 0.0, act_lo)] + nonz
    return [(a, v) for a, v, _ in sorted(pts)]     # ascending alpha; v monotone from 0

print("building solar-alpha feasibility curve (engine 1/r² gate, bisected escape edge)…")
ACURVE = alpha_curve()
print("  " + "  ".join(f"α{a:.0f}→{v:.1f}" for a, v in ACURVE))

def min_alpha(v_req_kms):
    """smallest alpha whose achievable v_inf >= required cruise (linear interp on the
    escape-anchored curve — never interpolates across the v = 0 flat); None if unreachable.
    The fixed 20 km/s sizing budget has a rigorous impulsive-from-1-AU ceiling of
    ~26.5 km/s; curve points above it are fixed-dt integration overshoot (audit finding,
    round 2), so cruises beyond the ceiling are UNREACHABLE at this sizing."""
    if v_req_kms > 26.5:
        return None
    prev = None
    for a, v in ACURVE:
        if v >= v_req_kms:
            if prev is None or prev[1] >= v_req_kms:
                return a
            a0, v0 = prev
            return a0 + (a - a0) * (v_req_kms - v0) / max(v - v0, 1e-9)
        prev = (a, v)
    return None

KMS_LYMYR = 3.3356
data = json.load(open("tmp/ro/nearby_stars.json"))["data"]
# ROBUST RVs (fetch_rv_medians.py): SIMBAD's adopted rvz takes the most recent paper, which
# let one bad 2023 source give ksi Boo −21.3 (17 measurements say +3, receding!) and c UMa
# −38.6 (16 say ~−14.6). Hierarchy: Gaia DR2/DR3 (quality A/B) → median of all measurements.
RVBEST = json.load(open("tmp/ro/rv_medians.json"))

names, sps, Vs, ra, dec, plx, pmra, pmdec, rv = [], [], [], [], [], [], [], [], []
n_fixed = 0
for r in data:
    if r[3] is None or r[3] <= 0:
        continue
    rv_val = r[6]
    b = RVBEST.get(r[0])
    if b is not None:
        if abs(b["rv"] - rv_val) > 3.0:
            n_fixed += 1
        rv_val = b["rv"]
    names.append(r[0]); ra.append(r[1]); dec.append(r[2]); plx.append(r[3])
    pmra.append(r[4]); pmdec.append(r[5]); rv.append(rv_val)
    sps.append((r[7] or "?").strip()); Vs.append(r[8] if r[8] is not None else None)
print(f"RV validation: {n_fixed} adopted values overridden by >3 km/s (Gaia/median hierarchy)")

# Stars whose SYSTEMIC radial velocity is disputed between credible catalogue solutions.
# The MAD test below cannot catch these: a spectroscopic binary's published RVs sample its
# ORBIT, so they can be numerous and mutually consistent (low MAD) while their median is a
# biased estimate of the centre-of-mass velocity. alf02 Lib is the type case: median of 8
# measurements gives -11.0 km/s (MAD 5.9) while the revised-Hipparcos systemic solution is
# -22.0 +/- 5.8 km/s — an 11 km/s (~2xMAD) disagreement that moves its intercept epoch ~2x
# (cross-checked in audit/AUDIT_COMPARISON.md §2b). Encounter claims built on either value
# are soft, so the row carries the ⚠ flag.
RV_DISPUTED = {"* alf02 Lib"}

def unverified(name):
    """1 = kinematics can't be corroborated: <2 published RVs, a non-Gaia RV whose
    measurement scatter exceeds MAD 10 km/s, or a disputed systemic RV (RV_DISPUTED —
    spectroscopic binaries where credible catalogue solutions disagree)."""
    if name in RV_DISPUTED:
        return 1
    b = RVBEST.get(name)
    if b is None or b.get("n", 0) < 2:
        return 1
    if b.get("src") != "gaia" and b.get("mad", 0) > 10.0:
        return 1
    return 0

c = SkyCoord(ra=np.array(ra)*u.deg, dec=np.array(dec)*u.deg,
             distance=(1000.0/np.array(plx))*u.pc,
             pm_ra_cosdec=np.array(pmra)*u.mas/u.yr, pm_dec=np.array(pmdec)*u.mas/u.yr,
             radial_velocity=np.array(rv)*u.km/u.s, frame="icrs")
e = c.transform_to(BarycentricMeanEcliptic())
pos = e.cartesian.xyz.to(u.lyr).value.T
vel = e.cartesian.differentials["s"].d_xyz.to(u.km/u.s).value.T * KMS_LYMYR

speed_kms = np.linalg.norm(vel, axis=1) / KMS_LYMYR
d_now = np.linalg.norm(pos, axis=1)
v2 = np.einsum("ij,ij->i", vel, vel)
t_star = -np.einsum("ij,ij->i", pos, vel) / v2
d_star = np.linalg.norm(pos + vel*t_star[:, None], axis=1)

# Spurious-RV guard: unverified stars above 150 km/s are dropped; VERIFIED fast movers
# (real halo passers, Kapteyn-class) are kept up to the galactic-escape ~600 km/s.
verified_arr = np.array([0 if unverified(n) else 1 for n in names], dtype=bool)
ok = (speed_kms <= 150.0) | (verified_arr & (speed_kms <= 600.0))
approach = ok & (t_star > 0) & (t_star <= 1.5)
sel = set()
# (a) naked-eye context within 55 ly
for i in np.where(ok & (d_now <= 55))[0]:
    if Vs[i] is not None and Vs[i] <= 6.0:
        sel.add(int(i))
# (b) 40 closest approaches
for i in np.where(approach)[0][np.argsort(d_star[np.where(approach)[0]])][:40]:
    sel.add(int(i))

def clean(n):
    return (n.replace("NAME ", "").replace("V* ", "").replace("* ", "")
             .replace("  ", " ").strip())

stars = []
for i in sorted(sel):
    stars.append({
        "n": clean(names[i]), "sp": sps[i][:8],
        "V": None if Vs[i] is None else round(float(Vs[i]), 1),
        "p": [round(float(x), 3) for x in pos[i]],
        "v": [round(float(x), 4) for x in vel[i]],
        "tc": round(float(t_star[i]), 4) if approach[i] else None,   # closest-approach Myr
        "dc": round(float(d_star[i]), 2) if approach[i] else None,   # closest distance ly
    })
print(f"selected {len(stars)} stars (from {len(names)}; {int((~ok).sum())} spurious-RV dropped)")

# ---- ecliptic-plane crossings within 20 ly, next 1 Myr, ranked by time ----
tz = -pos[:, 2] / vel[:, 2]
r_cross = np.linalg.norm(pos + vel * tz[:, None], axis=1)
csel = np.where((tz > 0) & (tz <= 1.0) & (r_cross <= 20.0) & ok)[0]
csel = csel[np.argsort(tz[csel])]

T_HI = 1.5  # Myr search ceiling for the tangential (min-cruise) intercept

def vneed(i, T):
    """required constant cruise speed (km/s) to intercept star i at arrival time T (Myr)."""
    vp = pos[i] / T + vel[i]
    return float(np.linalg.norm(vp)) / KMS_LYMYR

def tangential(i):
    """golden-section min of vneed over T -> (T_myr, v_kms); None-capped if at the ceiling."""
    g = (math.sqrt(5) - 1) / 2
    a, b = 0.002, T_HI
    for _ in range(90):
        c1, c2 = b - g * (b - a), a + g * (b - a)
        if vneed(i, c1) < vneed(i, c2):
            b = c2
        else:
            a = c1
    T = (a + b) / 2
    return T, vneed(i, T)

crossings = []
for i in csel:
    Ttan, vmin = tangential(int(i))
    capped = Ttan > 0.995 * T_HI                 # optimum beyond the search ceiling
    # Arrive AT the crossing: the target point is in the ecliptic plane, so the aim has
    # tilt = 0 (full Earth-velocity borrow, no plane change). Cruise speed there + the
    # ENGINE's low-thrust departure model give the whole spacecraft Δv budget — this one
    # number combines "low cruise" and "tangential/ecliptic alignment" (misalignment
    # inflates the cruise above the star's own minimum).
    Tc = float(tz[i])
    vcr = vneed(int(i), Tc)                      # km/s, cruise for arrival at t_cross
    if vcr > 200.0:                              # crossing era too soon/fast to catch — unreachable
        vcr = None
        dvb = None
    else:
        dvb = lowthrust_departure_dv(vcr * 1e3, 0.0) / 1e3   # km/s, engine model, tilt 0
    crossings.append({
        "n": clean(names[i]), "sp": sps[i][:9],
        "V": None if Vs[i] is None else round(float(Vs[i]), 1),
        "dnow": round(float(d_now[i]), 1),
        "tkyr": int(round(Tc * 1e3)),
        "dcross": round(float(r_cross[i]), 1),
        "ttan": None if capped else int(round(Ttan * 1e3)),   # tangential intercept, kyr
        "vcr": None if vcr is None else round(vcr, 1),        # cruise @ crossing, km/s
        "dvb": None if dvb is None else round(dvb, 1),        # engine Δv budget, km/s
        "pf": None if dvb is None else round(100 * prop_frac(dvb)),      # propellant %
        "amin": None if (vcr is None or min_alpha(vcr) is None) else round(min_alpha(vcr)),  # min solar α W/kg
        "lw": luminosity_w(None if Vs[i] is None else float(Vs[i]), float(d_now[i]), sps[i]),  # bolometric W
        "u": unverified(names[i]),                                        # kinematic-confidence flag (ksi-Boo lesson)
    })
print(f"crossings within 20 ly / 1 Myr: {len(crossings)} "
      f"({sum(1 for c in crossings if c['dvb'] is None)} unreachable-era)")

# ---- top-20 candidates: Δv budget (cruise+alignment) + brightness penalty ----
def score(c):
    if c["dvb"] is None or c.get("u"):           # unverified kinematics can't make the shortlist
        return 1e9
    V = c["V"] if c["V"] is not None else 15.0   # uncatalogued V => faint
    return c["dvb"] + 2.0 * max(0.0, V - 6.0)
top20 = sorted(crossings, key=score)[:20]
print("\nTOP 20 (score = Δv budget + 2·max(0, V−6)):")
print(f"{'#':>2s} {'star':26s} {'sp':9s} {'V':>5s} {'cross kyr':>9s} {'Δt kyr':>7s} "
      f"{'cruise':>7s} {'Δv bud':>7s} {'score':>6s}")
for k, c in enumerate(top20, 1):
    dt = "—" if c["ttan"] is None else f"{c['tkyr']-c['ttan']:+d}"
    vs = f"{c['V']:5.1f}" if c["V"] is not None else "    —"
    print(f"{k:2d} {c['n'][:26]:26s} {c['sp']:9s} {vs} {c['tkyr']:9d} {dt:>7s} "
          f"{c['vcr']:7.1f} {c['dvb']:7.1f} {score(c):6.1f}")

# ---- the 100 closest passes in the next 1 Myr (crossers AND non-crossers) ----
# Same evaluation for every star at its OWN tangential optimum with its TRUE aim tilt;
# ecliptic-crossing time shown when one exists in-window ("—" otherwise). Near-ecliptic
# non-crossers show up as small |tilt| — reachable without a plane crossing.
psel = np.where(ok & (t_star > 0) & (t_star <= 1.0))[0]
psel = psel[np.argsort(d_star[psel])][:100]
passes = []
for i in psel:
    i = int(i)
    T, v = tangential(i)
    capped = T > 0.995 * T_HI
    vp = pos[i] / T + vel[i]
    tilt = math.degrees(math.asin(vp[2] / np.linalg.norm(vp)))
    dvb = lowthrust_departure_dv(v * 1e3, tilt) / 1e3
    tcx = float(tz[i])
    has_cross = 0.0 < tcx <= 1.0
    # BEST arrival strategy: a well-aligned ecliptic crossing (tilt = 0) often beats the
    # tilt-blind tangential optimum (e.g. LSPM J2146+3813: 19.7 vs 33.0 km/s). Price the
    # star at whichever is cheaper; the tilt column shows the CHOSEN aim.
    if has_cross:
        vcx = vneed(int(i), tcx)
        if vcx <= 200.0:
            dvbx = lowthrust_departure_dv(vcx * 1e3, 0.0) / 1e3
            if dvbx < dvb:
                v, tilt, dvb = vcx, 0.0, dvbx
    am = min_alpha(v)
    passes.append({
        "n": clean(names[i]), "sp": sps[i][:9],
        "V": None if Vs[i] is None else round(float(Vs[i]), 1),
        "dnow": round(float(d_now[i]), 1),
        "dpass": round(float(d_star[i]), 2),                  # closest pass, ly
        "tpass": int(round(float(t_star[i]) * 1e3)),          # pass time, kyr
        "ttan": None if capped else int(round(T * 1e3)),
        "tcross": int(round(tcx * 1e3)) if has_cross else None,
        "tilt": round(tilt, 1),
        "vmin": round(v, 1),
        "dvb": round(dvb, 1),
        "pf": round(100 * prop_frac(dvb)),
        "amin": None if am is None else round(am),
        "lw": luminosity_w(None if Vs[i] is None else float(Vs[i]), float(d_now[i]), sps[i]),
        "u": unverified(names[i]),
    })
print(f"\nclosest-passes table: {len(passes)} stars (of {len(psel)} selected)")

# ---- LUMINOUS APPROACHERS: the biggest energy prizes coming our way inside 1 Myr ----
# (wide-volume sweep to ~315 ly + the region's giants to ~1000 ly: rank every star whose
#  closest approach lies ahead and meaningfully inside its current distance by LUMINOSITY)
lum_all = np.array([0.0 if (Vs[i] is None) else
                    (luminosity_w(float(Vs[i]), float(d_now[i]), sps[i]) or 0.0)
                    for i in range(len(names))])
appr = ok & (t_star > 0) & (t_star <= 1.0) & (d_star < 0.85 * d_now)
lsel = np.where(appr & (lum_all > 0))[0]
lsel = lsel[np.argsort(-lum_all[lsel])][:25]
lums = []
for i in lsel:
    i = int(i)
    T, v = tangential(i)
    capped = T > 0.995 * T_HI
    vp = pos[i] / T + vel[i]
    tilt = math.degrees(math.asin(vp[2] / np.linalg.norm(vp)))
    dvb = lowthrust_departure_dv(v * 1e3, tilt) / 1e3
    tcx = float(tz[i])
    if 0.0 < tcx <= 1.0:
        vcx = vneed(i, tcx)
        if vcx <= 200.0:
            dvbx = lowthrust_departure_dv(vcx * 1e3, 0.0) / 1e3
            if dvbx < dvb:
                v, tilt, dvb = vcx, 0.0, dvbx
    lums.append({
        "n": clean(names[i]), "sp": sps[i][:9],
        "V": round(float(Vs[i]), 1),
        "dnow": round(float(d_now[i]), 1),
        "dpass": round(float(d_star[i]), 2),
        "tpass": int(round(float(t_star[i]) * 1e3)),
        "tilt": round(tilt, 1), "vmin": round(v, 1), "dvb": round(dvb, 1),
        "pf": round(100 * prop_frac(dvb)),
        "amin": None if min_alpha(v) is None else round(min_alpha(v)),
        "lw": luminosity_w(float(Vs[i]), float(d_now[i]), sps[i]),
        "u": unverified(names[i]),
    })
print(f"\nLUMINOUS APPROACHERS (top {len(lums)} by luminosity, approaching within 1 Myr):")
for s in lums[:12]:
    print(f"  {s['n'][:24]:24s} {s['sp']:9s} V{s['V']:5.1f} L={s['lw']:.1e}W "
          f"now {s['dnow']:6.1f} ly -> {s['dpass']:6.2f} ly @ {s['tpass']:4d} kyr  "
          f"Δv {s['dvb']:5.1f}{' ⚠' if s['u'] else ''}")

# ---- non-crossers vs crossers: Δv budget at each star's OWN tangential optimum ----
# (answers "is it worth looking at stars that don't cross the ecliptic, like Altair?" —
#  they just pay the plane-change tilt penalty, which the engine models via v_inf,Earth)
print("\nHEADLINE CANDIDATES at their own tangential optimum (true aim tilt):")
print(f"{'star':16s} {'T_tan kyr':>9s} {'cruise':>7s} {'tilt deg':>8s} {'Δv budget':>9s} {'prop%':>6s} {'minα':>5s}")
for nm in ("alf Cen", "HD 168442", "ksi Boo", "c UMa", "lam Ser", "alf Aql", "tau Cet", "zet Her"):
    idx = [i for i in range(len(names)) if clean(names[i]) == nm or nm in clean(names[i])]
    idx = [i for i in idx if ok[i]]
    if not idx:
        print(f"{nm:16s} (not found)")
        continue
    i = min(idx, key=lambda j: d_now[j])
    T, v = tangential(i)
    vp = pos[i] / T + vel[i]
    tilt = math.degrees(math.asin(vp[2] / np.linalg.norm(vp)))
    dv = lowthrust_departure_dv(v * 1e3, tilt) / 1e3
    am = min_alpha(v)
    lw = luminosity_w(None if Vs[i] is None else float(Vs[i]), float(d_now[i]), sps[i])
    print(f"{clean(names[i])[:16]:16s} {T*1e3:9.0f} {v:7.1f} {tilt:8.1f} {dv:9.1f} "
          f"{100*prop_frac(dv):6.0f} {('—' if am is None else f'{am:.0f}'):>5s} "
          f"{('—' if lw is None else f'{lw:.1e}W'):>9s}")

# ---- Philip's three ksi Boo questions, with the CORRECTED kinematics ----
print("\nKSI BOO with validated RV (receding — Philip was right):")
for nm in ("* ksi Boo",):
    idx = [i for i in range(len(names)) if names[i] == nm]
    if idx:
        i = idx[0]
        print(f"  RV used: {rv[i]:+.2f} km/s   d_now {d_now[i]:.1f} ly   speed {speed_kms[i]:.1f} km/s")
        print(f"  closest pass: t* = {t_star[i]*1e3:+.0f} kyr (negative = PAST), d* = {d_star[i]:.1f} ly")
        tzz = tz[i]
        print(f"  ecliptic crossing: t = {tzz*1e3:+.0f} kyr, r@cross = {np.linalg.norm(pos[i]+vel[i]*tzz):.1f} ly")
        Tm, vm = tangential(i)
        print(f"  tangential intercept: T = {Tm*1e3:.0f} kyr (capped at 1500 = no useful future optimum), "
              f"min cruise = {vm:.1f} km/s")

hdr = ("// Nearby-star data for the encounter map + crossing table — generated by "
       "tools/make_starmap_data.py from SIMBAD\n// TAP (plx>=20 mas, 6-D "
       "kinematics), ecliptic frame via astropy, spurious RVs "
       "(|v|>150 km/s) removed. Positions ly, velocities\n// ly/Myr, Sun at origin. "
       "NEARBY_STARS: n=name, sp=type, V=mag, p=pos, v=vel, tc=closest-approach Myr,\n"
       "// dc=closest ly.  ECLIPTIC_CROSSINGS_20LY: all z=0 crossings within 20 ly in the "
       "next 1 Myr, time-ranked;\n// tkyr=crossing time, dcross=Sun distance at crossing, "
       "dnow=current distance.\n")
with open("web/stars.js", "w") as fh:
    fh.write(hdr + "const NEARBY_STARS = " + json.dumps(stars, separators=(",", ":")) + ";\n"
             + "const ECLIPTIC_CROSSINGS_20LY = "
             + json.dumps(crossings, separators=(",", ":")) + ";\n"
             + "const CLOSEST_PASSES_100 = "
             + json.dumps(passes, separators=(",", ":")) + ";\n"
             + "const LUMINOUS_APPROACHERS = "
             + json.dumps(lums, separators=(",", ":")) + ";\n")
print("wrote web/stars.js")
# sanity echoes
for s in stars:
    if s["dc"] is not None and s["dc"] < 6 and (s["V"] or 99) <= 6:
        print("  nice/close:", s["n"], s["sp"], s["V"], s["tc"], "Myr", s["dc"], "ly")
