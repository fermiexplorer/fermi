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
  // Perihelion-pumping validated design profile (mirror of fermi_sim.constants): campaigns
  // are flown at a0_eff = min(vehicle a0, PUMP_DESIGN_A0) and Isp PUMP_DESIGN_ISP — the
  // bang-bang policy is validated only in this corridor (non-monotonic in a0 AND Isp).
  const PUMP_DESIGN_A0 = 2.5e-4, PUMP_DESIGN_ISP = 2800;

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
  // Earth's sphere-of-influence radius (m): the orbit the spiral must reach to escape Earth =
  // the physical RADIUS of the escape disk. r_SOI = a·(mu_earth/mu_sun)^(2/5) ≈ 145 R_earth.
  function earthSoiRadius(rSunAu = 1) { return rSunAu * AU * Math.pow(MU_EARTH / MU_SUN, 0.4); }
  // Correction Δv (m/s) for an RMS LEO-injection pointing error σ: re-aim at parking speed, Δv = 2·v_circ·sin(σ/2).
  function injectionPointingDv(sigmaDeg, altKm = 590) {
    if (sigmaDeg <= 0) return 0;
    const vCirc = Math.sqrt(MU_EARTH / (R_EARTH + altKm * 1e3));
    return 2 * vCirc * Math.sin(sigmaDeg * Math.PI / 180 / 2);
  }
  // Cosine steering-loss factor (≥1) for an RMS thrust-pointing error σ during the spiral: Δv ÷ cos σ.
  function gncSteeringFactor(sigmaDeg) { return 1 / Math.cos(Math.max(0, Math.min(89, sigmaDeg)) * Math.PI / 180); }
  // CONSERVATIVE solar-electric feasibility: max heliocentric v∞ a SEP probe can reach from a 1-AU
  // circular orbit, with thrust faded as 1/r² (array power). Saturates → practical SEP falls below
  // the ~23.4 km/s cruise floor (the 1/r² power-fade analysis). RK4 in SI; cached by argument key.
  const _sepCache = {};
  function sepAchievableVinf(powerW, wetKg, dryPayKg, ispS, eff = 0.5, r0Au = 1, fadeExp = 2) {
    const ve = ispS * G0, mp = wetKg - dryPayKg;
    if (mp <= 0 || powerW <= 0 || ve <= 0) return 0;
    const key = [powerW, wetKg, dryPayKg, ispS, eff, r0Au, fadeExp].map(x => +(+x).toFixed(3)).join(',');
    if (_sepCache[key] !== undefined) return _sepCache[key];
    const mu = MU_SUN, r0 = r0Au * AU, F0 = 2 * eff * powerW / ve, dt = 5e4, TCAP = 400 * YEAR;
    let rx = r0, ry = 0, vx = 0, vy = Math.sqrt(mu / r0), m = wetKg, t = 0;
    const dr = (s, mass) => { const x = s[0], y = s[1], vxx = s[2], vyy = s[3];
      const r = Math.hypot(x, y) || 1, sp = Math.hypot(vxx, vyy) || 1, g = -mu / (r * r * r);
      const Fm = mass > dryPayKg ? F0 * (r0 / r) ** fadeExp : 0;     // solar fadeExp=2 (1/r²); nuclear=0 (constant)
      return [vxx, vyy, g * x + Fm * vxx / sp / mass, g * y + Fm * vyy / sp / mass]; };
    while (t < TCAP) {
      const r = Math.hypot(rx, ry);
      if (r > 80 * AU) break;
      const s = [rx, ry, vx, vy], k1 = dr(s, m);
      const s2 = s.map((v, i) => v + 0.5 * dt * k1[i]), k2 = dr(s2, m);
      const s3 = s.map((v, i) => v + 0.5 * dt * k2[i]), k3 = dr(s3, m);
      const s4 = s.map((v, i) => v + dt * k3[i]), k4 = dr(s4, m);
      rx += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]);
      ry += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]);
      vx += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]);
      vy += dt / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3]);
      if (m > dryPayKg) { const Fm = F0 * (r0 / Math.hypot(rx, ry)) ** fadeExp; m -= Fm / ve * dt; if (m < dryPayKg) m = dryPayKg; }
      else { const rr = Math.hypot(rx, ry), ee = 0.5 * (vx * vx + vy * vy) - mu / rr; if (ee < 0 || rr > 8 * AU) break; }
      t += dt;
    }
    const r = Math.hypot(rx, ry), E = 0.5 * (vx * vx + vy * vy) - mu / r;
    const out = E > 0 ? Math.sqrt(2 * E) : 0;
    _sepCache[key] = out;
    return out;
  }
  // PERIHELION PUMPING (mirror of fermi_sim.departure.perihelion_pumped_vinf): multi-revolution
  // escape from 1 AU circular. Retrograde arcs near apoapsis drop perihelion to rpMinAu (thermal
  // cap), then prograde arcs at perihelion — power capped at powerCap× the 1-AU rating — staircase
  // the energy to the target. Defeats the 1/r² outward-spiral saturation at today's α.
  // Returns { vinf (m/s), dv (m/s), years, revs, reaches }. Cached by argument key.
  const _pumpCache = {};
  function perihelionPumpedVinf(a0, vInfTarget, ispS = 2800, rpMinAu = 0.42, powerCap = 4, maxYr = 60) {
    const key = [a0, vInfTarget, ispS, rpMinAu, powerCap, maxYr].map(x => "" + x).join(",");
    if (_pumpCache[key] !== undefined) return _pumpCache[key];
    const mu = MU_SUN, ve = ispS * G0, targetE = 0.5 * vInfTarget * vInfTarget;
    let x = AU, y = 0, vx = 0, vy = Math.sqrt(mu / AU);
    let m = 1, t = 0, dv = 0, angPrev = 0, revs = 0, pumpedDown = false;
    const maxT = maxYr * YEAR;
    const accelMag = (r) => a0 * Math.min((AU / r) ** 2, powerCap) / m;
    let out = null;
    while (t < maxT) {
      const r = Math.hypot(x, y);
      const v2 = vx * vx + vy * vy;
      const E = 0.5 * v2 - mu / r;
      if (E >= targetE) { out = { vinf: Math.sqrt(2 * E), dv, years: t / YEAR, revs, reaches: true }; break; }
      const h = x * vy - y * vx;
      const ecc = Math.sqrt(Math.max(0, 1 + 2 * E * h * h / (mu * mu)));
      const pSl = h * h / mu;
      const rp = pSl / (1 + ecc);
      const rdotSign = (x * vx + y * vy) >= 0 ? 1 : -1;
      let nu = 0;
      if (ecc > 1e-6) {
        const cnu = Math.max(-1, Math.min(1, (pSl / r - 1) / ecc));
        nu = rdotSign * Math.acos(cnu);                    // (-pi, pi], 0 = periapsis
      }
      if (rp <= rpMinAu * AU) pumpedDown = true;           // one-way latch (else the policy dithers)
      let thrustDir;
      if (!pumpedDown) {
        if (ecc < 0.05) thrustDir = x > 0 ? -1 : 0;        // inertial-side bootstrap from circular
        else thrustDir = Math.abs(Math.abs(nu) - Math.PI) < Math.PI / 3 ? -1 : 0; // pump-down at apoapsis
      } else if (E < -3.0e7) {
        // escape-guarded staircase: prograde near periapsis only while comfortably bound
        thrustDir = Math.abs(nu) < 70 * Math.PI / 180 ? 1 : 0;
      } else {
        thrustDir = 1;                                     // near-parabolic finisher: burn continuously
      }
      const vmag = Math.sqrt(v2) || 1;
      const amag = thrustDir ? accelMag(r) : 0;
      const period = 2 * Math.PI * Math.sqrt(Math.max(r, 0.1 * AU) ** 3 / mu);
      const dt = Math.min(Math.max(600, 0.002 * period), 5 * 86400);
      const dr2 = (s) => { const X = s[0], Y = s[1], VX = s[2], VY = s[3];
        const rr = Math.hypot(X, Y), vv = Math.hypot(VX, VY) || 1;
        const am = thrustDir ? accelMag(rr) * thrustDir : 0;
        const g = -mu / (rr * rr * rr);
        return [VX, VY, g * X + am * VX / vv, g * Y + am * VY / vv]; };
      const s = [x, y, vx, vy], k1 = dr2(s);
      const s2 = s.map((v, i) => v + 0.5 * dt * k1[i]), k2 = dr2(s2);
      const s3 = s.map((v, i) => v + 0.5 * dt * k2[i]), k3 = dr2(s3);
      const s4 = s.map((v, i) => v + dt * k3[i]), k4 = dr2(s4);
      x += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]);
      y += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]);
      vx += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]);
      vy += dt / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3]);
      if (thrustDir) {
        dv += amag * dt;
        m = Math.max(0.05, m - (a0 * Math.min((AU / r) ** 2, powerCap) / ve) * dt);
      }
      const ang = Math.atan2(y, x);
      let dAng = ang - angPrev;
      if (dAng > Math.PI) dAng -= 2 * Math.PI;
      else if (dAng < -Math.PI) dAng += 2 * Math.PI;
      revs += Math.abs(dAng) / (2 * Math.PI);
      angPrev = ang;
      t += dt;
    }
    if (!out) {
      const r = Math.hypot(x, y), E = 0.5 * (vx * vx + vy * vy) - mu / r;
      out = { vinf: E > 0 ? Math.sqrt(2 * E) : 0, dv, years: t / YEAR, revs, reaches: false };
    }
    _pumpCache[key] = out;
    return out;
  }

  // PERIHELION SYNCHROTRON — "the lasso idea" (mirror of fermi_sim synchrotron_escape).
  // An externally powered station at perihelion rp applies one impulsive prograde kick per
  // pass; the probe is passive (no onboard propellant/power) and flies exact Kepler
  // ellipses between kicks. Corrections enforced: periods sum (and balloon near escape),
  // and escape TERMINATES recirculation — a kick that clears escape below the target
  // perihelion speed strands the probe ("escapedBelow").
  function synchrotronEscape(rpRsun, dvPass, vInfTarget, maxPasses = 10000) {
    const rp = rpRsun * R_SUN;
    const vEsc = Math.sqrt(2 * MU_SUN / rp);
    const vTarget = Math.sqrt(vInfTarget * vInfTarget + vEsc * vEsc);
    const dvFinalMin = vTarget - vEsc;
    let v = Math.sqrt(MU_SUN / rp);                // circular start at the station
    let passes = 0, t = 0, eStation = 0, maxPeriod = 0, escapedBelow = false, leftAtTarget = false;
    while (passes < maxPasses) {
      const v2 = v + dvPass;
      eStation += 0.5 * (v2 * v2 - v * v);
      passes += 1;
      v = v2;
      if (v >= vTarget) { leftAtTarget = true; break; } // leaves at ≥ target v∞ → feasible
      if (v >= vEsc) { escapedBelow = true; break; } // hyperbolic but slow → gone forever
      const eps = 0.5 * v * v - MU_SUN / rp;
      const a = -MU_SUN / (2 * eps);
      const period = 2 * Math.PI * Math.sqrt(a ** 3 / MU_SUN);
      t += period;
      maxPeriod = Math.max(maxPeriod, period);
    }
    const vInfFinal = Math.sqrt(Math.max(v * v - vEsc * vEsc, 0));
    return { passes, timeYr: t / YEAR, maxPeriodYr: maxPeriod / YEAR,
      vPeriFinal: v, vInfFinal, vEsc, vTarget, dvFinalMin, energySpec: eStation,
      rendezvousVel: (Math.SQRT2 - 1) * Math.sqrt(MU_SUN / rp),   // worst case: near-escape pass
      escapedBelow, reached: leftAtTarget && !escapedBelow };
  }

  // First-order total departure Δv for the pumped architecture (mirror of fermi_sim
  // pumped_departure_dv): Earth escape to C3≈0 at the orbit-energy speed √(μ⊕/a) + the
  // heliocentric pumping campaign at v∞ + v∞·|sin β| (plane change — the campaign is
  // integrated in-plane, so the out-of-plane aim is charged separately) + tax (calibrated
  // against perihelionPumpedVinf: Δv − v∞ ≈ 2.0 km/s at the a₀ = 2.5e-4 design corridor;
  // single-point calibration — misprices grow away from it). No Earth-velocity borrow.
  function pumpedDepartureDv(vinf, tiltDeg, periAltKm, apoAltKm, pumpTax = 2000) {
    const rp = R_EARTH + periAltKm * 1e3;
    const ra = R_EARTH + Math.max(apoAltKm == null ? periAltKm : apoAltKm, periAltKm) * 1e3;
    const plane = vinf * Math.abs(Math.sin(tiltDeg * Math.PI / 180));
    return Math.sqrt(MU_EARTH / (0.5 * (rp + ra))) + vinf + plane + pumpTax;
  }

  const expv = (isp) => isp * G0;
  const propMass = (dry, dv, isp) => dry * (Math.exp(dv / expv(isp)) - 1);
  const elecEnergy = (mp, isp, eta) => 0.5 * mp * expv(isp) * expv(isp) / eta;

  // DERIVED minimal dry mass (mirror of fermi_sim.spacecraft.minimal_dry_mass). The dry mass is the
  // minimum that must be there: active(power source + engine) + tank + structure (+payload in dry_eff),
  // with structure = ks·(active + (propCoef+1)·m_p) and m_p = dry_eff·(MR−1). propCoef = dry mass added
  // per kg of propellant (tank fraction, plus fuel-cell reactant on the web). Denominator ≤0 ⇒ diverges.
  function minimalDryMass(activeKg, payloadKg, dv, isp, propCoef, structFrac) {
    const K = Math.exp(dv / expv(isp)) - 1, ks = structFrac, gp = propCoef;
    const D = 1 - K * (gp + ks * (gp + 1));
    if (D <= 0) return { converges: false, dryEff: Infinity, mProp: Infinity, structure: Infinity, wet: Infinity };
    const dryEff = (activeKg * (1 + ks) + payloadKg) / D, mProp = dryEff * K;
    const structure = ks * (activeKg + (gp + 1) * mProp);
    return { converges: true, dryEff, mProp, structure, wet: dryEff + mProp };
  }

  // Solar array sizing: area = power / (solar flux * efficiency); flux ~ 1/r^2.
  const SOLAR_CONST = 1361.0; // W/m^2 at 1 AU
  const solarArrayArea = (powerW, eff, distAu = 1) => powerW / ((SOLAR_CONST / (distAu * distAu)) * eff);

  const API = {
    AU, LY, YEAR, G0, MU_SUN, MU_EARTH, R_EARTH, V_ESC_SUN, V_EARTH, R0, VAC, SPIRAL_MAX,
    PUMP_DESIGN_A0, PUMP_DESIGN_ISP,
    SOLAR_CONST, SPIRAL_FIT_C0, SPIRAL_FIT_C1, SPIRAL_FIT_CE1, SPIRAL_FIT_CE2, requiredVinfVec, intercept, tangentialT,
    eclipticCrossingT, vInfEarth, impulsiveDv, lowthrustDepartureDv, timeToAc, jupiterGain,
    oberthBurnFor, earthEscapeRevs, sunEscapeRevs, earthSoiRadius, injectionPointingDv, gncSteeringFactor, sepAchievableVinf, perihelionPumpedVinf, pumpedDepartureDv, synchrotronEscape, expv, propMass, elecEnergy, solarArrayArea, minimalDryMass,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.FERMI = API;
})(typeof globalThis !== "undefined" ? globalThis : this);
