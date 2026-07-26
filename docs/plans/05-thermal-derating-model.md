# 05 — Derive the perihelion power cap from a first-principles thermal model

Issue: https://github.com/fermiexplorer/fermi/issues/5
Roadmap: `docs/PRECISION_ROADMAP.md` Stage 7

## Problem

The pumping power model is `P(r) = P1 · min((1 AU/r)², power_cap)` with
`power_cap = 4.0` as an assumption parameter. Its limits are disclosed (the
page states it assumes a derating-free, Parker-class thermally-managed array
and that realistic GaAs at the 0.42 AU floor delivers nearer ~3× effective),
its feasibility margin is measured (a halved 2.0× cap still closes: +1.1 km/s,
9.6 → 18.3 yr), and its non-monotone closure pattern is audit-pinned — but the
number itself is assumed, not derived. This stage replaces the assumption with
a computed curve.

## Change

1. `fermi_sim/`: a small thermal module — equilibrium cell temperature T(r)
   from absorbed vs radiated flux (absorptivity α, emissivity ε, one/two-sided
   emission, optional off-pointing angle), then η(T) from the cell temperature
   coefficient (GaAs ~0.2%/K primary; Si ~0.45%/K as the sensitivity case),
   giving `cap_eff(r) = (1 AU/r)² · η(T(r)) / η(T_1AU)`.
2. `perihelion_pumped_vinf` consumes cap_eff(r) in place of
   `min((1 AU/r)², cap)`; the constant-cap form stays available (parameter or
   sibling function) as the independent audit comparator.
3. Mirror in `web/physics.js`; the page caveat is rewritten from "assumed 4×,
   realistically ~3×" to the computed curve and its inputs (α/ε, coefficient).
4. `audit/calcs/audit_pumping.py`: the cap-sweep check becomes a
   cap_eff-vs-constant-cap comparison (the two must bracket each other at the
   design radius); thermal-balance closure check (absorbed = radiated at T(r))
   verified against an independent hand calculation.

## Re-baseline (same commit — see docs/DOC_MAINTENANCE.md)

Campaign numbers move toward the 2×-cap bracket (expected: closure survives,
campaign between 9.6 and 18.3 yr): page pumping table + caveat + CONOPS
custody quotes, REPORT/README, AUDIT_COMPARISON §4 engine column, parity REFs
for pumped checks, audit_pumping pins. Coordinate with issue #4 — the
optimised schedule should consume cap_eff(r) directly, so land this first or
together.

## Verification

- Thermal balance closes against an independent calculation (audit check).
- `run_audits.py`, `audit_webjs.mjs`, `ui_sliders.py`, `pytest` green at the
  new baseline via `tmp/ro/verify_ui_now.py`.
- Cross-check: cap_eff(0.42 AU) lands near the page's disclosed ~3× estimate;
  a Parker-class managed-array option reproduces ~4× (the current working
  point) so the old baseline remains a selectable comparator.

## Push / merge

Branch from `main`, one commit (thermal module + integrator + mirror + audits
+ doc propagation), release via `tools/release.py` (deploy — physics.js and
index.html change), poll live, close issue #5 with a comment linking the
commit.
