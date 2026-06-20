# Grok Conclusions — Independent Audit

Deep review of Project Fermi (branch `codex/v3-independent-audit`, June 2026).
Independent simulations live in `audit/grok/`; the parallel Codex session in
`audit/codex/` was not modified.

## What Was Run

| Artifact | Purpose |
|---|---|
| `audit/grok/grok_independent_checks.py` | Cross-check core physics without importing `fermi_sim` |
| `audit/grok/grok_sensitivity_sweeps.py` | Design-space sweeps → `sweep_results.json` |
| `audits/run_audits.py` | Existing 41-check independent suite |
| `node audits/audit_webjs.mjs` | Python ↔ web JS parity (10 checks) |
| `.venv/bin/pytest` | Engine smoke tests (8) |
| `.venv/bin/python run_analysis.py` | Integrated baseline report |

All checks passed.

## Independent Simulation Results

`grok_independent_checks.py` uses **different methods** from the Codex v3 script:

- Alpha Centauri state from **astropy** (not hand-built catalog algebra)
- Departure-Δv minimum via **200-yr grid + parabolic refinement** (not scipy)
- Earth escape spiral via a **separate RK4 integrator** (not `fermi_sim.departure`)
- Fuel-cell optimum via **golden-section search** (Codex uses scipy)

Key numbers (astropy-based):

| Quantity | Value |
|---|---|
| AC distance now | 4.344 ly |
| AC space speed | 32.301 km/s |
| Closest approach | 27,960 yr @ 3.130 ly |
| **Exact impulsive Δv floor** | **13.875 km/s @ 72,793 yr** |
| 75,000-yr benchmark Δv | 13.886 km/s (+10.3 m/s above floor) |
| 75,000-yr cruise v∞ | 23.811 km/s, tilt −1.5° |
| 2600 AU miss half-window @ 75k | ±710 yr |
| 2600 AU miss half-window @ optimum | ±689 yr |
| Independent spiral Δv @ 75k | 25.06 km/s (engine: 25.13) |
| Default 5 kW silicon array | 18.37 m², 55.1 kg, 91 W/kg |
| Dry-mass remainder (bus+payload) | 150 kg |
| Fuel-cell reactant @ Isp 3000 s | 37.3 t (677× array mass) |
| Mass-optimal fuel-cell Isp | 1353 s, 28.3 t consumables |

Astropy and hand-built catalog states agree to machine precision (<10⁻⁸ % on speed).

## Sensitivity Sweep Highlights

From `sweep_results.json`:

1. **Flat Δv region.** Impulsive departure Δv stays between 13.9 and 14.0 km/s for
   arrival times **66,500 – 81,000 yr** — a 14,500-yr window only 125 m/s wide at
   the top end. The mission is not sensitive to picking 75k vs 73k vs 78k within
   this band.

2. **100,000-yr deadline headroom.** The minimum cruise speed that still intercepts
   within 100k yr is the tangential floor **23.30 km/s**, arriving at ~55,300 yr.
   The baseline 23.8 km/s @ 75k yr uses only ~75% of the allowed timeline.

3. **Isp trade (20 km/s, 255 kg dry).** Propellant fraction ranges 40–64% for
   Isp 4000–2000 s; dry-mass closure stays positive (133–156 kg remainder) across
   the sweep. Isp 3000 s is a reasonable middle ground.

4. **Power trade.** At 12 kW the array alone is 132 kg, leaving only **31 kg** for
   bus + payload + margin on a 255 kg dry budget. The 5 kW default is not arbitrary —
   higher power tightens mass closure sharply without changing the physics conclusion.

5. **Cell efficiency.** Array mass spans 41 kg (30% cells) to 104 kg (12% cells) at
   5 kW. The 20%/3 kg/m² default is mid-range and defensible, but the conclusion
   (solar wins) holds even at pessimistic 12% efficiency.

## Conclusions — Physics & Architecture

### 1. The core feasibility claim is robust

Direct LEO → Alpha Centauri on solar-electric ion propulsion satisfies the tender
criterion (≤2600 AU miss, ≤100,000 yr) with margin. A ~500 kg wet vehicle, ~20 km/s
realistic low-thrust budget, and ~75k yr arrival is consistent across:

- the `fermi_sim` engine,
- 41 independent `audits/` checks,
- this Grok re-implementation (astropy + grid search + separate integrator),
- the Codex v3 re-implementation (hand-built + scipy),
- web JS parity.

No numerical disagreement exceeds rounding tolerance on any headline quantity.

### 2. Departure Δv ≠ cruise speed — and the energy chain closes

The ~14 km/s impulsive floor is LEO departure budget, not coast speed. Patched-conic
energy plus Earth's 29.8 km/s in-plane orbital velocity yields ~24 km/s heliocentric
cruise. The 75k-yr worked example closes exactly: AC is 5.957 ly away, and 23.811 km/s
× 75,000 yr covers 5.957 ly (closure error <10⁻¹³ %).

The realistic ion budget (~20 km/s) sits between the 13.9 km/s impulsive floor and
the ~25 km/s naive continuous-spiral ceiling. Industry perigee-biased SEP (~20 km/s)
is therefore a credible design point, not an optimistic fudge.

### 3. Solar decisively beats fuel cells — by orders of magnitude

Electric propulsion needs ~50,000 kWh for 20 km/s. Chemical reactants store ~MJ/kg;
even the mass-optimal fuel-cell Isp (1353 s) needs **28 tonnes** of consumables vs
**55 kg** of silicon array. The wall is energy density, not exhaust velocity.
Hybrid architectures add fuel-cell mass for zero benefit on a Sun-proximate burn.

### 4. Gravity assists are optional, not required

Jupiter can donate ~15 km/s in best geometry, but alignment with the AC aim direction
is rare and adds ~6 yr. Solar Oberth (~1–2 km/s burn near the Sun → ~24 km/s v∞)
cuts onboard Δv dramatically but needs a heat shield and perihelion-lowering
maneuver. Direct SEP remains the simplest path that meets the schedule constraint.

### 5. Model fidelity limits are understood and small

- **Straight-line AC motion** over 75k yr: galactic tidal curvature ≈ 1 AU over
  100k yr — negligible vs 2600 AU tolerance.
- **2600 AU miss mapping**: ±690 yr at the exact optimum, ±710 yr at the 75k
  benchmark — both well inside the 100k-yr envelope.
- **1 AU launch offset** ignored: correct at this scale (~5.5 ly target distance).

## Conclusions — Documentation & Product Gaps

These do not undermine the physics but should be fixed before tender-facing use:

1. **Stale mass figures.** `README.md` and `docs/REPORT.md` §2 still cite a ~33 kg
   solar array; the current silicon model reports **55 kg** @ 5 kW. Audit counts in
   README are also stale (41 Python + 10 JS, not 32 + 8).

2. **Optimum arrival time wording.** `index.html` methodology says the departure-Δv
   optimum sits "~75k yr". The exact floor is **~72.8 kyr**; 75k is a defensible
   near-equivalent (+10 m/s, 0.07 %), not the optimum itself.

3. **Third-party names in shipped artifacts.** `index.html`, `run_analysis.py`, and
   `fermi_sim/spacecraft.py` reference Starlink/SpaceX/ExoTerra despite the repo rule
   against identifying names in public artifacts.

4. **Web propellant selector is cosmetic.** Krypton/Argon change labels and tank
   fraction but not Isp, thrust, density, or storage volume.

5. **Web JS impulsive Δv at 75k** shows 13.886 km/s vs Python 13.890 km/s — within
   parity tolerance but worth noting the slider uses a slightly different departure
   path than the analysis script's full `departure_budget()`.

6. **Power headroom.** The sensitivity sweep shows array mass scales linearly with
   power; pushing beyond ~8 kW on a 255 kg dry budget erodes payload margin quickly.
   If higher thrust is desired, wet mass must grow or dry mass budget must be reallocated.

## Agreement With Codex v3 Audit

The Grok and Codex independent scripts agree on every headline quantity to ≤0.1 %.
Methodological differences (astropy vs hand-built, grid vs scipy, golden-section vs
scipy) produce no material divergence. Both audits independently confirm:

- optimum ≈ 72,792 yr / 13.875 km/s,
- 75k penalty ≈ 10 m/s,
- miss window ≈ ±710 yr @ 75k,
- array mass ≈ 55 kg,
- fuel-cell penalty ≈ 677× solar array mass.

## Recommended Next Steps

1. Update `README.md` and `docs/REPORT.md` solar-array mass and audit counts.
2. Fix `index.html` optimum wording (72.8 kyr exact, 75 kyr benchmark).
3. Scrub or anonymise vendor names in shipped artifacts per repo rule.
4. Promote the exact-optimum and 75k energy-chain checks from `audit/codex/` and
   `audit/grok/` into `audits/` once the v3 review is accepted.
5. Either make the propellant selector physically meaningful or label it as a
   tankage/display sensitivity only.

## Files Produced

```
audit/grok/
  grok_independent_checks.py   # astropy + grid + independent spiral
  grok_sensitivity_sweeps.py   # parameter sweeps
  sweep_results.json           # sweep output data
  grok-conclusions.md          # this document
```