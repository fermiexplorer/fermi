# 11 — Defensible arrival-epoch anchors: derive, don't assert

**Issue:** #11 · **Status:** shipped (build 176, 2026-08-01) · **Filed:** 2026-08-01

## Background (owner findings)

1. The pumped variation's "optimum at 77,800 yr" was over-precise: the fuel basin is
   flat to ~30 m/s (below the model's own noise floor) and its bottom moved when the
   tilt pricing was refined — a fragile headline number.
2. PSI did not derive the pumped arrival epoch: their stated "~73,000 yr" for the
   pumped recommendation reuses the impulsive optimum, and their report flags the
   pumped tilt pricing as open future work (§2.5, R6). Under the derived tilt curve
   the 73k epoch costs the pumped vehicle +0.27 km/s.
3. The page asserted optima without showing the optimization: no visible per-epoch
   comparative simulation, no per-architecture basins.

## Shipped record

- **Design anchors, per architecture, geometry over fragility:** the pumped design
  epoch is the ~79,252-yr ECLIPTIC CROSSING — the only derivation-independent epoch
  in its basin (fixed by astrometry alone; +27 m/s vs the wandering basin bottom,
  inside model noise). Direct keeps its ~72,800-yr fuel optimum (PSI-corroborated).
  Architecture switch snaps the arrival slider to the selected variation's design
  point; the page's native default is the pumped variation at the crossing.
- **The optimum is now derived by comparative simulation, and recorded:**
  `tools/derive_epoch_table.py` integrates the FULL 3-D anchored thermal campaign at
  ten arrival epochs (no closed-form budget in the loop; per-epoch steering
  optimisation) — basin visible in data: 73k +273 m/s, 75k +93, 77k +7, 77.8k
  bottom, crossing +27, 85k +498; epochs ≤ ~68k are NOT FLYABLE (tilt beyond the
  hyperbolic-leg validity). The closed-form budget sweep matches the direct
  simulations to ~30 m/s across the window. Per-architecture sweeps (pumped /
  direct / jupiter / oberth — one basin each, never mixed): tmp/ro/i11_arch_sweeps.py
  run recorded in this plan's issue.
- **Fuel-optimum readout honesty:** "at the optimum" is judged in Δv (any aim within
  50 m/s of the minimum is inside the flat basin — model noise), not in years.
- **Provenance stated on-page** ("Two mission variations" table): direct's epoch
  matches PSI's independent 73,012 to 0.2%; the pumped fuel optimum is our
  derivation (PSI left it open), validated against their one measured 3-D point
  to 5%.
- **The second optimization dimension (owner finding):** the pumped epoch window
  ~73k–79.3k is flat in fuel (±0.3 km/s) AND in program cost (~$25k of xenon +
  launch mass under PSI's own cost model), so the ARRIVAL DATE itself becomes a
  legitimate axis: the early (~73k) end arrives ~6,000 yr sooner for a
  rounding-error price. Presented as a design WINDOW: crossing end =
  fuel/geometry robustness (slider default), 73k end = arrival value (the
  charitable reading of PSI's quoted arrival). Cost optimization proper
  (custody/ops/automation vs the $10M target) is issue #12.

## Verification

`tmp/ro/verify_ui_now.py` all green: audits + parity + UI (crossing-anchor default
checks, basin-membership check in Δv, snap checks both directions).

## Push / merge

Released via the `tools/release.py` wrapper (deploy: index.html changed); commit
closes #11. Follow-up (cost-criterion optimization layer) tracked as issue #12.
