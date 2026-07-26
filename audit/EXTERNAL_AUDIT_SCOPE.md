# External Audit — Scope & File Guide

A guide for a third-party reviewer auditing the **physics engine and its
conclusions**. It tells you which files carry the load-bearing math, what each
one claims, what to check, and where the known soft spots are.

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
  departure.py   (598)   ** the heavy one ** — see §5
run_analysis.py  (345)   integrated report; produces the shipped headline numbers

audit/calcs/             INDEPENDENT SUITE (Python)  — ~139 checks, run_audits.py
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
  psi/                   external assessment (PSI-TR-2026-0714) + our notes
  codex/ grok/ gemini/ fable/   parallel independent-model re-implementations

tests/test_smoke.py      pytest regression (8 tests)
docs/REPORT.md           tender feasibility report (prose conclusions)
```

---

## 5. Tier-1 files — review in depth

### `fermi_sim/departure.py` (598 LOC) — HIGHEST PRIORITY
This is where the novel and contested physics lives. Functions to scrutinise:

- **`perihelion_pumped_vinf`** — the headline result. A multi-revolution
  bang-bang escape: retrograde arcs drop perihelion to a 0.42 AU thermal floor,
  then prograde perihelion burns (power capped at 4× the 1-AU rating) staircase
  the orbit energy. **Check:** energy/work-energy closure; that the 4× cap is
  never exceeded; the thermal floor is respected; the reported v∞/Δv/revs at the
  design point (a₀=2.5e-4, Isp=2800). **Non-obvious property to verify
  yourself:** the closure is **non-monotonic** — in a₀, in Isp, *and* in the
  power cap. There are success "islands" below and stall "bands" above the
  design point (e.g. reaches at cap 2.0/2.5/3.5/4.0×, strands at 1.5/3.0/3.25×).
  Confirm this is real physics of the bang-bang schedule, not a bug.
- **`pumped_departure_dv`** — the two-leg budget: √(μ⊕/a) escape + v∞ +
  v∞·|sinβ| plane change + a flat **2 km/s "pump tax."** **Check:** the flat tax
  is calibrated *only* near the AC corridor (v∞≈23–25 km/s); it under-prices
  low-v∞ targets. Confirm shipped code never evaluates it outside that corridor
  (see the docstring caveat).
- **`sep_achievable_vinf`** — the conservative solar-power-fade feasibility gate
  (1/r² thrust, RK4). **Check:** the fixed 50,000 s timestep (see
  [§8](#8-known-open--declined-items)); whether the saturation verdict is robust
  to step size. This gate decides "does pure solar close?"
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
| Pumped two-leg budget (LEO) | ~31–34 km/s (bang-bang) |
| GTO-start Earth-escape leg | ~4.0 km/s |
| Pumping @ a₀=2.5e-4, Isp=2800 | v∞ 23.66, Δv 25.6, 9.6 yr, ~4.9 revs |
| Pumping contiguous working region | a₀ ≳ 2.24×10⁻⁴ m/s² (non-monotone below) |
| Whole-vehicle α to close pumping | ~15–21 W/kg |
| Whole-vehicle α to close outward spiral | ~100 W/kg |
| Synchrotron @ 10 R☉, 5 km/s | 12 kicks → leaves at ~33 km/s |

---

## 7. Known assumptions & limitations

These are intended simplifications. Judge whether each is *disclosed and
reasonable* for a first-order estimate:

- Alpha Centauri moves in a **straight line at constant velocity** (neglects
  galactic curvature; valid over the ~80 kyr window, degrades far beyond it).
- **Two-body dynamics** (Sun + one body); no planetary perturbations or galactic
  tides in the trajectory integrators.
- The pumping and SEP-gate integrators are **2D planar** (in-plane); the
  out-of-plane aim is charged separately as a first-order plane change.
- Solar power follows **1/r² exactly**; the 4× perihelion power cap is a thermal
  modelling assumption (a real hot array derates toward ~3×).
- Constant thruster efficiency (η≈0.55–0.6); continuous mass flow.
- The bang-bang pumping policy is **~7% off the optimal schedule** on Δv
  (documented); an optimised schedule removes the non-monotone gaps.
- No relativistic effects (v ≪ c throughout).
- **Precision floor:** `R_EARTH` and `R_SUN` are 4-significant-digit constants,
  so all LEO/solar-surface-referenced results are ~4-digit regardless of the
  floating-point arithmetic. The integrators are far more precise than the
  constants.

---

## 8. Known open / declined items (full disclosure)

We have already identified these; they are documented so you can judge them
independently rather than "discover" them. Each was declined as negligible or
inert for a Fermi estimate — **challenge that judgement if you disagree.**

- **Catastrophic cancellation, `departure.py:49`** (`v_inf_earth_required`, law
  of cosines): loses ~1–2 of ~15 double-precision digits. Declined (sub-
  precision, and it feeds the parity-mirrored path). A half-angle rewrite is the
  standard fix if you consider it warranted.
- **Cancellation, `trajectory.py`** (`solar_oberth_vinf`, `v_after²−v_esc²`):
  `max(...,0)` guard present; digits lost only for tiny burns the tool never
  uses. Declined.
- **Fixed 50,000 s timestep in `sep_achievable_vinf`**: ~3% vs a finer step. The
  solar-saturation verdict has wide margin (solar saturates far below the floor),
  so no verdict flips — but confirm that for yourself near the threshold.
- **Python-side input validation** on `perihelion_pumped_vinf` / others: the
  engine's callers are controlled, so non-finite/degenerate inputs are not
  guarded at the Python boundary (the browser port is guarded separately). If you
  intend the engine to be a reusable library, this is worth flagging.
- **Flat 2 km/s pump tax** in `pumped_departure_dv`: exact only near the AC
  corridor; under-prices low-v∞ targets by ~10 km/s. Valid only for the AC-class
  budgets the code actually evaluates.

The independent suite has a further ~139 assertions; a passing run is **not** a
substitute for your own derivation of the claims in [§6](#6-claims-to-validate).

---

## 9. How to run what exists

```bash
python3 -m venv .venv
.venv/bin/pip install numpy scipy astropy pytest

.venv/bin/python run_analysis.py              # the integrated analysis (headline numbers)
.venv/bin/pytest tests/                        # smoke/regression (8 tests)
.venv/bin/python audit/calcs/run_audits.py     # independent suite (~139 checks)
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
```
