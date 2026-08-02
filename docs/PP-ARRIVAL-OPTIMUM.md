# The PP arrival-epoch optimum — derivation, simulation, audits, decision

**Scope: the perihelion-pumped (PP) mission only** — the mission architecture. No other
propulsion mode appears in this analysis; every Δv below is propellant the PP vehicle
itself must generate. *"Budget" throughout means the Δv budget (velocity change, km/s,
the propellant currency) — never money.*

**Machine record:** [`docs/data/pp_arrival_sim.json`](data/pp_arrival_sim.json), written
by [`tools/sim_pp_arrival.py`](../tools/sim_pp_arrival.py); rows are replayed fresh from
the engine by the audit suite (audit_pumping §13h) on every run.

---

## 1. The question

The mission requirement admits any arrival within 100,000 yr. The arrival epoch T fixes
the aim: the required heliocentric cruise velocity v∞(T) and its tilt β(T) below the
ecliptic (from the AC barycentric astrometry, with the 2600-AU miss allowance shaved).
Which T minimises the PP vehicle's propellant?

## 2. Method — direct simulation, no closed forms in the loop

For each candidate T:

1. **Aim.** v∞(T), β(T) from the intercept geometry (`fermi_sim.intercept`, state from
   `fermi_sim.astro`; 2600 AU/T shave).
2. **Campaign.** The full 3-D anchored thermal pumping campaign is integrated to that
   aim: `pump_schedule.scheduled_pumped_vinf_3d` — 7-state RK4, the anchored 12-yr
   schedule geometry, the DERIVED thermal power curve (cap_eff(0.42 AU) = 3.54), thrust
   steered out of plane on the hyperbolic leg by angle γ with an asymptote-latitude
   feedback cutoff and a pure −z endgame. γ is optimised per epoch (golden section,
   0–40°). Acceptance gates per row: target v∞ reached; asymptote latitude within 0.06°
   of −β; custody ≤ 15 yr.
3. **Total.** + the LEO-400 orbit-energy escape leg √(μ⊕/a) = 7.67 km/s.
4. **Numerics.** dt/4 steps with the v∞-overshoot correction (d(dv)/d(v∞) = 0.64 along
   the campaign — the same convention as the tilt-curve derivation,
   `tools/derive_plane_tax.py`); three rows re-integrated at dt/8 as a convergence check.

Grid: 66–86 kyr at 2 kyr + 75–80.5 kyr at 500 yr + the exact ecliptic crossing; the
flyability edge located by bisection.

## 3. Results (the optimization — minimum read off the rows)

| T (yr) | v∞ (km/s) | tilt | γ* | total Δv (km/s) | vs bottom | custody |
|---|---|---|---|---|---|---|
| 66,000 | 23.24 | −5.5° | 29.5° | 33.63 | +1427 m/s | 13.6 yr |
| 68,000 | 23.32 | −4.5° | 29.2° | 33.26 | +1054 | 12.6 |
| 70,000 | 23.40 | −3.6° | 26.6° | 32.90 | +698 | 12.3 |
| 72,000 | 23.50 | −2.7° | 21.6° | 32.60 | +396 | 12.1 |
| 73,000 | 23.55 | −2.3° | 18.9° | 32.48 | +273 | 12.1 |
| 74,000 | 23.60 | −1.9° | 15.8° | 32.38 | +174 | 12.1 |
| 75,000 | 23.65 | −1.5° | 13.1° | 32.30 | +93 | 12.1 |
| 76,000 | 23.70 | −1.1° | 10.0° | 32.24 | +37 | 12.0 |
| 77,000 | 23.75 | −0.8° | 6.9° | 32.21 | +7 | 12.0 |
| **77,500** | 23.78 | −0.6° | 5.3° | **32.204 — bottom** | 0 | 12.0 |
| 78,000 | 23.80 | −0.4° | 3.9° | 32.21 | +2 | 12.0 |
| 78,500 | 23.83 | −0.25° | 2.2° | 32.21 | +7 | 12.0 |
| 79,000 | 23.86 | −0.08° | 0.9° | 32.22 | +19 | 12.0 |
| **79,252 — crossing** | 23.87 | 0.0° | 0.3° | 32.23 | **+27 — design default** | 12.0 |
| 80,000 | 23.91 | +0.25° | 2.2° | 32.26 | +60 | 12.0 |
| 82,000 | 24.02 | +0.9° | 7.2° | 32.40 | +199 | 12.1 |
| 84,000 | 24.13 | +1.5° | 11.7° | 32.59 | +388 | 12.2 |
| 86,000 | 24.23 | +2.1° | 15.3° | 32.82 | +614 | 12.3 |

**Read-off conclusions:**

- **The fuel minimum is a flat basin**: bottom at **77,500 yr (32.204 km/s)**; everything
  from 77,000 to 78,500 lies within 7 m/s; 76–79.3k within 40 m/s.
- **The ecliptic crossing (79,252 yr, in-plane aim) sits +26.7 m/s from the bottom** —
  inside the model's own noise (§5) — and is adopted as the **design epoch**, because it
  is the one epoch fixed by geometry alone (astrometry: −z₀/v_z), invariant under every
  pricing-model revision.
- **The flyability edge is ~65,000 yr** (aim tilt −5.96°): earlier aims cannot be
  acquired by the campaign within custody at any steering angle. Approaching the edge is
  expensive in both Δv (+1.4 km/s at 66k) and custody (13.6 yr at 66k vs 12.0 in the
  basin) — the "arrive earlier" branch is closed by physics well before the 58k
  cruise-speed minimum.
- **Custody is ~12.0–12.1 yr everywhere in the basin** — the epoch choice does not move
  operations cost.
- The 73,000-yr epoch (the impulsive/chemical optimum, which PP never pays) costs the PP
  vehicle **+0.27 km/s ≈ 2.4 kg of xenon**.

## 4. Cross-checks

1. **Convergence:** dt/8 re-integration moves the three checked rows by ≤ 4.1 m/s
   (75k: −2.9; 77.5k: −4.0; crossing: −4.1) — recorded in the JSON, audit-gated <40 m/s.
2. **Closed-form budget sweep** (v∞ + derived plane-tax + tax tables — independent
   tabulated pricing): argmin 77.8k, agreeing with the direct simulation within one grid
   step and ~30 m/s across the whole window (audit 13g(v)).
3. **Independent own-code 3-D re-integration** of the tilt cost (audit 13g(ii), written
   from the docstring spec with its own stepping): 610 m/s at the cap-model 2.48° point
   vs the engine's 606 m/s — and vs **PSI's independently measured 578 m/s** (their
   final assessment, 3-D re-optimization, an unrelated implementation): 5% apart.
4. **Fresh row replay in the audit suite** (13h): the recorded 75,000-yr row is
   re-simulated from the engine on every audit run and must land within 40 m/s.
5. **PSI's planar pumped column** (their Table 14 — tilt-free by their own caption)
   bottoms near 65,000 yr: exactly where a tilt-blind pricing should, and exactly where
   the tilt bill (their flagged open item, our derivation) closes the branch.

## 5. Error budget — why the "bottom" is quoted as a basin, not a point

| Source | Scale |
|---|---|
| Steering-search scatter + termination granularity (dt/4, corrected) | ~5–10 m/s |
| dt truncation (measured dt/4 → dt/8) | ≤ 4 m/s per row |
| Tilt-curve derivation noise (build 174) | ~10–20 m/s |
| Tax-table dt truncation (documented, conservative direction) | ~+20–35 m/s |
| Miss-allowance treatment (max-shave approximation) | ~±50 m/s equivalent |
| Astrometry inputs (sub-0.5% differences move the crossing itself ~500 yr) | ~±500 yr on any epoch label |

The 77.0–78.5k plateau spans 7 m/s — far below the ~30–50 m/s noise floor — so the
formal bottom (77,500) is **not resolvable from its neighbours** and has already moved
between derivation refinements (79.25k → 77.8k → 77.5k as tilt pricing and grids
sharpened). The crossing, +27 m/s away, never moves. Hence: **design epoch = the
crossing; the basin is the honest statement of the optimum.**

## 6. PSI context (final assessment, `audit/psi/`)

PSI's 73,012 yr is the derived optimum of the **impulsive (chemical) departure Δv** —
a quantity the PP vehicle never pays — kept as their report-wide design point with the
PP caveat stated six times (their pp. 16, 17, 26, 62, 63: the pumped column "is planar
and excludes the tilt-acquisition cost"; "whether the cruise-speed saving survives the
tilt bill is an open question… left as future work"; settling it "requires a
three-dimensional re-optimization across the window"). This analysis is that
computation. Exhaustive negative-proof (every 73k mention machine-classified; no 77–78k
AC arrival exists in their document): `audit/psi/PP-NOTES.md`. Where PSI did measure in
3-D (the 2.48° tilt cost), our derivations agree to 5%.

## 7. Decision and residuals

- **Design epoch: the 79,252-yr ecliptic crossing** (geometry-anchored; +27 m/s ≈
  0.08% ≈ noise). The calculator's default state and architecture-switch snap implement
  this; the fuel-optimum readout reports basin membership in Δv terms.
- **The epoch is a cost non-driver**: the whole 73–79.3k window is worth ~2.4 kg of
  xenon (~$25k under PSI's cost model), and custody is epoch-flat. An arrival-value
  preference (arrive ~6 kyr sooner at 73k for +0.27 km/s) is legitimate and documented,
  but is a preference, not an optimum.
- **Residuals:** steering is hyperbolic-leg-only (bound-phase plane steering could
  soften the ~65k flyability edge — untested); the tilt curve and tax tables are
  design-a₀-anchored; astrometry inputs are catalog values (a pre-departure re-reduction
  is PSI's R6 mitigation).

## 8. Reproduce

```bash
.venv/bin/python tools/sim_pp_arrival.py        # ~5 min; rewrites docs/data/pp_arrival_sim.json
.venv/bin/python tools/derive_epoch_table.py    # the coarse-grid variant (issue #11)
.venv/bin/python tools/derive_plane_tax.py      # the tilt-cost curve behind the integrator
.venv/bin/python audit/calcs/run_audits.py      # includes 13g/13h replays of the above
```
