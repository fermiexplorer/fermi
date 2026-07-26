# 02 — Tighten the SEP power-gate integrator (adaptive dt + mass-coupled RK4)

Issue: https://github.com/fermiexplorer/fermi/issues/2
Roadmap: `docs/PRECISION_ROADMAP.md` Stage 1

## Problem

`fermi_sim.departure.sep_achievable_vinf` (mirrored in `web/physics.js
sepAchievableVinf`) has two first-order weaknesses in the same integrator:

1. **Fixed 50,000 s timestep**; the result is ~3% off a finer-step integration.
2. **Mass is Euler-updated, not RK4-coupled** (external ledger F6a.1): all four
   RK4 stages evaluate thrust with the mass from the start of the step, and the
   mass is decremented once afterwards — first-order for the mass while the state
   is fourth-order. Worst case (high power, ~80% propellant fraction, ~10⁴ steps)
   this adds ~1% error on top of the timestep's ~3%.

No verdict changes (solar saturates far below the 23.3 km/s floor with wide
margin), but the printed achievable-v∞ values — the page gate numbers, the star
tables' "Min solar α" column, the α ≈ 100 W/kg outward-spiral threshold — carry
the error. Decision (owner): tighten the numbers rather than document the
looseness.

## Change

1. `fermi_sim/departure.py`: replace `dt = 5.0e4` with the adaptive scheme the
   pumping integrator already uses — `dt = min(max(600, 0.002·period), 5·86400)`,
   period from the local osculating orbit.
2. Fold mass into the RK4 state vector (5th component, ṁ = −F/vₑ) so all four
   stages see a consistently advanced mass; clamp at `dry_pay_kg` on stage
   evaluation. (Check whether `perihelion_pumped_vinf` warrants the same
   treatment — its per-step mass change is ~10³× smaller, likely below noise;
   document the measurement either way.)
3. Mirror both in `web/physics.js sepAchievableVinf` (keep the memo cache; results
   change, so cached keys are naturally fresh).
4. Add a step-halving convergence assertion to `audit/calcs/audit_departure.py`
   (halving dt moves achievable v∞ by < 0.5%).

## Re-baseline (same commit — see docs/DOC_MAINTENANCE.md)

- Parity REF values for the SEP/NEP checks in `audit/calcs/audit_webjs.mjs`.
- Star tables' `amin` column: regenerate `web/stars.js` via
  `tools/make_starmap_data.py` (its α-feasibility curve calls the gate).
- Page/REPORT quotes that move: the α ≈ 100 W/kg threshold, the 0/3.1/16.7 km/s
  spiral-ceiling triplet, the "Min solar α" caption values if they shift.
- `audit/AUDIT_COMPARISON.md` outward-spiral rows if the engine column moves.

## Verification

- `.venv/bin/python audit/calcs/run_audits.py` green at the new baseline
  (including the new convergence check).
- `node audit/calcs/audit_webjs.mjs` 35+/35+ at the re-baselined REFs.
- `.venv/bin/python audit/calcs/ui_sliders.py` green (gate feasibility verdicts
  unchanged: default closes, low-α does not).
- `.venv/bin/pytest tests/` green.

## Push / merge

Branch from `main`, one commit (engine + mirror + re-baselines together), deploy
via `tools/deploy.py` (physics.js + stars.js change), commit+push both Pages
clones, push the branch, PR into `main` (or direct push per current practice),
poll `tmp/ro/poll_live.py`, close issue #2 with a comment linking the commit.
