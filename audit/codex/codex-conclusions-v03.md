# Codex Conclusions v03

Fresh deep review of the current code and docs. This round starts over from the
current `main` state and adds an independent numerical script:

- `audit/codex/v3_independent_checks.py`

The script intentionally does not import `fermi_sim`; it rebuilds the Alpha
Centauri state, intercept geometry, departure energetics, solar sizing, and
fuel-cell optimization from local constants and standard equations.

## Independent Simulation Results

`v3_independent_checks.py` passed. Key outputs:

- Alpha Centauri distance now: 4.344 ly.
- Alpha Centauri space speed: 32.3008 km/s.
- Closest approach: 27,960 years at 3.1297 ly.
- Exact impulsive direct-departure floor: 13.875 km/s at 72,792 years.
- 75,000-year benchmark: 13.886 km/s, only 10.3 m/s above the floor.
- 75,000-year cruise speed: 23.811 km/s.
- 70,000-year distance check: AC is 5.506 ly away; 23.579 km/s for 70,000 years
  covers 5.506 ly.
- 75,000-year distance check: AC is 5.957 ly away; 23.811 km/s for 75,000 years
  covers 5.957 ly.
- 2600 AU miss tolerance at the 75,000-year benchmark maps to about +/-710 years.
- First-order galactic-curvature estimate over 100,000 years: about 1.03 AU.
- Default 5 kW silicon array: 18.37 m^2, 55.1 kg, 90.7 W/kg.
- Baseline mass closure: 55.1 kg array + 30.0 kg engine/PPU + 19.9 kg tankage,
  leaving 150.0 kg of dry mass for bus, payload, and margin.
- Fuel-cell EP at Isp 3000 s: 37.3 tonnes H2/O2 reactants, about 677x the default
  solar-array mass.
- Mass-optimal fuel-cell EP: Isp 1353 s and about 28.3 tonnes consumables.

## Conclusions That Still Hold

1. The core architecture conclusion remains sound at this model fidelity: direct
   solar-electric ion propulsion from LEO can satisfy the 2600 AU / 100,000-year
   criterion with a roughly 500 kg wet vehicle and a roughly 20 km/s realistic
   low-thrust budget.

2. The latest report's "delta-v budget is not cruise speed" worked example is
   numerically consistent. The 14 km/s LEO departure budget is not the coast speed;
   patched-conic energy plus Earth's orbital velocity produce a roughly 24 km/s
   heliocentric cruise.

3. The exact optimum remains near 72.8 kyr, but the 70-80 kyr region is flat enough
   that the round 75 kyr benchmark is a defensible communication simplification.

4. The current solar sizing model is better than the earlier fixed-W/kg model. It
   exposes the physical area and areal-density assumptions and still closes the
   baseline dry-mass budget.

5. The fuel-cell result remains robust. Even after using the heavier 55 kg silicon
   array instead of the old 33 kg array, chemical reactants are hundreds of times
   heavier than solar for the same electric-propulsion energy.

## New Or Reconfirmed Findings

1. `README.md` is stale. It still says the baseline has a ~33 kg solar array and
   that audits are 32 Python checks plus 8 JS checks. Current reality is a 55 kg
   default silicon array, 41 Python checks, and 10 JS checks.

2. `docs/REPORT.md` is partly stale. Section 2 still says the 5 kW burn uses a
   ~33 kg solar array, while the current model and `run_analysis.py` report about
   55 kg for the default silicon array.

3. `index.html` still says the departure-delta-v optimum is "~75k yr" in the
   methodology text. This should be updated to say exact floor near 72.8 kyr, with
   75 kyr retained only as a near-equivalent benchmark.

4. The previous v02 statement that 2600 AU maps to roughly +/-690 years around a
   fixed 75 kyr intercept should be corrected. The independent v3 calculation gives
   about +/-710 years at 75 kyr. The ~690-year value corresponds more closely to
   the exact 72.8 kyr optimum.

5. Shipped public artifacts still contain identifying third-party names despite the
   repo rule against them. Current examples include Starlink/SpaceX and ExoTerra
   in `index.html`, and Starlink-class wording in `run_analysis.py` and
   `fermi_sim/spacecraft.py`.

6. The web references section is not yet source-rigorous. Several quantitative
   references point to Wikipedia or a vendor homepage. Tender-facing docs should
   prefer primary mission pages, datasheets, papers, or standards, with assumptions
   clearly labeled when primary data is unavailable.

7. The propellant selector in the browser is only partially physical. Krypton and
   Argon change the label and tank fraction, but not thruster performance, density,
   storage volume, cost, or achievable Isp/efficiency.

8. The browser badge still says "Xenon fraction" even when Krypton or Argon is
   selected. The KPI and chart labels update correctly, so this is a localized UI
   text bug.

9. The web footer says "No third-party site code was used" while the page loads
   Plotly from a CDN. The intended point appears to be that no third-party physics
   code is used; the wording should say that.

10. The new solar audit verifies arithmetic and broad plausibility, but it does not
    independently validate the default 20% cell efficiency, 3 kg/m^2 areal density,
    6 kg/kW engine/PPU mass, or 8% tank fraction against primary sources.

11. The current project audit suite verifies the broad departure region, but not
    the exact 72,792-year optimum printed by `run_analysis.py`. The v3 independent
    script covers it; promoting that check into `audits/` would prevent regression.

## Recommended Fix Order

1. Update README and `docs/REPORT.md` stale solar-array masses and audit counts.

2. Clean shipped public text of identifying vendor/product names, or explicitly
   adjust the repo rule if those names are now intended.

3. Replace weak web references with primary sources and label unsourced defaults.

4. Update `index.html` methodology text for the exact 72.8 kyr optimum and the
   75 kyr near-equivalent benchmark.

5. Fix the propellant badge and either make the propellant selector physically
   meaningful or label it as a tankage/display sensitivity only.

6. Clarify the Plotly/CDN wording: no third-party physics code is used, but the UI
   does load Plotly from a third-party CDN.

7. Consider moving the exact-optimum and 75k energy-chain checks from
   `audit/codex/v3_independent_checks.py` into the normal `audits/` suite after the
   v3 review is accepted.
