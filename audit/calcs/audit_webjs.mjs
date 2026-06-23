// Audit 6 -- web calculator JS vs Python engine parity.
// Loads the SAME physics module the web page uses (web/physics.js) and checks it
// against reference values produced by the validated Python engine (fermi_sim).
// Run:  node audit/calcs/audit_webjs.mjs
import { createRequire } from "module";
import { fileURLToPath } from "url";
import path from "path";

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const F = require(path.join(here, "..", "..", "web", "physics.js"));

// Reference values from the Python engine (run_analysis.py / dump_state.py).
const REF = {
  tangential_yr: 58138.32310500001,
  tangential_vinf_kms: 23.271895966952513,
  ecliptic_crossing_yr: 79252.25245836211,
  vinf_75k_kms: 23.81055748451608,
  tilt_75k_deg: -1.5174801147861419,
  // impulsive departure Δv from LEO 400 km at 75k yr arrival (km/s)
  dv_impulsive_75k_kms: 13.89,
  // DERIVED low-thrust (naïve spiral) departure Δv from LEO 400 km at 75k yr (km/s)
  dv_lowthrust_75k_kms: 25.127443,
  // ...from a 590x35786 km elliptical (GTO-like) start at 75k yr (km/s)
  dv_lowthrust_gto_75k_kms: 21.690959,
  // Earth-escape revolutions for 0.2 N on 600 kg from 590 km
  earth_escape_revs_ref: 981.919542,
  // Sun-escape revolutions (heliocentric spiral-out) for 0.2 N on 600 kg from 1 AU
  sun_escape_revs_ref: 0.707852,
  // Earth sphere-of-influence radius (m) — the physical radius of the escape disk
  earth_soi_radius_ref: 924646795.104645,
  // injection-pointing correction Δv (m/s) for 1° at 590 km, and GNC cosine-loss factor at 5°
  injection_pointing_dv_ref: 132.0702276157546,
  gnc_steering_factor_ref: 1.0038198375433474,
  // conservative 1/r² power-limited achievable v∞ (m/s): 20 kW, 1600 kg wet, 300 kg dry, Isp 1585, η0.5
  sep_achievable_vinf_ref: 19547.62063596138,
  // constant-power (nuclear-electric, fade_exp=0) achievable v∞ (m/s), same args — the EP-only escape
  sep_achievable_vinf_nep_ref: 31112.327059089537,
  // cruise time for v_inf = 24 km/s (yr)
  time_24kms_yr: 46072,
};

let pass = 0, total = 0;
function check(name, a, b, tol) {
  total++;
  const ok = Math.abs(a - b) <= tol * Math.max(Math.abs(a), Math.abs(b), 1e-30);
  console.log(`  [${ok ? "PASS" : "FAIL"}] ${name}  -- js ${a.toFixed(4)} vs py ${b.toFixed(4)}`);
  if (ok) pass++;
}

console.log("== Audit 6: web JS <-> Python parity ==");

check("tangential arrival time (yr)", F.tangentialT() / F.YEAR, REF.tangential_yr, 1e-4);
check("tangential v_inf (km/s)", F.intercept(F.tangentialT()).vinf / 1e3, REF.tangential_vinf_kms, 1e-4);
check("ecliptic crossing (yr)", F.eclipticCrossingT() / F.YEAR, REF.ecliptic_crossing_yr, 1e-4);

const ic75 = F.intercept(75000 * F.YEAR);
check("v_inf at 75k yr (km/s)", ic75.vinf / 1e3, REF.vinf_75k_kms, 1e-4);
check("tilt at 75k yr (deg)", ic75.tiltDeg, REF.tilt_75k_deg, 1e-3);

const dep = F.vInfEarth(ic75.vinf, ic75.tiltDeg);
check("impulsive Δv from LEO at 75k (km/s)", F.impulsiveDv(dep.vInfE, 400) / 1e3, REF.dv_impulsive_75k_kms, 2e-3);
check("derived low-thrust departure Δv at 75k (km/s)", F.lowthrustDepartureDv(ic75.vinf, ic75.tiltDeg, 400) / 1e3, REF.dv_lowthrust_75k_kms, 1e-4);
check("derived low-thrust Δv, 590x35786 elliptical start (km/s)", F.lowthrustDepartureDv(ic75.vinf, ic75.tiltDeg, 590, 35786) / 1e3, REF.dv_lowthrust_gto_75k_kms, 1e-4);
check("Earth-escape revolutions (0.2 N, 600 kg, 590 km)", F.earthEscapeRevs(0.2, 600, 590).revs, REF.earth_escape_revs_ref, 1e-4);
check("Sun-escape revolutions (0.2 N, 600 kg, 1 AU)", F.sunEscapeRevs(0.2, 600, 1).revs, REF.sun_escape_revs_ref, 1e-4);
check("Earth SOI radius (m)", F.earthSoiRadius(1), REF.earth_soi_radius_ref, 1e-4);
check("injection pointing Δv (1°, 590 km)", F.injectionPointingDv(1, 590), REF.injection_pointing_dv_ref, 1e-4);
check("GNC steering factor (5°)", F.gncSteeringFactor(5), REF.gnc_steering_factor_ref, 1e-4);
check("SEP achievable v∞ under 1/r² (20 kW, 1600 kg)", F.sepAchievableVinf(20000,1600,300,1585,0.5,1,2), REF.sep_achievable_vinf_ref, 2e-3);
check("NEP achievable v∞ constant power (fade_exp=0)", F.sepAchievableVinf(20000,1600,300,1585,0.5,1,0), REF.sep_achievable_vinf_nep_ref, 2e-3);
check("derived minimal dry mass (active 155, pay 1, 30 km/s, Isp 3000, tank 2.5%, struct 10%)",
  F.minimalDryMass(155,1,30000,3000,0.025,0.10).dryEff, 221.5710758812226, 1e-6);

check("cruise time at v_inf=24 km/s (yr)", F.timeToAc(24e3) / F.YEAR, REF.time_24kms_yr, 1e-3);

// Internal consistency: rocket equation + energy formula round-trips.
const mp = F.propMass(255, 20e3, 3000);
check("xenon mass for 20 km/s @Isp3000 (kg)", mp, 248.2, 2e-3);

// Solar array sizing parity (silicon: 5 kW, 20% cells -> 18.37 m^2).
check("solar array area @5kW,20% (m^2)", F.solarArrayArea(5000, 0.20, 1), 18.3688, 1e-3);
check("solar array area scales as r^2 (2 AU)", F.solarArrayArea(5000, 0.20, 2), 73.475, 1e-3);

console.log(`\n${"-".repeat(60)}\nWEB PARITY: ${pass}/${total} checks passed`);
process.exit(pass === total ? 0 : 1);
