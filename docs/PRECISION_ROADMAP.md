# Precision roadmap — tightening the model, stage by stage

The engine is a first-order ("Fermi estimate") model. This roadmap lists the places
where its numbers are looser than they need to be, ordered by impact, with the
tightened model each stage adopts and what it re-baselines. The policy is to
**tighten the numbers rather than merely document their looseness**; until a stage
lands, its looseness is stated here and (where possible) enforced by a runtime
guard or regression test.

Ground rules for every stage:

- `fermi_sim/` first, then the `web/physics.js` mirror, then re-run the parity
  audit (`node audit/calcs/audit_webjs.mjs`).
- Any stage that shifts published numbers re-baselines the parity reference
  values, the affected star-table columns (regenerate via
  `tools/make_starmap_data.py`), and the page/report prose **in the same commit**
  (see `docs/DOC_MAINTENANCE.md`).
- A stage is done when the full suite (`audit/calcs/run_audits.py`, parity,
  UI, pytest) is green at the new baseline.

Tracking: each scheduled stage has a GitHub issue and a `docs/plans/NN-slug.md`
plan (NN = issue number). Unscheduled stages get theirs when picked up.

---

## Stage 1 — Adaptive timestep in the SEP power gate  *(shipped: [#2](https://github.com/fermiexplorer/fermi/issues/2), build 154)*

`sep_achievable_vinf` integrates with an adaptive step (`dt = min(max(600,
0.002·period_r), 5 days)`, r-based Kepler period) and the mass folded into the
RK4 state vector (5th component, ṁ = −F/vₑ); step-halving convergence is
asserted in `audit/calcs/audit_departure.py` (< 0.5%, measured 1.4×10⁻⁶–1.9×10⁻³).
Validation: the integrator matches Fable's independent adaptive RK45 to
0.001–0.09%. The pumping integrator was measured and deliberately left as-is
(mass coupling moves its campaign only 0.06% v∞ / 0.10% Δv).

## Stage 2 — v∞-dependent pumped-campaign pricing  *(shipped: [#3](https://github.com/fermiexplorer/fermi/issues/3))*

`pumped_departure_dv` prices the campaign leg as v∞ + `pump_tax_for(v∞)` — a
piecewise-linear table swept from the campaign integrator at the design a₀
(13.5 km/s at v∞ = 8 falling to 0 by ~28; validity [8, 29] km/s, refuses below;
half-grid interpolation error ≤ 79 m/s, suite-pinned < 0.3 km/s at off-knot
targets). The 23.64 km/s knot is pinned to the shipped 2.0 km/s calibration, so
every published AC budget is unchanged. Residual: the table is swept at the
design a₀ only (~±0.4 km/s a₀-dependence) — Stage 3 (#4, shipped) re-anchored
the pricing to the optimised schedule and kept this table as the cross-check.

## Stage 3 — Optimised pumping schedule  *(shipped: [#4](https://github.com/fermiexplorer/fermi/issues/4))*

`fermi_sim/pump_schedule.py` integrates the campaign under a 4-parameter
switching schedule (retro/prograde arc half-widths, escape energy guard,
perihelion latch) with **bisection-located switch events** (~1e-3 dt — retiring
the F5l arc-edge quantization on the flown path), optimised per a₀ by
Nelder-Mead multi-start (`tools/optimize_pump_schedule.py`), every baked number
re-integrated at full engine resolution. Results: the anchored 12-yr-custody
optimum at the design a₀ costs **Δv 23.14 km/s (bang-bang gate: 25.63; PSI's
published 12-yr optimum: 23.97 — beaten by 3.5%)**; the unconstrained frontier
reaches 22.84 at 28.5 yr; per-a₀ schedules **close every bang-bang island/stall
gap** on the tested grid (1.6/1.9/2.24/2.5/3.0×10⁻⁴ all REACH — the
non-monotonicity was a fixed-arc phasing artifact). The calculator flies and
prices the anchored optimised campaign (tax at the AC anchor: **−0.509 km/s**,
Oberth-negative; two-leg default budget 34.3 → 31.8 km/s); the bang-bang
integrator stays as the feasibility gate and independent cross-check, and
`audit/calcs/audit_pumping.py` replays the anchor, the grid closures, the
energy bookkeeping, and optimum-beats-gate. Residual: the shipped tax/campaign
tables remain design-a₀-anchored (Stage 2's residual, unchanged in kind).

## Stage 4 — 3-D pumping campaign  *(tilt pricing landed — issue #9)*

**Today:** the out-of-plane aim is priced by a DERIVED 3-D steering curve: the
campaign integrator generalised to 3-D (`pump_schedule.scheduled_pumped_vinf_3d` —
thrust steered out of plane on the hyperbolic leg, asymptote-latitude feedback,
planar-embedding exact at β = 0), per-β steering optimised and baked
(`tools/derive_plane_tax.py` → `PLANE_TAX_THERMAL_TABLE`). The curve is
~quadratic near zero (~95 m/s·β²) and costs **0.51 km/s at the 2.48°
direct-optimum aim** — half the previous v∞·|sin β| bolt-on; the cap-model point
(0.61) sits 5% from PSI's independently measured 0.58. Consequences: default
two-leg budget 33.1 → **32.6 km/s**; the pumped fuel optimum moves off the
ecliptic crossing into a **shallow basin bottoming ~77,500 yr** (crossing +33 m/s —
still the rule of thumb); the early-arrival branch stays ~3 km/s out.
`audit_pumping` 13g: planar embedding, independent own-code 3-D re-integration,
knot replay + step convergence, the ≤ v∞·|sin β| bound, and the basin guard.

**Residual:** tilt is bought on the hyperbolic leg only (no bound-phase plane
steering — relevant above the 4° validity edge, where the far-field marginal
continuation prices the aim); the curve is derived at the design a₀ and the
23.64 km/s anchor (v∞-scaled, like the tax tables).

## Stage 5 — Finite-burn / higher-T/W departure  *(unscheduled; extends plan 01)*

**Today:** the Earth-escape leg is the constant-tangential spiral (closed-form
fit, validated to ~0.5 m/s against integration); perigee-biased phasing was shown
time-divergent at sub-milli-g thrust.

**Tightened:** a full finite-burn solution for a higher-T/W stage, pricing the
phased-departure option the report currently lists as future work.

## Stage 6 — Ephemeris beyond linear motion  *(unscheduled)*

**Today:** every star (including AC) moves on a straight line at constant
velocity. The extrapolation error is *second-order* — the measured 6-D velocity
already contains all first-order relative motion, so the residual is
½·a_rel·t², where a_rel is the differential galactic tide (~Ω²·d ≈ 2.6×10⁻¹⁴
m/s² in-plane, ~9× that for the vertical oscillation) plus the mutual Sun↔AC
attraction (≈ 2.4×10⁻¹³ m/s² — the largest single term). Quantified: **~6–10 AU
at the 80 kyr AC mission horizon** (0.2–0.4% of the 2600 AU miss allowance) —
negligible; **~1000–2600 AU by the 1–1.3 Myr horizons** of the beyond-AC tables
(e.g. the Gliese 710 epoch) — comparable to the allowance itself, which is what
makes this stage worth doing.

**Tightened:** epicyclic/galactic-potential propagation (plus point-mass mutual
attraction for the nearest systems) for the long-horizon star tables;
AC-mission numbers are unaffected.

## Stage 7 — Thermal derating derived, not assumed  *(shipped: [#5](https://github.com/fermiexplorer/fermi/issues/5))*

`fermi_sim/thermal.py` derives the perihelion power multiple from a
first-principles flat-panel energy balance — (α − η(T))·S(r) = (εf+εb)·σ·T⁴
self-consistently with η(T) linear in the cell coefficient — giving
**cap_eff(0.42 AU) = 3.54** (T = 492 K, −186 K vs 1 AU; GaAs 0.2 %/K, α 0.92,
ε 0.85/face), which both campaign integrators consume as `power_model="thermal"`
(the shipped default; a fixed 1024-point log-radius table mirrored in JS keeps
parity to ~1e-11). The suite verifies the balance by an INDEPENDENT bisection
solve. Results: silicon (0.45 %/K) **collapses to 0.08×** at the floor — the
campaign is cell-technology-critical; both fixed-geometry schedules STRAND at
the design a₀ under the derived curve (bang-bang reaches only 20.1 km/s), and
per-a₀ re-optimisation closes the design point and the whole tested grid again
(`OPTIMIZED_SCHEDULES_THERMAL`); the flown 12-yr anchored campaign costs
**24.44 km/s** (+1.3 vs the idealised 4× cap — inside the previously measured
2×-cap sensitivity bracket), tax anchor +0.785 km/s, default two-leg budget
31.8 → **33.1 km/s**, implied vehicle α 15.2 W/kg (inside the published 15–21
band). The constant-cap form stays as `power_model="cap"` — the audit
comparator and the PSI-comparable working point. Residual: the thermo-optical
inputs are representative published values, not a qualified-hardware model
(disclosed in `audit/EXTERNAL_AUDIT_SCOPE.md` §7).

---

## Floor that is NOT worth tightening

`R_EARTH` and `R_SUN` are 4-significant-digit constants because the physical
quantities themselves are fuzzy at that level (mean vs equatorial radius; the
photosphere is ~200 km deep). They bound every LEO- and solar-radius-referenced
number to ~4 digits regardless of the arithmetic. More digits would add
precision the underlying definition does not have.
