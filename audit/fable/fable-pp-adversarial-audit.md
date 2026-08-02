# Adversarial audit — the PSI final paper (PP claims) + the PP arrival-optimum derivation

**Run:** 2026-08-01, 126 agents (10 adversarial finder lenses → 3 distinct-lens
skeptics per finding, 2-of-3 survival → synthesis), ~52 min, ~5.7M subagent tokens,
1,492 tool calls. Targets: the archived PSI **final** assessment's PP-relevant claims,
and this repo's PP arrival-optimum derivation (3-D integrator, tilt curve, epoch
simulation record, note, guards, shipped claims). Findings: **10 distinct confirmed
(0 critical, 4 major, 6 minor), 2 refuted.** All confirmed findings applied in the
same build as this record.

## Verdicts

- **The PP arrival-optimum conclusion STANDS**: flat basin; crossing design default
  inside noise; epoch a cost non-driver; early branch closed; custody epoch-flat.
- **Our use of the PSI paper stands on the core claim** (PSI did not derive the
  pumped epoch — direct adversarial attack on that claim, including the p14
  "low-thrust proxy" angle, was refuted by the skeptics), **except one corroboration
  story that was a misread and is retracted** (major finding 9).

## Confirmed findings and dispositions

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 0 | major | Miss-allowance max-shave convention one-sidedly overpriced tilted epochs (the 2600-AU offset direction is free; it can buy down tilt). 73k penalty was ~25% overstated; the "±50 m/s" error line was mis-signed | `sim_pp_arrival.py aim()` now optimizes the offset direction (closed-form proxy for selection; rows remain full 3-D integrations). Re-baked: 73k **+273 → +211 m/s** (2.4 → 1.8 kg Xe), crossing **+26.7 → +33.4 m/s**, bottom 32.204 → 32.198 (still 77,500). Error budget restated as one-sided + live-page convention delta disclosed |
| 6 | major | Flyability edge misplaced: 65,000 yr flies at γ≈33–36° — the `flyable()` probe only tried γ∈{20,30,38} | `flyable()` now uses the same golden steering search as the rows. Re-baked edge: **65,039 → 64,238 yr**; the page's "65,000 unflyable" row replaced by the measured flyable row (33.71 km/s, 14.0 yr custody) |
| 7 | major | Guard 13h certified the false edge with a single γ=30 probe passing by 0.08 yr | 13h rewritten: recorded-aim row replay + two-sided edge check — earliest flyable row must replay with ≥0.5 yr custody margin; an easier-than-achievable aim 1.2 kyr below the edge must fail a golden steering sweep even at gate+0.5 yr |
| 9 | major | The "PSI's planar column bottoms at 65k — exactly where tilt-blind pricing should" corroboration treated PSI's explicitly flagged ±0.2 km/s seed-scatter outlier (23.49 @ 65k, a −0.3 discontinuity between 23.79/23.82 neighbours) as a trend minimum; the coincidence with our old 65k edge was spurious | Retracted in `docs/PP-ARRIVAL-OPTIMUM.md` §4 and `audit/psi/PP-NOTES.md`; replaced by the defensible statement: the column's trend floor is 23.74 across 56–60k, near their cruise-speed minimum — and in particular NOT at 73k |
| 1 | minor | Same PSI misread, doc-wording lens | Covered by 9 |
| 2 | minor | "At any steering angle" overstated a 3-angle computation; edge label carries shave-convention dependence | Fixed structurally by 0+6; convention row added to the error budget |
| 8 | minor | "Closed by physics" wrong mechanism — the 63–65k band is acquirable in ~16–20 yr; the edge is a 15-yr custody-gate policy label (~±1 kyr per gate choice) | Reworded on the page, note, and PP-NOTES; gate-sensitivity added to the error budget and residuals |
| 3 | minor | Above-ecliptic aims priced via an undocumented `abs(beta)` z-mirror fold | Mirror-fold paragraph added to the `scheduled_pumped_vinf_3d` docstring (exactness by z-equivariance) |
| 4 | minor | The (v∞/23.64) tilt-knot scaling has the wrong trend sign (true cost falls with v∞); up to ~20–30% overcharge at the band top — conservative, no shipped number affected | Comments corrected in pump_schedule.py / departure.py / physics.js; re-derivation at multiple v∞ anchors listed as a residual |
| 5 | minor | The >4° far-field continuation was validated by a 23-yr-custody trajectory breaking the derivation's own gate; one page line priced a declared-unflyable aim without caveat | "A-fortiori comparison bound, not a flyable budget" caveat added to `plane_tax_for`, the page, and the 58-kyr docstring mention |

## Refuted findings (2)

Both attacked non-shipped surfaces or ignored the attacked text's own caveats: a
staleness attack on a `docs/plans/` snapshot (plans are dated work-tracking records,
not published claims), and an attack alleging we ignored PSI's low-thrust
corroboration sentence (the repo's characterization was quoting PSI correctly).

## Guard tightenings applied

13h: recorded-aim replay; two-sided edge check with ≥0.5-yr custody margins and a
golden steering sweep for the negative side (no pass/fail may hinge on <0.5 yr or on
a fixed probe angle). The corrected record is the audit's input; every row-level
claim on the page traces to `docs/data/pp_arrival_sim.json`.
