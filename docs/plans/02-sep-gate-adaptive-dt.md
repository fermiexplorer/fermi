# 02 — Tighten the SEP power-gate integrator (adaptive dt)

Issue: https://github.com/fermiexplorer/fermi/issues/2
Roadmap: `docs/PRECISION_ROADMAP.md` Stage 1

## Problem

`fermi_sim.departure.sep_achievable_vinf` (mirrored in `web/physics.js
sepAchievableVinf`) integrates the conservative 1/r² solar-power-fade gate with a
fixed 50,000 s timestep; the result is ~3% off a finer-step integration. No verdict
changes (solar saturates far below the 23.3 km/s floor with wide margin), but the
printed achievable-v∞ values — the page gate numbers, the star tables' "Min solar α"
column, the α ≈ 100 W/kg outward-spiral threshold — carry the error. Decision
(owner): tighten the numbers rather than document the looseness.

## Change

1. `fermi_sim/departure.py`: replace `dt = 5.0e4` with the adaptive scheme the
   pumping integrator already uses — `dt = min(max(600, 0.002·period), 5·86400)`,
   period from the local osculating orbit.
2. Mirror in `web/physics.js sepAchievableVinf` (keep the memo cache; results
   change, so cached keys are naturally fresh).
3. Add a step-halving convergence assertion to `audit/calcs/audit_departure.py`
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
