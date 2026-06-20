# Codex Conclusions v01

Deep audit performed against the prompts in `docs/CODEX_AUDIT_PROMPTS.md`.

## Bottom Line

The core feasibility result holds: direct solar-electric ion propulsion from LEO is
a viable first-order architecture for reaching within 2600 AU of Alpha Centauri in
less than 100,000 years. The nominal vehicle remains roughly 500 kg wet, with a
~20 km/s low-thrust budget, ~40-50% xenon, and a best arrival window around
70,000-80,000 years.

## Findings

1. The shipped web methodology had one substantive text error: it described the
   fuel-cell optimum as ~250 s. The model result is ~1350 s for separate-reactant
   fuel-cell electric propulsion; ~245 s is the self-powered exhaust cap. The live
   calculator math was already correct.

2. The exact direct-departure Δv floor is ~13.88 km/s at ~72,800 years (not
   75,000). The Δv-vs-arrival curve is extremely flat near the optimum, so a
   round 75,000-year arrival is practically the same point: its budget is
   13.886 km/s versus 13.875 km/s at 72,800 years — i.e. only ~10 m/s MORE than
   the optimum (a ~0.07% increment), far below the first-order model's precision.
   Units to avoid confusion: the total budget is ~13.9 km/s; the 75k-vs-optimum
   penalty is ~10 m/s.

3. The Alpha Centauri ephemeris, ecliptic rotation, and proper-motion conversion
   check out against Astropy. Closest approach is about 27,960 years from now at
   about 3.13 ly.

4. The straight-line Alpha Centauri propagation assumption is acceptable for the
   tender target. A first-order galactic-tide estimate gives about 1 AU of relative
   curvature over 100,000 years, far below the 2600 AU miss-distance allowance.

5. The 2600 AU tolerance maps to roughly +/-690 years around a fixed 75,000-year
   intercept, using the local probe-to-target relative speed.

6. The patched-conic departure formulas are internally consistent. The model's
   best-case launch geometry is optimistic by design because it assumes the
   in-ecliptic projection of the departure velocity can be aligned with Earth's
   orbital velocity.

7. The low-thrust spiral value around 25 km/s is a credible naive upper bound.
   The project still needs an explicit citation or sensitivity table for the
   optimized ~20 km/s perigee-biased SEP assumption.

8. The rocket-equation, power, thrust, and energy bookkeeping are consistent:
   255 kg dry mass, 20 km/s, Isp 3000 s, eta 0.6 gives about 248 kg xenon,
   about 49,700 kWh, and about 1.1 years at 5 kW.

9. The fuel-cell conclusion is robust. At the mass-optimal point, consumables are
   still about 28 tonnes versus tens of kg for a solar array. High-Isp fuel-cell
   electric propulsion gets worse because electrical energy rises with exhaust
   velocity at fixed mission delta-v.

10. Gravity-assist and solar-Oberth values are geometric upper bounds, not phased
    trajectory solutions. They are useful architecture comparisons, not mission
    designs.

## Residual Risks

1. The largest feasibility sensitivity is the assumed optimized low-thrust escape
   penalty: ~20 km/s is plausible but not directly derived by this code.

2. The 150 W/kg solar-array assumption is plausible for modern lightweight arrays
   but should be sourced or varied in a sensitivity sweep.

3. The model assumes best-case launch timing and does not solve a calendar-phased
   Earth departure.

4. Gravity-assist options are not launch-window or phasing solutions.

5. Long-duration payload survival, communications, and operations over tens of
   thousands of years are outside the propulsion feasibility model.

## Verification Run

- `.venv/bin/pytest`: 8/8 passed
- `.venv/bin/python audits/run_audits.py`: 32/32 passed
- `node audits/audit_webjs.mjs`: 8/8 passed
- `.venv/bin/python run_analysis.py`: completed and matched the feasibility result

External sanity checks used NASA/JPL material on solar electric propulsion and
NASA's DART mission page for current flight context.

## Follow-up (addressed after v01)

- **Finding 1** (fuel-cell optimum wording): fixed — the web methodology now states
  the separate-reactant optimum is ~1350 s and the self-powered cap is ~2.4 km/s.
- **Finding 2 / reviewer note**: Point 2 reworded for clarity. Floor ~13.88 km/s at
  ~72,800 yr; the round 75,000-yr arrival is only ~10 m/s (≈0.07%) above that. Units
  made explicit (total budget in km/s vs the 75k-vs-optimum increment in m/s).
- **Finding 7 / Residual 1** (SEP ~20 km/s): the calculator now states the budget is
  bracketed by the ~14 km/s impulsive floor and the ~25 km/s spiral bound, with the
  low-thrust-penalty slider as the sensitivity control; full phased finite-burn
  optimisation is flagged as future work.
- **Residual 2** (solar 150 W/kg): replaced with a physical, tunable sizing model —
  area = P/(S₀·η/r²), mass = area·areal density; commercial-silicon defaults (~20%
  cells, ~3 kg/m² → ~90 W/kg), plus solar/engine/propellant technology dropdowns, an
  ion-engine+PPU (~6 kg/kW) and tank (~8%) model, a mass-closure check, and a new
  independent audit (`audits/audit_solar.py`).

## Verification (current)

- `pytest`: 8/8 · `audits/run_audits.py`: 41/41 · `audits/audit_webjs.mjs`: 10/10
- `audits/ui_playwright.py`: renders all charts in Chromium, exercises the dropdowns
  and Play, no console errors.
