// Project Fermi -- shared mission physics (browser + Node).
// Ported from the validated Python engine (fermi_sim/). Loaded by index.html and
// cross-checked against Python in audit/calcs/audit_webjs.mjs. No third-party code.
(function (root) {
  "use strict";

  // ----- constants (SI) -----
  const AU = 1.495978707e11, LY = 9.4607304725808e15, YEAR = 3.15576e7, G0 = 9.80665;
  const MU_SUN = 1.32712440018e20, MU_EARTH = 3.986004418e14, R_EARTH = 6.371e6;
  const V_ESC_SUN = Math.sqrt(2 * MU_SUN / AU), V_EARTH = Math.sqrt(MU_SUN / AU);
  const R_SUN = 6.957e8, MU_JUP = 1.26687e17, R_JUP = 7.1492e7;
  // Alpha Centauri ecliptic state (m, m/s) from the fermi_sim engine.
  const R0 = [-1.5364679397919116e16, -2.6062563844058972e16, -2.7814865852216956e16];
  const VAC = [-9222.153827911658, 28889.554946491313, 11121.449350900906];
  const SPIRAL_MAX = 11.3; // naive continuous-spiral penalty (km/s), from numerical RK4

  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

  function requiredVinfVec(T) {
    return [(R0[0] + VAC[0] * T) / T, (R0[1] + VAC[1] * T) / T, (R0[2] + VAC[2] * T) / T];
  }
  function intercept(T) {
    const v = requiredVinfVec(T);
    const inPlane = Math.hypot(v[0], v[1]);
    return { vinf: Math.hypot(inPlane, v[2]), tiltDeg: Math.atan2(v[2], inPlane) * 180 / Math.PI };
  }
  function tangentialT() { return dot(R0, R0) / (-dot(R0, VAC)); }
  function eclipticCrossingT() { return -R0[2] / VAC[2]; }

  function vInfEarth(vinfSun, tiltDeg) {
    const vDep = Math.sqrt(vinfSun * vinfSun + V_ESC_SUN * V_ESC_SUN);
    const b = tiltDeg * Math.PI / 180;
    const e = Math.max(vDep * vDep + V_EARTH * V_EARTH - 2 * vDep * V_EARTH * Math.cos(b), 0);
    return { vInfE: Math.sqrt(e), vDep };
  }
  function impulsiveDv(vInfE, periAltKm, apoAltKm) {
    // Single Oberth kick at perigee from the (possibly elliptical) starting orbit.
    const rp = R_EARTH + periAltKm * 1e3;
    const ra = R_EARTH + Math.max(apoAltKm == null ? periAltKm : apoAltKm, periAltKm) * 1e3;
    const a = 0.5 * (rp + ra);
    const vp = Math.sqrt(MU_EARTH * (2 / rp - 1 / a));   // perigee speed of the starting orbit
    const vesc = Math.sqrt(2 * MU_EARTH / rp);
    return Math.sqrt(vInfE * vInfE + vesc * vesc) - vp;
  }
  // Derived naive low-thrust Earth-escape dv from LEO (Plan 02, Phase A). Closed-form fit of the
  // integrated constant-tangential spiral (fermi_sim spiral_escape_dv); see tools/fit_spiral.py.
  // dv = v_circ(alt) + C0 + C1*vInfE (m/s); matches the integration to 0.5 m/s over vInfE in [8,32] km/s.
  const SPIRAL_FIT_C0 = -1173.491, SPIRAL_FIT_C1 = 0.999997;
  // Starting-orbit generalisation: v_circ -> sqrt(mu/a) (orbit energy) + small eccentricity term.
  const SPIRAL_FIT_CE1 = 85.4, SPIRAL_FIT_CE2 = 284.8;
  function lowthrustDepartureDv(vinfSun, tiltDeg, periAltKm, apoAltKm) {
    const vInfE = vInfEarth(vinfSun, tiltDeg).vInfE;
    const rp = R_EARTH + periAltKm * 1e3;
    const ra = R_EARTH + Math.max(apoAltKm == null ? periAltKm : apoAltKm, periAltKm) * 1e3;
    const a = 0.5 * (rp + ra), e = (ra - rp) / (ra + rp);
    const va = Math.sqrt(MU_EARTH / a);
    return va + SPIRAL_FIT_C0 + SPIRAL_FIT_C1 * vInfE + SPIRAL_FIT_CE1 * e + SPIRAL_FIT_CE2 * e * e;
  }
  function timeToAc(vinf) {
    const a = dot(R0, R0), b = dot(R0, VAC), cc = dot(VAC, VAC) - vinf * vinf;
    const disc = b * b - a * cc;
    if (disc < 0) return null;
    const s = Math.sqrt(disc);
    const us = [(-b + s) / a, (-b - s) / a].filter((u) => u > 0);
    return us.length ? 1 / Math.max(...us) : null;
  }
  function jupiterGain(vrel) {
    const rp = R_JUP + 200000e3, sd = 1 / (1 + rp * vrel * vrel / MU_JUP);
    return 2 * vrel * sd;
  }
  function oberthBurnFor(rpRsun, vinf) {
    const r = rpRsun * R_SUN, ve = Math.sqrt(2 * MU_SUN / r);
    return Math.sqrt(vinf * vinf + ve * ve) - ve;
  }
  // Earth-escape spiral: revolutions & time to spiral from circular LEO to C3=0 at a=thrust/mass.
  // Analytic near-circular result N = mu/(8*pi*a*r_p^2), t = v_circ/a (matches integration ~0.2%).
  function earthEscapeRevs(thrustN, massKg, periAltKm) {
    const a = thrustN / Math.max(massKg, 1);
    if (a <= 0) return { revs: 0, tYr: 0 };
    const rp = R_EARTH + periAltKm * 1e3;
    return { revs: MU_EARTH / (8 * Math.PI * a * rp * rp), tYr: (Math.sqrt(MU_EARTH / rp) / a) / YEAR };
  }
  // Heliocentric spiral-out: revolutions around the Sun raising the orbit from r0 (~1 AU) to solar
  // escape. N = mu_sun/(8*pi*a*r0^2). The cruise after is a straight coast, so this is the total
  // turns around the Sun — typically < 1 (vs ~hundreds around Earth).
  function sunEscapeRevs(thrustN, massKg, r0Au = 1) {
    const a = thrustN / Math.max(massKg, 1);
    if (a <= 0) return { revs: 0 };
    const r0 = r0Au * AU;
    return { revs: MU_SUN / (8 * Math.PI * a * r0 * r0) };
  }
  const expv = (isp) => isp * G0;
  const propMass = (dry, dv, isp) => dry * (Math.exp(dv / expv(isp)) - 1);
  const elecEnergy = (mp, isp, eta) => 0.5 * mp * expv(isp) * expv(isp) / eta;

  // Solar array sizing: area = power / (solar flux * efficiency); flux ~ 1/r^2.
  const SOLAR_CONST = 1361.0; // W/m^2 at 1 AU
  const solarArrayArea = (powerW, eff, distAu = 1) => powerW / ((SOLAR_CONST / (distAu * distAu)) * eff);

  const API = {
    AU, LY, YEAR, G0, MU_SUN, MU_EARTH, R_EARTH, V_ESC_SUN, V_EARTH, R0, VAC, SPIRAL_MAX,
    SOLAR_CONST, SPIRAL_FIT_C0, SPIRAL_FIT_C1, SPIRAL_FIT_CE1, SPIRAL_FIT_CE2, requiredVinfVec, intercept, tangentialT,
    eclipticCrossingT, vInfEarth, impulsiveDv, lowthrustDepartureDv, timeToAc, jupiterGain,
    oberthBurnFor, earthEscapeRevs, sunEscapeRevs, expv, propMass, elecEnergy, solarArrayArea,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.FERMI = API;
})(typeof globalThis !== "undefined" ? globalThis : this);
