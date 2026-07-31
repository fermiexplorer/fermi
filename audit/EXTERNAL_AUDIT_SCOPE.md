# Guide for an Independent Auditor (Human or AI) — Scope & Files

A guide for any **independent reviewer** — human or AI — auditing the **physics
engine and its conclusions**. Human and AI reviewers should check the same
things: the same files, the same claims, the same independence bar. It tells you
which files carry the load-bearing math, what each one claims, what to check,
and where the known soft spots are.

**AI reviewers:** the adversarial prompt set is
[`AUDIT_PROMPTS.md`](AUDIT_PROMPTS.md) (§1–10 geometry/departure, §11–12
pumping/synchrotron); the existing AI reviews and their results are under
`audit/codex|grok|gemini|fable/`. Follow this scope document for *what* to
review, the prompt set for *how* to run it, and commit conclusions plus a
`*_results.json` under a new `audit/<name>/` per
[`README.md`](README.md#adding-a-new-independent-audit).

**Browser / UI code is deliberately out of scope for this pass** (see
[§2](#2-out-of-scope)). This document covers the Python engine, the integrated
analysis, the independent-audit corpus, and the tender report.

---

## 1. What you are auditing

Fermi is a first-order ("Fermi estimate") feasibility model for an interstellar
precursor mission: deliver ~1 kg to within 2600 AU of Alpha Centauri (99% of the
way) inside 100,000 yr, from LEO, on solar-electric ion propulsion. The engine
sizes the vehicle, finds the minimum departure Δv and optimal arrival time, and
compares power architectures (solar / nuclear / fuel cell) and trajectories
(direct spiral, perihelion pumping, solar-Oberth, gravity assist, and an
external "synchrotron" accelerator).

Your job is to independently judge whether the **headline numbers**
([§6](#6-claims-to-validate)) follow from sound physics and correct code —
especially the novel/contested ones (perihelion pumping, the two-leg departure
budget). Treat every result as unproven until you have reproduced it by a
**different method** than the engine uses.

**Two audit modes — declare yours before starting.** This guide serves two
different reviews, and one section reads differently in each:

- **Conclusions audit** — "is the answer right?" The scope, claims table, and
  the materiality claims in [§8](#8-known-numerical-limitations-of-the-implementation)
  are all working material: test the claims, rule on each.
- **Defect audit** — "where can this code fail?" Then the project's materiality
  opinions are **not your input**: disregard the "materiality claim" halves of
  §8 entirely and treat its items as open defects alongside anything you find.
  A defect is a finding whether or not it moves a headline number.

---

## 2. Out of scope

Do **not** spend audit budget on the browser/UI layer:

- `index.html` (the calculator page, animations, 3D views)
- `web/physics.js`, `web/stars.js`, `web/three.min.js` (the browser port + assets)
- `audit/calcs/audit_webjs.mjs` (JS↔Python parity — only relevant if you review
  the port, which you are not)
- `audit/calcs/ui_sliders.py`, `audit/calcs/ui_playwright.py` (Playwright UI tests)

The web calculator is a **port** of the Python engine and is verified against it
separately. If the Python engine is correct, the port is covered by its own
parity suite. Audit the engine.

---

## 3. Ground rules

1. **`fermi_sim/` is the source of truth.** Everything else (the page, the port,
   the report) derives from it. Audit the Python.
2. **Independence is the whole point.** The existing suite in `audit/calcs/`
   checks the math by *different* methods — astropy ephemerides, conservation
   laws, brute-force / scipy optimisers, independent re-integration with a
   different step schedule — never by calling the engine and comparing it to
   itself. Hold your own review to the same bar: re-derive, don't re-run.
3. **This is a Fermi estimate, not a nav tool.** First-order models, 2D planar
   sub-simulations, and ~few-percent tolerances are by design. Judge whether the
   approximations are *disclosed and defensible*, not whether they are
   flight-grade. [§7](#7-known-assumptions--limitations) lists them.

---

## 4. Repository map (in-scope files)

```
fermi_sim/               PYTHON ENGINE — source of truth  (~1160 LOC)
  constants.py    (39)   physical constants (SI)
  astro.py       (100)   AC ephemeris; equatorial->ecliptic; closest approach
  intercept.py   (106)   aim geometry; tangential min; ecliptic crossing
  trajectory.py   (80)   Jupiter assist; solar-Oberth; time-to-AC
  spacecraft.py  (238)   rocket eq; minimal dry mass; power/array sizing; fuel cell
  departure.py   (~650)  ** the heavy one ** — see §5
  pump_schedule.py (~340) optimised pumping schedules + baked campaign/tax tables — see §5
  thermal.py     (~150)  DERIVED perihelion power curve (array energy balance) — see §5
run_analysis.py  (~360)  integrated report; produces the shipped headline numbers

audit/calcs/             INDEPENDENT SUITE (Python)  — 190+ checks, run_audits.py
  audit_ephemeris.py     vs astropy
  audit_intercept.py     geometry
  audit_departure.py     spiral / escape / departure budgets
  audit_propulsion.py    rocket eq / energy
  audit_fuelcell.py      fuel-cell energy wall
  audit_solar.py         array sizing
  audit_pumping.py       ** perihelion pumping ** (independent re-integration)
  audit_synchrotron.py   external-accelerator "lasso"
  audit_stars.py         nearby-star data invariants
  audit_docs.py          cross-file numeric consistency
  _util.py, run_audits.py   harness

audit/                   CROSS-VALIDATION & PARALLEL REVIEWS (read, don't trust blindly)
  README.md              master audit index
  AUDIT_COMPARISON.md    quantity-by-quantity: engine vs PSI vs GMAT vs 4 AI re-impls
  AUDIT_PROMPTS.md       the adversarial prompts used
  gmat/                  NASA GMAT propagator cross-validation (departure energetics)
  stk/                   STK cross-validation
  psi/                   external PSI assessments (final July 2026 + working draft) + our notes
  codex/ grok/ gemini/ fable/   parallel independent-model re-implementations

tests/test_smoke.py      pytest regression (8 tests)
docs/REPORT.md           tender feasibility report (prose conclusions)
```

---

## 5. Tier-1 files — review in depth

### `fermi_sim/departure.py` (598 LOC) — HIGHEST PRIORITY
This is where the novel and contested physics lives. Functions to scrutinise:

- **`perihelion_pumped_vinf`** — the mechanism validator. A multi-revolution
  bang-bang escape: retrograde arcs drop perihelion to a 0.42 AU thermal floor,
  then prograde perihelion burns staircase the orbit energy. Power model
  selectable: the legacy `"cap"` step (min((1 AU/r)², 4) — the PSI-comparable
  cross-check) or the derived `"thermal"` curve. **Check:** energy/work-energy
  closure; the power law is never exceeded; the thermal floor is respected;
  the reported v∞/Δv/revs at the design point (a₀=2.5e-4, Isp=2800, cap
  model). **Non-obvious property to verify yourself:** fixed-geometry closure
  is **non-monotonic** — in a₀, in Isp, *and* in the power model. At the 4×
  cap there are success "islands" below and stall "bands" above the design
  point (reaches at cap 2.0/2.5/3.5/4.0×, strands at 1.5/3.0/3.25×), and
  under the derived thermal curve the fixed geometries strand at the design
  a₀ itself (bang-bang reaches only ~20 km/s there). Confirm this is real
  schedule-phasing physics, not a bug.
- **`fermi_sim/thermal.py`** — the DERIVED perihelion power curve (issue #5):
  flat sun-normal panel, two-sided emission, extracted electricity removed
  from the heat load, self-consistent η(T): cap_eff(r) = (1/r²)·η(T(r))/η(T₁ₐᵤ)
  — **3.54× at the 0.42 AU floor** (T = 492 K), replacing the previously
  assumed 4× step. **Check:** the energy balance against your own solve (the
  suite uses an independent bisection); the thermo-optical inputs (α 0.92,
  ε 0.85/face, GaAs 0.2 %/K) against published cell data; the Si sensitivity
  case (0.45 %/K ⇒ cap_eff collapses to 0.08× — the campaign is
  cell-technology-critical); the fixed-grid interpolation the integrators
  consume vs the exact function.
- **`pumped_departure_dv`** — the two-leg budget: √(μ⊕/a) escape + v∞ +
  a **DERIVED 3-D plane tax** (`plane_tax_for`, issue #9: the 3-D campaign
  integrator `scheduled_pumped_vinf_3d` steers the tilt on the hyperbolic leg;
  ~quadratic near β = 0, 512 m/s at the 2.48°/23.64 km/s knot vs the 1023 m/s
  far-field bound v∞·|sinβ| that upper-bounds it everywhere; validity to 4°,
  far-field marginal slope beyond; audit_pumping 13g re-derives the cap-model
  point independently — 610 own-code vs 606 engine vs PSI's measured 578) + a
  **v∞-dependent pump tax** (`pump_tax_for`, two
  schedules): the default `"optimized"` table is swept from the **anchored
  optimised campaign** (10.6 km/s at v∞ = 8, **−0.509** at the pinned
  23.64 km/s AC anchor — negative: the Oberth-efficient campaign spends less Δv
  than the v∞ it buys; validity [8, 26] km/s, refuses outside); the
  `"bangbang"` table is the cross-check (2.0 at the anchor, validity [8, 29]).
  **Check:** each table against your own integration at off-knot targets (the
  suite pins the bang-bang < 0.3 km/s and replays the optimised anchor); the
  sign of the optimised anchor; the a₀-dependence caveat in
  [§8](#8-known-numerical-limitations-of-the-implementation).
- **`fermi_sim/pump_schedule.py`** — the optimised-campaign integrator (issue
  #4): a 4-parameter switching schedule (retro/prograde arc half-widths, escape
  guard, perihelion latch) with **bisection-located switch events**, 5-state
  mass-coupled RK4, baked per-a₀ optima (`OPTIMIZED_SCHEDULES`), and the
  anchored campaign/tax tables (`OPT_CAMPAIGN_TABLE`, `TAX_OPT_TABLE`).
  **Check:** replay any baked entry through `scheduled_pumped_vinf` and confirm
  the tuple reproduces; energy bookkeeping via `return_diag` (thrust work ==
  specific-energy gain); that the optimum never loses to the bang-bang gate;
  the headline **23.14 km/s @ 12.0 yr vs PSI's published 23.97 @ 12 yr**.
- **`sep_achievable_vinf`** — the conservative solar-power-fade feasibility gate
  (1/r² thrust, adaptive-step mass-coupled RK4; step-halving convergence is
  suite-pinned < 0.5%, and the integrator matches an independent adaptive RK45
  to 0.001–0.09%). **Check:** the convergence claims yourself; whether the
  saturation verdict is robust near the threshold. This gate decides "does pure
  solar close?"
- **`spiral_escape_dv`**, **`lowthrust_departure_dv`** (closed-form fit),
  **`earth_escape_revs`**, **`impulsive_dv_from_leo`**, **`synchrotron_escape`**.
  **Check:** the closed-form departure fit vs a real integration; the C3=0
  Earth-escape time (uses ~0.93·v_circ, not the r→∞ asymptote); the synchrotron
  "escape terminates recirculation" rule.

### `fermi_sim/spacecraft.py` (238 LOC)
Rocket equation, `minimal_dry_mass` (the no-margin mass closure — verify the
convergence denominator `D>0` and the derived-mass algebra), array sizing, the
fuel-cell energy wall, golden-section Isp optimisation. **Check:** mass closure
matches `m/m0 = exp(-Δv/vₑ)`; the fuel-cell reactant mass against first
principles.

### `run_analysis.py` (345 LOC)
The integrated report that emits the shipped headline numbers. **Check:** every
number it prints traces to an engine call, and matches `docs/REPORT.md` and
`AUDIT_COMPARISON.md`.

---

## 6. Claims to validate

Reproduce these independently (astropy, hand calculation, your own integrator):

| Quantity | Engine value |
|---|---|
| AC distance / space speed | 4.344 ly / 32.30 km/s |
| Closest approach | ~27,960 yr at ~3.13 ly |
| Cruise floor (tangential min v∞) | 23.3 km/s (23.272) |
| Ecliptic crossing arrival | ~79,252 yr |
| Min-Δv arrival | ~72,800 yr |
| Low-thrust spiral departure Δv (AC-class) | ~25–26 km/s |
| Derived thermal power curve | cap_eff(0.42 AU) = 3.54, T(0.42 AU) = 492 K; Si case collapses to 0.08× |
| Pumped two-leg budget (LEO) | ~33 km/s (anchored optimised schedule, derived thermal curve; ~31.8 at the idealised 4× cap) |
| GTO-start Earth-escape leg | ~4.0 km/s |
| Pumping @ a₀=2.5e-4, Isp=2800 (bang-bang @ 4× — cross-check) | v∞ 23.66, Δv 25.6, 9.6 yr, ~4.9 revs |
| Pumping @ a₀=2.5e-4 (anchored optimised @ 4× — PSI-comparable) | v∞ 23.64, Δv 23.14, 12.0 yr, ~5.9 revs (PSI's published 12-yr optimum: 23.97) |
| Pumping @ a₀=2.5e-4 (**flown default**: anchored optimised, thermal) | v∞ 23.65, **Δv 24.44**, 12.0 yr, ~7.9 revs |
| Pumping contiguous working region (bang-bang @ 4×) | a₀ ≳ 2.24×10⁻⁴ m/s² (non-monotone below; per-a₀ optimised schedules close every tested gap, under both power models) |
| Whole-vehicle α to close pumping | ~15–21 W/kg |
| Whole-vehicle α to close outward spiral | ~100 W/kg |
| Synchrotron @ 10 R☉, 5 km/s | 12 kicks → leaves at ~33 km/s |

---

## 7. Known assumptions & limitations

**How §7 and §8 differ:** §7 lists **modelling choices** — simplifications the
model makes *on purpose*; the audit question is whether each is disclosed and
reasonable for a first-order estimate. §8 lists **implementation shortfalls** —
places where the code computes its own model less accurately than it could; each
has a tracked fix. If a §7 assumption turns out unreasonable, the *model* is
wrong; if a §8 claim fails, the *code* is wrong.

For each row: what is assumed, where the assumption bites, and the disclosed
error it introduces. Judge disclosure and reasonableness; if you find an
undisclosed assumption, that is a finding.

| Assumption | Where it bites | Disclosed error / scope |
|---|---|---|
| AC (and every star) moves in a **straight line at constant velocity** | all intercept geometry | error is *second-order* (the measured 6-D velocity absorbs all first-order motion): ½·a_rel·t² with a_rel = differential galactic tide + mutual Sun↔AC gravity (the larger term) ≈ **6–10 AU at 80 kyr** — 0.2–0.4% of the 2600 AU allowance; grows to ~1000–2600 AU by the 1–1.3 Myr beyond-AC horizons (roadmap Stage 6) |
| **Two-body dynamics** (Sun + one body) | all trajectory integrators | no planetary perturbations or galactic tides |
| Campaign integrators are **2-D in-plane** (except the 3-D tilt-pricing integrator) | pumping + SEP gate | out-of-plane aim charged by the DERIVED 3-D steering curve (`plane_tax_for`; hyperbolic-leg steering only, 4° validity, far-field marginal slope beyond — roadmap Stage 4 residual) |
| Solar flux = **1/r² exactly**; perihelion multiple = cap_eff(r) from a flat-panel energy balance (issue #5) | pumping power model | the derate curve is DERIVED, but its thermo-optical inputs (α 0.92, ε 0.85/face, GaAs 0.2 %/K, sun-normal, no active cooling) are representative published values, not a qualified-hardware model; the old 4× step survives only as the audit comparator |
| **Constant thruster efficiency** (η ≈ 0.55–0.6), continuous mass flow | all propulsion sizing | no throttle/efficiency curves |
| **Bang-bang pumping policy** | pumping Δv, campaign shape | ~7% above the optimal schedule; source of the non-monotone islands (roadmap Stage 3) |
| **No relativity** | everywhere | v ≪ c throughout; exact for this regime |
| **4-digit `R_EARTH`, `R_SUN`** | every LEO- or solar-radius-referenced number | hard ~4-digit precision floor — the physical definitions are fuzzy at that level, so this is not worth tightening (see the roadmap's closing note) |

---

## 8. Known numerical limitations of the implementation

Places where the code computes its own model less accurately than it could
(contrast §7, which lists the model's *deliberate* simplifications). Each entry
has two labelled halves:

- ***Defect*** — a bare, falsifiable statement of what the code does wrong and
  what it propagates to. This half is fact; audit modes do not change it.
- ***Materiality claim (test this)*** — the project's argument for why the
  defect does not change a shipped conclusion. **Conclusions audit:** rule on
  each claim in your deliverable ([§10](#10-suggested-deliverable)) —
  MATERIAL / CONFIRMED-IMMATERIAL / UNTESTED; do not inherit it.
  **Defect audit:** ignore this half entirely — the defect is an open finding
  regardless of materiality (see the audit-modes note in
  [§1](#1-what-you-are-auditing)).

Every entry has a tracked fix; the staged plan is
[`docs/PRECISION_ROADMAP.md`](../docs/PRECISION_ROADMAP.md).

- **The pump-tax tables are swept at the design a₀ only.**
  *Defect:* both `pump_tax_for` tables (the anchored-optimised default and the
  bang-bang cross-check) are integrated at a₀ = 2.5×10⁻⁴; the true overhead is
  a₀-dependent (bang-bang, measured at the AC target: 1.96 km/s at the design
  a₀ vs 2.39 km/s at 5×10⁻⁴ — ~±0.4 km/s across the flyable band), so budgets
  for vehicles flying a different effective a₀ carry that approximation.
  *Materiality claim (test this):* the calculator throttles every stronger
  vehicle to the design a₀ (the profile the tables match), and weaker vehicles
  are gated by direct integration before any budget is shown; ±0.4 km/s is ~1%
  of the two-leg total. (Per-a₀ optimised schedules exist for a 5-point grid —
  `OPTIMIZED_SCHEDULES` — but the shipped tax/campaign tables are the design-a₀
  anchored ones.)
- **Baked campaign/tax tables carry the engine dt's first-order truncation.**
  *Defect:* the shipped `TAX_OPT[_THERMAL]_TABLE` / `OPT_CAMPAIGN[_THERMAL]_TABLE`
  knots are integrated at the engine dt convention (min(max(600 s,
  0.002·period), 5 d)) with per-step switching in `campaign_overhead_curve`;
  dt-refined runs converge ~8–35 m/s BELOW the shipped overhead values at the
  top of the aim range (thermal anchor ships +785.3 m/s vs ~764 converged) and
  ~12 m/s above at low targets in the cap table.
  *Materiality claim (test this):* the bias is ≤0.11% of any two-leg budget,
  errs conservative at the AC anchor, and every prose surface quotes the tax
  to 0.1 km/s, which absorbs it; the audit suite replays the knots at the same
  convention, so they are internally consistent and tamper-guarded.
- **Per-step bang-bang switch quantization in `perihelion_pumped_vinf`.**
  *Defect:* in the bang-bang GATE, the burn on/off/sign decision is taken once
  per RK4 step from start-of-step osculating elements, so burn-arc edges are
  fuzzy by O(dt).
  *Materiality claim (test this):* directly measured by a per-stage-switching
  A/B — 0.12% Δv / 0.00% v∞ at the design point, verdict unchanged; the verdict
  flips only at the bisected working-region edge, where any perturbation flips
  it. The flown default campaign does not carry this defect: the optimised path
  (`pump_schedule.scheduled_pumped_vinf`,
  [issue #4](https://github.com/fermiexplorer/fermi/issues/4)) locates every
  switch boundary by bisection to ~1e-3 dt.

The independent suite has a further 190+ assertions; a passing run is **not** a
substitute for your own derivation of the claims in [§6](#6-claims-to-validate).

---

## 9. How to run what exists

```bash
python3 -m venv .venv
.venv/bin/pip install numpy scipy astropy pytest

.venv/bin/python run_analysis.py              # the integrated analysis (headline numbers)
.venv/bin/pytest tests/                        # smoke/regression (8 tests)
.venv/bin/python audit/calcs/run_audits.py     # independent suite (190+ checks)
```

(The `audit_webjs.mjs` parity check and the `ui_*.py` Playwright tests are the
browser layer — out of scope here.)

---

## 10. Suggested deliverable

For each claim in [§6](#6-claims-to-validate) and each Tier-1 function in
[§5](#5-tier-1-files--review-in-depth): **CONFIRMED / DISPUTED / NEEDS-INFO**,
with the *independent method* you used (not "re-ran the engine") and the numbers
you got. Flag any assumption in [§7](#7-known-assumptions--limitations) you find
undisclosed or indefensible, and any new defect with a concrete failing input.
