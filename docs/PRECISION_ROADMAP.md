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

## Stage 1 — Adaptive timestep in the SEP power gate  *(scheduled: [#2](https://github.com/fermiexplorer/fermi/issues/2))*

**Today:** `sep_achievable_vinf` integrates with a fixed 50,000 s step (result up
to ~3% off a finer-step integration), and its mass is Euler-updated once per step
while the state is fourth-order — all four RK4 stages see the start-of-step mass
(worst case ~1% more, at high power and ~80% propellant fraction). The verdict it
produces (conservative solar saturates far below the 23.3 km/s floor) has margin
far wider than either error, so no conclusion changes — but the achievable-v∞
*values* it prints (page gate numbers, the star tables' "Min solar α" column, the
α ≈ 100 W/kg outward-spiral threshold) carry them.

**Tightened:** adaptive step `dt = min(max(600, 0.002·period), 5 days)` — the
scheme the pumping integrator already uses — with mass folded into the RK4 state
vector (5th component, ṁ = −F/vₑ), plus a step-halving convergence assertion in
`audit/calcs/audit_departure.py`.

**Re-baselines:** parity REF values for the two SEP checks; the star tables'
`amin` column; the α-threshold numbers quoted on the page/REPORT if they move.

## Stage 2 — v∞-dependent pumped-campaign pricing  *(scheduled: [#3](https://github.com/fermiexplorer/fermi/issues/3))*

**Today:** `pumped_departure_dv` prices the campaign leg as v∞ + a flat 2 km/s
tax, calibrated at the AC corridor (v∞ ≈ 23–25 km/s). The true in-plane overhead
is ~8 km/s at v∞ = 15 and ~13 km/s at v∞ = 8, so the flat tax is wrong off-corridor
— now **enforced**: the function raises below `PUMP_TAX_VINF_MIN` (20 km/s), and
off-corridor targets are priced by integrating `perihelion_pumped_vinf` directly
(as `audit/AUDIT_COMPARISON.md` §2b does for α² Lib).

**Tightened:** replace the flat tax with a calibrated overhead curve tax(v∞)
fitted against the integrator across v∞ = 8–30 km/s (or integrate on demand with
caching), removing the corridor restriction.

**Re-baselines:** pumped-budget parity checks; the two-leg budget quotes in the
page/REPORT if the in-corridor value shifts.

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

---

## Floor that is NOT worth tightening

`R_EARTH` and `R_SUN` are 4-significant-digit constants because the physical
quantities themselves are fuzzy at that level (mean vs equatorial radius; the
photosphere is ~200 km deep). They bound every LEO- and solar-radius-referenced
number to ~4 digits regardless of the arithmetic. More digits would add
precision the underlying definition does not have.
