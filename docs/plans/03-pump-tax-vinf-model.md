# 03 — Replace the flat pump tax with a v∞-dependent overhead model

Issue: https://github.com/fermiexplorer/fermi/issues/3
Roadmap: `docs/PRECISION_ROADMAP.md` Stage 2

## Problem

`fermi_sim.departure.pumped_departure_dv` prices the pumping campaign as
v∞ + a flat 2 km/s tax, calibrated at the AC corridor (v∞ ≈ 23–25 km/s). The
integrated in-plane overhead is ~8 km/s at v∞ = 15 and ~13 km/s at v∞ = 8. The
corridor is currently ENFORCED (`PUMP_TAX_VINF_MIN` = 20 km/s raises in both
languages), which prevents silent mispricing but leaves low-v∞ targets without a
closed-form budget.

## Change

1. Sweep `perihelion_pumped_vinf` at the design a₀ across v∞ = 8–30 km/s
   (~1 km/s grid); fit overhead(v∞) = dv − v∞ with a low-order form (piecewise
   linear or rational) to ≤ 0.3 km/s of the integrator.
2. `pumped_departure_dv` uses tax(v∞) from the fit; drop the corridor guard
   (keep finite-input validation); document the fit's own validity range and
   residual.
3. Mirror the fit in `web/physics.js pumpedDepartureDv`.
4. Regression check in `audit/calcs/audit_pumping.py`: fit vs integrator at
   v∞ = {8, 12, 15, 20, 23.64, 28} within the stated residual.

## Re-baseline (same commit)

- Pumped-budget parity checks in `audit/calcs/audit_webjs.mjs` (in-corridor value
  shifts only if the fit differs from 2.0 km/s at 23.64 — keep the fit anchored
  there so shipped AC numbers are stable; state the anchor in the docstring).
- `audit/AUDIT_COMPARISON.md` §2b footnote (α² Lib row can then quote the
  closed-form budget instead of the manual integration).

## Verification

- `run_audits.py` green including the new fit-vs-integrator check.
- `audit_webjs.mjs` green.
- `ui_sliders.py` green (AC-corridor budgets unchanged at the anchor).
- `pytest tests/` green.

## Push / merge

Branch from `main`, one commit (engine + mirror + checks + doc updates), deploy
via `tools/deploy.py`, commit+push both Pages clones, push the branch, merge to
`main`, poll live, close issue #3 with a comment linking the commit.
