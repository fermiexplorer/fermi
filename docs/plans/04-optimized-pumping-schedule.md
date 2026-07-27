# 04 — Optimised pumping schedule

Issue: https://github.com/fermiexplorer/fermi/issues/4
Roadmap: `docs/PRECISION_ROADMAP.md` Stage 3
Status: **SHIPPED** (build 156). Measured record: 12-yr custody optimum at the
design a₀ = Δv 23.14 km/s (bang-bang gate 25.63; PSI's published 12-yr optimum
23.97 — beaten by 3.5%); frontier ≤10 yr → 23.49, unconstrained → 22.84 @
28.5 yr; per-a₀ schedules close every bang-bang island/stall gap on the tested
grid; tax re-anchored (−0.509 at the AC anchor), default budget 34.3 → 31.8;
suite 160/160, parity 40/40, UI 82/82.

## Problem

The pumping campaign is flown by the bang-bang heuristic in
`fermi_sim.departure.perihelion_pumped_vinf`. One rewrite retires three costs:

1. **~7% Δv premium** over an optimised schedule (25.63 vs PSI's 23.97 km/s at
   the design point), almost entirely in the cruder retrograde pump-down.
2. **Non-monotonic closure** in a₀ / Isp / power-cap (islands and stall bands,
   pinned by `audit/calcs/audit_pumping.py`): fixed switching arcs whose phasing
   beats against the orbit. This is why designs must be gated by integration at
   a validated profile rather than a threshold.
3. **Per-step switch quantization** (external ledger F5l): the on/off/sign
   decision is taken once per RK4 step from start-of-step osculating elements,
   so burn-arc edges are fuzzy by O(dt). Directly measured (A/B experiment,
   per-step vs per-stage switching, `tmp/ro/f5l_repro.py`): **0.12% Δv / 0.00%
   v∞ at the design a₀** with the reach verdict unchanged; at the *bisected
   edge* a₀ = 2.24×10⁻⁴ the verdict flips (v∞ −0.14%) — i.e. the published
   edge is scheme-dependent at the ~1% level in a₀, which is precisely why
   designs are gated by integration at the validated profile, 12% above the
   edge. LOW alone; retired for free here because switching times become
   decision variables. (F5l's wording is imprecise: the thrust *direction* is
   stage-local; only the switch *state* is frozen per step.)

## Change

1. `fermi_sim/`: an optimised schedule solver (direct collocation or equivalent;
   scipy-only if possible per the dependency-light rule) producing the burn
   programme for a given (a₀, Isp, v∞ target, r_p floor, power cap). Switching
   times are decision variables.
2. Keep `perihelion_pumped_vinf` (bang-bang) unchanged as the independent
   cross-check: the audit relationship inverts — the heuristic audits the
   optimum (must never beat it; gap ≈ the known ~7%).
3. Mirror the *results* to the web (the solver itself need not run in JS —
   precompute the design-corridor table like the page's pumping table, or port
   if lightweight).
4. `audit/calcs/audit_pumping.py`: new checks — optimum ≤ bang-bang everywhere;
   monotone closure in a₀ (the islands must vanish); work-energy and mass
   closure on the optimised trajectory.

## Re-baseline (same commit — see docs/DOC_MAINTENANCE.md)

Campaign numbers move by design (~25.6 → ~24 km/s Δv class): the page pumping
table and campaign prose, REPORT/README quotes, `AUDIT_COMPARISON.md` §4 engine
column, the pumped two-leg totals (~31–34 band tightens at the bottom), the
pump-tax calibration (coordinate with issue #3 — the tax(v∞) fit should be
re-anchored to the optimised campaign), parity REFs, and the audit_pumping
non-monotone pins (they become bang-bang-only checks).

## Verification

- `run_audits.py` green at the new baseline, including the new
  optimum-vs-heuristic and monotonicity checks.
- `audit_webjs.mjs` green at re-baselined REFs.
- `ui_sliders.py` green (default campaign numbers updated in the checks).
- `pytest tests/` green.
- Cross-check the design-point optimum against PSI's published 23.97 km/s /
  12 yr schedule (should land within a few %).

## Push / merge

Branch from `main`, one commit (solver + audits + re-baselines + doc
propagation per DOC_MAINTENANCE clusters), deploy via `tools/deploy.py`,
commit+push both Pages clones, push the branch, merge to `main`, poll live,
close issue #4 with a comment linking the commit.
