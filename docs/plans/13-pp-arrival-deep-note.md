# 13 — PP arrival optimum: deep simulation, audits, and the analysis note

**Issue:** #13 · **Status:** shipped (build 180, 2026-08-01) · **Filed:** 2026-08-01

## Owner request

Compile a detailed note for the PP arrival optimum, create a simulation for it, run
deep audits, and point to the detailed analysis.

## Shipped record

- **The analysis note:** `docs/PP-ARRIVAL-OPTIMUM.md` — question, method, the full
  per-epoch results table, cross-checks (convergence, closed-form sweep,
  independent own-code re-integration, PSI's one measured 3-D point), the error
  budget (why the bottom is a basin, not a point), PSI context with the
  negative-proof pointer, the design decision (crossing default; epoch a cost
  non-driver), residuals, and reproduction commands.
- **The simulation:** `tools/sim_pp_arrival.py` — 22-epoch direct 3-D campaign
  grid (2 kyr coarse + 500 yr fine + the exact crossing + the 73k comparison row),
  per-epoch steering optimisation, flyability-edge bisection, dt/8 convergence
  rows; writes the tracked machine record `docs/data/pp_arrival_sim.json`.
  Results: basin bottom 77,500 yr (32.204 km/s; 77.0–78.5k within 7 m/s —
  sub-noise plateau); crossing +26.7 m/s (design default); 73k +273 m/s;
  flyability edge ~65,000 yr (tilt −6.0°; custody 13.6 yr at 66k); custody
  12.0–12.1 yr across the basin; dt/8 convergence ≤4.1 m/s.
- **Deep audits:** audit_pumping §13h (6 checks) — record existence + meta pins,
  basin/crossing gates, agreement with the independent closed-form scan (≤600 yr),
  convergence gates (<40 m/s), a FRESH engine replay of the 75,000-yr row on every
  audit run, and a live probe that the 65-kyr aim is not acquirable (the edge is
  real). Full suite green.
- Surfaces: the page epoch table synced to the record (77,500 bottom row, 66k row,
  edge-annotated 65k row) + a link block to the note and the record; basin prose
  aligned (~77,500, sub-noise) on README/REPORT/run_analysis/PP-NOTES;
  audit_docs basin guard accepts the refined value.

## Verification

`tmp/ro/verify_ui_now.py` all green (suite includes the new 13h replays).

## Push / merge

Released via the `tools/release.py` wrapper (deploy: index.html changed); commit
closes #13.
