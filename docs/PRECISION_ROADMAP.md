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
design a₀ only (~±0.4 km/s a₀-dependence) — re-anchored by Stage 3 (#4).

## Stage 3 — Optimised pumping schedule  *(scheduled: [#4](https://github.com/fermiexplorer/fermi/issues/4))*

**Today:** the bang-bang policy costs ~7% more Δv than PSI's optimised schedule
(25.6 vs 24.0 km/s) and is non-monotonic in a₀/Isp/power-cap (islands and stall
bands, pinned by `audit/calcs/audit_pumping.py`). A third, smaller cost rides
the same heuristic: the bang-bang on/off/sign decision is taken once per RK4
step, so burn-arc edges are quantized by O(dt) — directly measured at **0.12%
Δv at the design a₀** (verdict unchanged; a per-stage-switching variant flips
the verdict only at the bisected working-region edge, where any perturbation
does), and bounded < 0.5% by the step-convergence audit check (external ledger
F5l).

**Tightened:** a trajectory-optimised burn schedule (direct collocation or
equivalent) with switching times as decision variables — removing the ~7%
premium, the phasing gaps, and the arc-edge quantization in one rewrite; the
bang-bang integrator stays as the independent audit cross-check.

## Stage 4 — 3-D pumping campaign  *(unscheduled)*

**Today:** the campaign is integrated in-plane; the out-of-plane aim is charged
separately as a first-order plane change v∞·|sin β|.

**Tightened:** integrate the campaign in 3-D with the aim's true inclination, so
the plane change is bought where it is cheapest instead of priced as a bolt-on.

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

## Stage 7 — Thermal derating derived, not assumed  *(scheduled: [#5](https://github.com/fermiexplorer/fermi/issues/5))*

**Today:** the pumping power model caps perihelion concentration at an assumed
`power_cap = 4.0` — disclosed as a derating-free, Parker-class-managed working
point (realistic GaAs at the 0.42 AU floor delivers nearer ~3× effective), with
a measured factor-of-two feasibility margin (a 2.0× cap still closes: +1.1 km/s,
9.6 → 18.3 yr) and the non-monotone closure pattern pinned in the audit suite.
The consequence of the thermal limit is modelled; the limit itself is not.

**Tightened:** a first-principles perihelion-array energy balance — T(r) from
absorbed vs radiated flux (α/ε, off-pointing as the control), η(T) from the
cell coefficient — yielding a continuous `cap_eff(r)` that the campaign
integrator consumes in place of `min((1 AU/r)², cap)`; the constant-cap form
stays as the audit comparator. Coordinate with Stage 3 (#4).

---

## Floor that is NOT worth tightening

`R_EARTH` and `R_SUN` are 4-significant-digit constants because the physical
quantities themselves are fuzzy at that level (mean vs equatorial radius; the
photosphere is ~200 km deep). They bound every LEO- and solar-radius-referenced
number to ~4 digits regardless of the arithmetic. More digits would add
precision the underlying definition does not have.
