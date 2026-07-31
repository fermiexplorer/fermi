# 09 — Price the out-of-plane aim from a 3-D campaign (PSI-final follow-ups)

**Issue:** #9 · **Status:** open · **Filed:** 2026-07-31

## Background

The PSI final feasibility assessment (July 2026, archived
`audit/psi/PSI_FermiExplorerInterstellarPrecursor_FeasibilityAssessment.pdf`) measures the
out-of-plane cost of the 2.48° departure tilt with a fully three-dimensional
re-optimization of the pumping schedule: **0.58 km/s**, inside the planar bracket
[22 m/s, 1.02 km/s]. Our two-leg pumped budget prices that tilt at the bracket's
conservative upper end, v∞·|sin β| (1.02 km/s at the direct-optimum aim). Our
cross-check (`audit/psi/crosscheck_final.py`) confirms the pumped fuel optimum stays at
the ~79,250-yr ecliptic crossing under either pricing, so the shipped conclusions are
unaffected — but the pricing itself is now known to be ~1.75× conservative off-crossing.

## Scope

1. **3-D campaign extension (roadmap Stage 4).** Extend the anchored optimised schedule
   with out-of-plane steering (tilt acquired within the escape burns, as PSI's E.3 sweep
   does) and DERIVE our own tilt-cost curve dv_plane(v∞, β) — do not copy PSI's 0.58 km/s
   constant. Engine first (`fermi_sim/pump_schedule.py`), then mirror to `web/physics.js`,
   parity audit must pass.
2. **Early-arrival trade.** PSI leaves the 55–65 kyr branch open (cruise-speed minimum
   57,854 yr at 23.17 km/s, but tilt steepens toward −10°). With the derived 3-D tilt
   curve, settle whether any early-arrival aim beats the crossing under the pumped budget.
3. **Guards.** Add audit checks pinning the derived tilt curve at the 2.48° point against
   an independent integration, and a regression guard that the arrival-epoch optimum
   remains a corner at the crossing (or document the shift if the derived curve moves it).

## Verification

- `tmp/ro/verify_now.py` (full suite + parity) green.
- New `audit/calcs/audit_pumping.py` checks for the 3-D tilt curve.
- Cross-compare the derived dv_plane(23.64 km/s, 2.48°) against PSI's measured 0.58 km/s
  (agreement expected within the schedule-search scatter, ±0.2 km/s).

## Push / merge

Branch from `main`, one commit per landed stage, release via `tools/release.py`
wrapper (`tmp/rw/release_now.py`) — deploy required (index.html/web change). Close #9
with the final commit ("Closes #9").
