// Project Fermi -- shared mission physics (browser + Node).
// Ported from the validated Python engine (fermi_sim/). Loaded by index.html and
// cross-checked against Python in audit/calcs/audit_webjs.mjs. No third-party code.
//
// INPUT-VALIDATION CONTRACT (mirror of the note in fermi_sim/departure.py):
// unlike the Python engine, this port NEVER throws on bad numeric input inside the
// render path -- an exception would kill the page's compute/render loop. Heavy
// functions (sepAchievableVinf, perihelionPumpedVinf, minimalDryMass,
// synchrotronEscape) return diverged/zero SENTINELS on non-finite input; light
// helpers (requiredVinfVec, eclipticCrossingT, leo-speed forms) are deliberately
// unguarded because the UI's slider bounds make bad input unreachable (arrival
// slider floor 58,000 yr; eclipticCrossingT has NO inputs -- it reads the baked
// ephemeris constant VAC[2], nonzero by construction). The one throwing exception:
// pumpedDepartureDv's calibration-corridor guard, unreachable from the page (the
// AC aim's v-inf floor is 23.27 km/s) and intended to fail loud for library callers.
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
  // SIGNED time (mirror of fermi_sim ecliptic_crossing_time): negative = the crossing is in the
  // past. For AC's catalogued state (below the ecliptic, moving up) it is in the future.
  function eclipticCrossingT() { return -R0[2] / VAC[2]; }

  function vInfEarth(vinfSun, tiltDeg) {
    const vDep = Math.sqrt(vinfSun * vinfSun + V_ESC_SUN * V_ESC_SUN);
    const b = tiltDeg * Math.PI / 180;
    // law of cosines in the cancellation-free half-angle form (mirror of fermi_sim):
    // v² + V² − 2vV·cosβ == (v − V)² + 4vV·sin²(β/2)
    const s = Math.sin(0.5 * b), d = vDep - V_EARTH;
    return { vInfE: Math.sqrt(d * d + 4 * vDep * V_EARTH * s * s), vDep };
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
    // cancellation-free identity: sqrt(v²+vₑ²) − vₑ == v²/(sqrt(v²+vₑ²) + vₑ) (mirror of fermi_sim)
    const r = rpRsun * R_SUN, ve = Math.sqrt(2 * MU_SUN / r);
    return vinf * vinf / (Math.sqrt(vinf * vinf + ve * ve) + ve);
  }
  // Earth-escape spiral: revolutions & time to spiral from circular LEO to C3=0 at a=thrust/mass.
  // Analytic near-circular result N = mu/(8*pi*a*r_p^2), t = v_circ/a (matches integration ~0.2%).
  // C3=0 escape costs ~0.93·v_circ under constant-tangential thrust (not the r→∞ Edelbaum
  // asymptote v_circ, which overstates the escape TIME by ~7.6 %); mildly accel-dependent, 0.93
  // holds the SEP band to ≲1 %. Mirror of fermi_sim.departure._C3_ESCAPE_FRAC.
  const C3_ESCAPE_FRAC = 0.93;
  function earthEscapeRevs(thrustN, massKg, periAltKm = 590) {
    const a = thrustN / Math.max(massKg, 1);
    if (a <= 0) return { revs: 0, tYr: 0 };
    const rp = R_EARTH + periAltKm * 1e3;
    return { revs: MU_EARTH / (8 * Math.PI * a * rp * rp), tYr: (C3_ESCAPE_FRAC * Math.sqrt(MU_EARTH / rp) / a) / YEAR };
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
  // the ~23.3 km/s cruise floor (the 1/r² power-fade analysis). RK4 in SI with MASS as the fifth
  // state component and an adaptive step (mirror of fermi_sim, issue #2); cached by argument key.
  // FIFO cap on the memo tables so a long slider-drag session can't grow them without bound (each
  // entry is tiny, but the key space is effectively unbounded); evict the oldest key past the cap.
  const CACHE_CAP = 4096;
  const _sepCache = {}, _sepOrder = [];
  function sepAchievableVinf(powerW, wetKg, dryPayKg, ispS, eff = 0.5, r0Au = 1, fadeExp = 2) {
    if (![powerW, wetKg, dryPayKg, ispS, eff, r0Au, fadeExp].every(Number.isFinite)) return 0;
    const ve = ispS * G0, mp = wetKg - dryPayKg;
    if (mp <= 0 || powerW <= 0 || ve <= 0) return 0;
    const key = [powerW, wetKg, dryPayKg, ispS, eff, r0Au, fadeExp].map(x => +(+x).toFixed(3)).join(',');
    if (_sepCache[key] !== undefined) return _sepCache[key];
    const mu = MU_SUN, r0 = r0Au * AU, F0 = 2 * eff * powerW / ve, TCAP = 400 * YEAR;
    let rx = r0, ry = 0, vx = 0, vy = Math.sqrt(mu / r0), m = wetKg, t = 0;
    const dr = (s) => { const x = s[0], y = s[1], vxx = s[2], vyy = s[3], mass = s[4];
      const r = Math.hypot(x, y) || 1, sp = Math.hypot(vxx, vyy) || 1, g = -mu / (r * r * r);
      const Fm = mass > dryPayKg ? F0 * (r0 / r) ** fadeExp : 0;     // solar fadeExp=2 (1/r²); nuclear=0 (constant)
      return [vxx, vyy, g * x + Fm * vxx / sp / mass, g * y + Fm * vyy / sp / mass, -Fm / ve]; };
    while (t < TCAP) {
      const r = Math.hypot(rx, ry);
      if (r > 80 * AU) break;
      // adaptive step: fraction of the r-based Kepler period (mirror of fermi_sim — NOT
      // the osculating-a period, which diverges near escape), floored 600 s, capped 5 days
      const period = 2 * Math.PI * Math.sqrt(Math.max(r, 0.1 * r0) ** 3 / mu);
      const dt = Math.min(Math.max(600, 0.002 * period), 5 * 86400);
      const s = [rx, ry, vx, vy, m], k1 = dr(s);
      const s2 = s.map((v, i) => v + 0.5 * dt * k1[i]), k2 = dr(s2);
      const s3 = s.map((v, i) => v + 0.5 * dt * k2[i]), k3 = dr(s3);
      const s4 = s.map((v, i) => v + dt * k3[i]), k4 = dr(s4);
      rx += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]);
      ry += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]);
      vx += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]);
      vy += dt / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3]);
      m += dt / 6 * (k1[4] + 2 * k2[4] + 2 * k3[4] + k4[4]);
      if (m <= dryPayKg) {                     // propellant spent — clamp, decide outcome, stop
        m = dryPayKg;
        const rr = Math.hypot(rx, ry), ee = 0.5 * (vx * vx + vy * vy) - mu / rr;
        if (ee < 0 || rr > 8 * AU) break;
      }
      t += dt;
    }
    const r = Math.hypot(rx, ry), E = 0.5 * (vx * vx + vy * vy) - mu / r;
    const out = E > 0 ? Math.sqrt(2 * E) : 0;
    _sepCache[key] = out;
    if (_sepOrder.push(key) > CACHE_CAP) delete _sepCache[_sepOrder.shift()];
    return out;
  }
  // PERIHELION PUMPING (mirror of fermi_sim.departure.perihelion_pumped_vinf): multi-revolution
  // escape from 1 AU circular. Retrograde arcs near apoapsis drop perihelion to rpMinAu (thermal
  // cap), then prograde arcs at perihelion — power capped at powerCap× the 1-AU rating — staircase
  // the energy to the target. Defeats the 1/r² outward-spiral saturation at today's α.
  // Returns { vinf (m/s), dv (m/s), years, revs, reaches }. Cached by argument key.
  const _pumpCache = {}, _pumpOrder = [];
  function perihelionPumpedVinf(a0, vInfTarget, ispS = 2800, rpMinAu = 0.42, powerCap = 4, maxYr = 60) {
    if (![a0, vInfTarget, ispS, rpMinAu, powerCap, maxYr].every(Number.isFinite)
        || a0 <= 0 || vInfTarget <= 0 || ispS <= 0)
      return { vinf: 0, dv: 0, years: 0, revs: 0, reaches: false };
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
    if (_pumpOrder.push(key) > CACHE_CAP) delete _pumpCache[_pumpOrder.shift()];
    return out;
  }

  // THERMAL DERATING (mirror of fermi_sim/thermal.py, issue #5): the perihelion power
  // multiple DERIVED from the array's own energy balance instead of the assumed 4× step.
  // Flat panel, sun-normal, two-sided emission, extracted electricity removed from the
  // heat load (self-consistent): (α−η(T))·S(r) = (εf+εb)·σ·T⁴, η(T) linear in T floored
  // at 0; cap_eff(r) = (1/r²)·η(T(r))/η(T_1AU). GaAs defaults; cap_eff(0.42 AU) = 3.54.
  // The fixed-point solve, the 1024-point log-radius table and the interpolation mirror
  // the Python construction operation-for-operation so the engines stay in parity.
  const TH_S0 = 1361.0, TH_SIGMA = 5.670374419e-8, TH_ITERS = 40;
  const TH = { alphaS: 0.92, epsFront: 0.85, epsBack: 0.85, etaRef: 0.30, beta: 0.002, tRef: 301.15 };
  function cellTemperature(rAu) {
    const s = TH_S0 / (rAu * rAu), eps = TH.epsFront + TH.epsBack;
    let t = 300.0;
    for (let i = 0; i < TH_ITERS; i++) {
      const eta = Math.max(0, TH.etaRef * (1 - TH.beta * (t - TH.tRef)));
      t = Math.pow((TH.alphaS - eta) * s / (eps * TH_SIGMA), 0.25);
    }
    return t;
  }
  const _thEta = (t) => Math.max(0, TH.etaRef * (1 - TH.beta * (t - TH.tRef)));
  function _capEffExact(rAu) {
    const eta1 = _thEta(cellTemperature(1.0));
    return (1 / (rAu * rAu)) * (_thEta(cellTemperature(rAu)) / eta1);
  }
  const TH_RMIN = 0.05, TH_RMAX = 40.0, TH_N = 1024;
  let _thCaps = null;
  function capEff(rAu) {
    if (_thCaps == null) {
      const lo = Math.log(TH_RMIN), hi = Math.log(TH_RMAX);
      _thCaps = new Array(TH_N);
      for (let i = 0; i < TH_N; i++)
        _thCaps[i] = _capEffExact(Math.exp(lo + (hi - lo) * i / (TH_N - 1)));
    }
    const lo = Math.log(TH_RMIN), hi = Math.log(TH_RMAX);
    const x = (Math.log(Math.min(Math.max(rAu, TH_RMIN), TH_RMAX)) - lo) * (TH_N - 1) / (hi - lo);
    const i = Math.min(Math.floor(x), TH_N - 2), f = x - i;
    return _thCaps[i] + f * (_thCaps[i + 1] - _thCaps[i]);
  }

  // SCHEDULE-PARAMETERIZED campaign integrator (mirror of
  // fermi_sim.pump_schedule.scheduled_pumped_vinf): the same pumping physics under an
  // explicit 4-parameter switching schedule with BISECTION-located switch events, 5-state
  // mass-coupled RK4, and the selected power model ("thermal" — the shipped default — or
  // "cap"). This is the calculator's feasibility GATE and flown campaign since issue #5
  // (the bang-bang+cap integrator above stays as the crude cross-check / parity anchor).
  // Schedule fields: thRetro/thPro (deg, arc half-widths), eGuard (J/kg), rpLatch (AU).
  const SCHEDULE_ANCHORED_THERMAL = {
    thRetro: 23.095223778657733, thPro: 84.43328139555737,
    eGuard: -25134228.462172244, rpLatch: 0.42 };
  function _schDecide(x, y, vx, vy, latched, sch) {
    const r = Math.hypot(x, y), v2 = vx * vx + vy * vy;
    const E = 0.5 * v2 - MU_SUN / r, h = x * vy - y * vx;
    const ecc = Math.sqrt(Math.max(0, 1 + 2 * E * h * h / (MU_SUN * MU_SUN)));
    const pSl = h * h / MU_SUN;
    const rp = (ecc < 1 || pSl > 0) ? pSl / (1 + ecc) : 0;
    const rd = (x * vx + y * vy) >= 0 ? 1 : -1;
    let nu = 0;
    if (ecc > 1e-6) nu = rd * Math.acos(Math.max(-1, Math.min(1, (pSl / r - 1) / ecc)));
    if (!latched) {
      if (ecc < 0.05) return [x > 0 ? -1 : 0, rp];
      return [Math.abs(Math.abs(nu) - Math.PI) < sch.thRetro * Math.PI / 180 ? -1 : 0, rp];
    }
    if (E < sch.eGuard) return [Math.abs(nu) < sch.thPro * Math.PI / 180 ? 1 : 0, rp];
    return [1, rp];
  }
  const _schCache = {}, _schOrder = [];
  function scheduledPumpedVinf(a0, vInfTarget, sch = SCHEDULE_ANCHORED_THERMAL,
                               ispS = 2800, powerCap = 4, maxYr = 60, powerModel = "thermal") {
    if (![a0, vInfTarget, ispS, powerCap, maxYr].every(Number.isFinite)
        || a0 <= 0 || vInfTarget <= 0 || ispS <= 0)
      return { vinf: 0, dv: 0, years: 0, revs: 0, reaches: false };
    const key = [a0, vInfTarget, sch.thRetro, sch.thPro, sch.eGuard, sch.rpLatch,
                 ispS, powerCap, maxYr, powerModel].map(x => "" + x).join(",");
    if (_schCache[key] !== undefined) return _schCache[key];
    const mu = MU_SUN, ve = ispS * G0, targetE = 0.5 * vInfTarget * vInfTarget;
    const pf = powerModel === "thermal" ? (rM) => capEff(rM / AU)
                                        : (rM) => Math.min((AU / rM) ** 2, powerCap);
    let x = AU, y = 0, vx = 0, vy = Math.sqrt(mu / AU), m = 1;
    let t = 0, dv = 0, revs = 0, angPrev = 0, latched = false;
    const maxT = maxYr * YEAR;
    const step = (s0, dt, d) => {
      const dr = (s) => { const [X, Y, VX, VY, M] = s;
        const rr = Math.hypot(X, Y), vv = Math.hypot(VX, VY) || 1;
        const am = d ? a0 * pf(rr) / Math.max(M, 0.05) * d : 0;
        const md = d ? -(a0 * pf(rr)) / ve : 0;
        const g = -mu / (rr * rr * rr);
        return [VX, VY, g * X + am * VX / vv, g * Y + am * VY / vv, md]; };
      const k1 = dr(s0);
      const k2 = dr(s0.map((v, i) => v + 0.5 * dt * k1[i]));
      const k3 = dr(s0.map((v, i) => v + 0.5 * dt * k2[i]));
      const k4 = dr(s0.map((v, i) => v + dt * k3[i]));
      const o = s0.map((v, i) => v + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]));
      o[4] = Math.max(o[4], 0.05);
      if (d) {
        const rr = Math.hypot(s0[0], s0[1]);
        return [o, (a0 * pf(rr) / Math.max(s0[4], 0.05)) * dt];
      }
      return [o, 0];
    };
    let out = null;
    while (t < maxT) {
      const r = Math.hypot(x, y);
      const E = 0.5 * (vx * vx + vy * vy) - mu / r;
      if (E >= targetE) { out = { vinf: Math.sqrt(2 * E), dv, years: t / YEAR, revs, reaches: true }; break; }
      let [d0, rp0] = _schDecide(x, y, vx, vy, latched, sch);
      if (!latched && rp0 <= sch.rpLatch * AU) {
        latched = true;
        [d0, rp0] = _schDecide(x, y, vx, vy, latched, sch);
      }
      const period = 2 * Math.PI * Math.sqrt(Math.max(r, 0.1 * AU) ** 3 / mu);
      let dt = Math.min(Math.max(600, 0.002 * period), 5 * 86400);
      const s0 = [x, y, vx, vy, m];
      let [s1, dv1] = step(s0, dt, d0);
      const [d1, rp1] = _schDecide(s1[0], s1[1], s1[2], s1[3], latched, sch);
      const crossedLatch = !latched && rp1 <= sch.rpLatch * AU;
      if (d1 !== d0 || crossedLatch) {
        // a switch boundary lies inside this step — bisect to it (~1e-3 dt), take the
        // sub-step under the OLD mode, and let the next loop iteration re-decide there
        let lo = 0, hi = dt;
        for (let i = 0; i < 10; i++) {
          const mid = 0.5 * (lo + hi);
          const [sm] = step(s0, mid, d0);
          const [dm, rpm] = _schDecide(sm[0], sm[1], sm[2], sm[3], latched, sch);
          if (dm !== d0 || (!latched && rpm <= sch.rpLatch * AU)) hi = mid;
          else lo = mid;
        }
        const sub = Math.max(hi, 1e-6 * dt);
        [s1, dv1] = step(s0, sub, d0);
        dt = sub;
      }
      [x, y, vx, vy, m] = s1;
      dv += dv1;
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
    _schCache[key] = out;
    if (_schOrder.push(key) > CACHE_CAP) delete _schCache[_schOrder.shift()];
    return out;
  }

  // PERIHELION SYNCHROTRON — "the lasso idea" (mirror of fermi_sim synchrotron_escape).
  // An externally powered station at perihelion rp applies one impulsive prograde kick per
  // pass; the probe is passive (no onboard propellant/power) and flies exact Kepler
  // ellipses between kicks. Corrections enforced: periods sum (and balloon near escape),
  // and escape TERMINATES recirculation — a kick that clears escape below the target
  // perihelion speed strands the probe ("escapedBelow").
  function synchrotronEscape(rpRsun, dvPass, vInfTarget, maxPasses = 10000) {
    // hardening: clamp the pass budget so a huge/hostile maxPasses can't spin the tab, and reject
    // non-physical inputs (dvPass<=0 never builds speed) with a fully-formed zero sentinel.
    maxPasses = Number.isFinite(maxPasses) ? Math.min(Math.max(1, Math.floor(maxPasses)), 1e6) : 10000;
    if (!(rpRsun > 0) || !(dvPass > 0) || !Number.isFinite(vInfTarget))
      return { passes: 0, timeYr: 0, maxPeriodYr: 0, vPeriFinal: 0, vInfFinal: 0, vEsc: 0, vTarget: 0,
        dvFinalMin: 0, energySpec: 0, rendezvousVel: 0, escapedBelow: false, reached: false };
    const rp = rpRsun * R_SUN;
    const vEsc = Math.sqrt(2 * MU_SUN / rp);
    const vTarget = Math.sqrt(vInfTarget * vInfTarget + vEsc * vEsc);
    const dvFinalMin = vInfTarget * vInfTarget / (vTarget + vEsc);   // cancellation-free v_target − v_esc
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
  // heliocentric pumping campaign at v∞ + planeTaxFor(v∞, β) (the DERIVED 3-D tilt cost,
  // issue #9 — the campaign steers the out-of-plane aim on its own hyperbolic leg;
  // quadratic near β = 0, half the far-field v∞·|sin β| bound at 2.48°) + tax (calibrated
  // against perihelionPumpedVinf: Δv − v∞ ≈ 2.0 km/s at the a₀ = 2.5e-4 design corridor).
  // The tax is v∞-DEPENDENT and, since issue #5, priced by the ANCHORED OPTIMISED schedule
  // under the DERIVED THERMAL power model (mirror of fermi_sim.pump_schedule
  // TAX_OPT_THERMAL_TABLE; cap_eff(0.42)=3.54): 11.6 km/s at v∞=8, +0.785 at the 23.64 AC
  // anchor. Validity [8, 26] km/s; throws outside. The cap-model optimised table
  // (schedule "optimized": −0.51 at the anchor, the PSI-comparable working point) and the
  // bang-bang table (pumpTaxBangbang: 2.0 at the anchor, valid to 29) remain available.
  const PUMP_TAX_VINF_MIN = 8e3;
  const TAX_OPT_THERMAL_TABLE = [
    [8000, 11634.6], [9000, 10771.2], [10000, 9924.1], [11000, 9093.6],
    [12000, 8280.2], [13000, 7484.8], [14000, 6708.4], [15000, 5952.5],
    [16000, 5218.9], [17000, 4510.1], [18000, 3829.1], [19000, 3179.7],
    [20000, 2567.3], [21000, 1998.3], [22000, 1482.0], [23000, 1031.2],
    [23640, 785.3], [24000, 664.5], [25000, 410.2], [26000, 299.6]];
  const TAX_OPT_TABLE = [
    [8000, 10562], [9000, 9704], [10000, 8863], [11000, 8038], [12000, 7229],
    [13000, 6439], [14000, 5665], [15000, 4911], [16000, 4176], [17000, 3462],
    [18000, 2770], [19000, 2104], [20000, 1467], [21000, 864], [22000, 300],
    [23000, -213], [23640, -509], [24000, -661], [25000, -1014], [26000, -1223]];
  const PUMP_TAX_TABLE = [
    [8000, 13505.8], [9000, 12434.7], [10000, 11727.2], [11000, 10874.8],
    [12000, 10100.8], [13000, 9215.6], [14000, 8558.2], [15000, 7785.7],
    [16000, 6914.6], [17000, 6224.6], [18000, 5570.4], [19000, 4859.5],
    [20000, 4122.8], [21000, 3562.5], [22000, 2907.1], [23000, 2345.5],
    [23640, 2000.0], [24000, 1760.2], [25000, 1246.3], [26000, 786.1],
    [27000, 394.8], [28000, 85.4], [29000, 0.0]];
  const _lerp = (T, v) => {
    for (let i = 0; i < T.length - 1; i++)
      if (v <= T[i + 1][0])
        return T[i][1] + (v - T[i][0]) * (T[i + 1][1] - T[i][1]) / (T[i + 1][0] - T[i][0]);
    return T[T.length - 1][1];
  };
  function pumpTaxFor(vinf, schedule = "thermal") {
    // schedule names mirror Python pump_tax_for exactly: "thermal" (default) / "optimized"
    // (cap-model) / "bangbang"; anything else THROWS (a silent fallback priced typos and
    // "bangbang" off the wrong, sign-flipped table — deep-audit finding)
    if (schedule === "bangbang") return pumpTaxBangbang(vinf);
    if (schedule !== "thermal" && schedule !== "optimized")
      throw new Error("pumpTaxFor: unknown schedule '" + schedule
        + "' (use 'thermal', 'optimized' or 'bangbang')");
    if (!Number.isFinite(vinf) || vinf < PUMP_TAX_VINF_MIN || vinf > 26e3)
      throw new Error("pumpTaxFor: v_inf " + (vinf / 1e3).toFixed(1) + " km/s is outside the "
        + "anchored optimised campaign's [8, 26] km/s range — use pumpTaxBangbang or integrate.");
    return _lerp(schedule === "thermal" ? TAX_OPT_THERMAL_TABLE : TAX_OPT_TABLE, vinf);
  }
  function pumpTaxBangbang(vinf) {
    if (!Number.isFinite(vinf) || vinf < PUMP_TAX_VINF_MIN)
      throw new Error("pumpTaxBangbang: v_inf below the swept 8 km/s range.");
    if (vinf >= 29e3) return 0;
    return Math.max(_lerp(PUMP_TAX_TABLE, vinf), 0);
  }
  // DERIVED out-of-plane (tilt) cost of the pumped campaign (mirror of fermi_sim
  // pump_schedule.PLANE_TAX_THERMAL_TABLE + departure.plane_tax_for, issue #9): the 3-D
  // anchored campaign steers thrust out of plane on the hyperbolic leg; knots are
  // dv3d(β, γ*) − dv3d(0) at the 23.64 km/s design aim (tools/derive_plane_tax.py).
  // ~Quadratic near 0 (~95 m/s·β²), 512 m/s at the 2.48° direct-optimum aim (the naive
  // far-field bound charges 1023 there; PSI's final assessment measures 578 at their 4×
  // cap — our cap-model derivation gives 606). Validity [0, 4°]; beyond, the far-field
  // MARGINAL slope continues the curve (measured <1% off at 6°). Knots scale by
  // (v∞ / 23.64 km/s). Always ≤ v∞·|sin β| (audit-pinned).
  const PLANE_TAX_THERMAL_TABLE = [
    [0.0, 0.0], [0.1, 1.2], [0.25, 6.7], [0.5, 24.3], [0.75, 54.0], [1.0, 94.2],
    [1.5, 205.2], [2.0, 350.8], [2.48, 512.1], [3.0, 708.7], [4.0, 1123.4]];
  const PLANE_TAX_BETA_MAX = 4.0, PLANE_TAX_V_REF = 23640.0;
  function planeTaxFor(vinf, tiltDeg) {
    if (!Number.isFinite(vinf) || !Number.isFinite(tiltDeg) || vinf < 0)
      throw new Error("planeTaxFor: need finite vinf >= 0 and finite tiltDeg");
    const beta = Math.abs(tiltDeg), scale = vinf / PLANE_TAX_V_REF;
    if (beta <= PLANE_TAX_BETA_MAX) return _lerp(PLANE_TAX_THERMAL_TABLE, beta) * scale;
    const edge = PLANE_TAX_THERMAL_TABLE[PLANE_TAX_THERMAL_TABLE.length - 1][1] * scale;
    return edge + vinf * (Math.sin(Math.min(beta, 90) * Math.PI / 180)
                          - Math.sin(PLANE_TAX_BETA_MAX * Math.PI / 180));
  }
  // Per-target campaign under the anchored design schedule (mirror of
  // fermi_sim.pump_schedule OPT_CAMPAIGN_THERMAL_TABLE — the shipped default — and
  // OPT_CAMPAIGN_TABLE, the cap-model comparator): [v_target, overhead, years, revs].
  const OPT_CAMPAIGN_THERMAL_TABLE = [
    [23000, 1031.2, 11.975, 7.869], [23250, 930.7, 11.999, 7.877],
    [23500, 835.8, 12.02, 7.883], [23640, 785.3, 12.038, 7.887],
    [23750, 746.9, 12.051, 7.89], [24000, 664.5, 12.094, 7.899],
    [24250, 589.1, 12.148, 7.906], [24500, 521.4, 12.214, 7.913],
    [24750, 461.8, 12.307, 7.921], [25000, 410.2, 12.458, 7.929],
    [25250, 367.3, 12.704, 7.938], [25500, 333.9, 13.156, 7.946],
    [25750, 311.0, 14.306, 7.954], [26000, 299.6, 20.603, 7.963]];
  const OPT_CAMPAIGN_TABLE = [
    [23000, -213.2, 12.004, 5.842], [23250, -332.1, 12.014, 5.850],
    [23500, -446.5, 12.026, 5.858], [23640, -508.5, 12.036, 5.863],
    [23750, -556.1, 12.042, 5.867], [24000, -660.6, 12.061, 5.876],
    [24250, -759.3, 12.083, 5.884], [24500, -851.7, 12.113, 5.894],
    [24750, -937.0, 12.149, 5.903], [25000, -1014.3, 12.202, 5.913],
    [25250, -1082.5, 12.279, 5.923], [25500, -1140.4, 12.408, 5.935],
    [25750, -1187.6, 12.641, 5.946], [26000, -1222.5, 13.188, 5.959]];
  function optCampaignFor(vinf, powerModel = "thermal") {
    const T = powerModel === "thermal" ? OPT_CAMPAIGN_THERMAL_TABLE : OPT_CAMPAIGN_TABLE;
    if (!Number.isFinite(vinf) || vinf < T[0][0] || vinf > T[T.length - 1][0]) return null;
    for (let i = 0; i < T.length - 1; i++)
      if (vinf <= T[i + 1][0]) {
        const f = (vinf - T[i][0]) / (T[i + 1][0] - T[i][0]);
        return { vinf, dv: vinf + T[i][1] + f * (T[i + 1][1] - T[i][1]),
                 years: T[i][2] + f * (T[i + 1][2] - T[i][2]),
                 revs: T[i][3] + f * (T[i + 1][3] - T[i][3]), reaches: true };
      }
    return null;
  }
  function pumpedDepartureDv(vinf, tiltDeg, periAltKm, apoAltKm, pumpTax = null) {
    if (pumpTax == null) pumpTax = pumpTaxFor(vinf);
    const rp = R_EARTH + periAltKm * 1e3;
    const ra = R_EARTH + Math.max(apoAltKm == null ? periAltKm : apoAltKm, periAltKm) * 1e3;
    const plane = planeTaxFor(vinf, tiltDeg);
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
    // non-finite input would make D = NaN, which SKIPS the D<=0 sentinel and returns a false
    // "converges" full of NaN — treat it as diverged instead (transitive-closure finding S3)
    if (![activeKg, payloadKg, dv, isp, propCoef, structFrac].every(Number.isFinite))
      return { converges: false, dryEff: Infinity, mProp: Infinity, structure: Infinity, wet: Infinity };
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
    oberthBurnFor, earthEscapeRevs, sunEscapeRevs, earthSoiRadius, injectionPointingDv, gncSteeringFactor, sepAchievableVinf, perihelionPumpedVinf, scheduledPumpedVinf, SCHEDULE_ANCHORED_THERMAL, capEff, cellTemperature, pumpedDepartureDv, pumpTaxFor, pumpTaxBangbang, planeTaxFor, optCampaignFor, synchrotronEscape, expv, propMass, elecEnergy, solarArrayArea, minimalDryMass,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.FERMI = API;
})(typeof globalThis !== "undefined" ? globalThis : this);
