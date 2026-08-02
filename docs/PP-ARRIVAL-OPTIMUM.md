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
   `fermi_sim.astro`), with the 2600-AU miss allowance spent **optimally**: the permitted
   aim-point offset is a free direction, so it is optimized per epoch between speed shave
   and tilt buy-down (against the closed-form pumped budget as the selection proxy; the
   row values remain full 3-D integrations). An earlier revision spent the whole
   allowance on speed shave at unchanged tilt, one-sidedly overpricing tilted epochs by
   up to ~60–100 m/s — found and corrected by adversarial audit (finding 0).
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

| T (yr) | v∞ (km/s) | tilt (optimized aim) | γ* | total Δv (km/s) | vs bottom | custody |
|---|---|---|---|---|---|---|
| 65,000 | 23.28 | −5.6° | 29.7° | 33.71 | +1509 m/s | 14.0 yr |
| 66,000 | 23.32 | −5.1° | 29.5° | 33.51 | +1317 | 13.1 |
| 68,000 | 23.40 | −4.1° | 29.2° | 33.14 | +940 | 12.5 |
| 70,000 | 23.48 | −3.2° | 24.4° | 32.79 | +597 | 12.2 |
| 72,000 | 23.56 | −2.4° | 19.4° | 32.52 | +320 | 12.1 |
| 73,000 | 23.60 | −2.0° | 16.7° | 32.41 | +211 | 12.1 |
| 74,000 | 23.65 | −1.6° | 13.6° | 32.32 | +125 | 12.1 |
| 75,000 | 23.68 | −1.3° | 10.8° | 32.26 | +63 | 12.0 |
| 76,000 | 23.72 | −0.9° | 8.3° | 32.22 | +20 | 12.0 |
| 77,000 | 23.76 | −0.6° | 5.5° | 32.198 | +0.6 | 12.0 |
| **77,500** | 23.78 | −0.5° | 4.5° | **32.198 — bottom** | 0 | 12.0 |
| 78,000 | 23.81 | −0.3° | 3.1° | 32.202 | +4 | 12.0 |
| 78,500 | 23.83 | −0.2° | 1.9° | 32.21 | +12 | 12.0 |
| 79,000 | 23.86 | −0.07° | 0.9° | 32.22 | +25 | 12.0 |
| **79,252 — crossing** | 23.87 | 0.0° | 0.3° | 32.23 | **+33 — design default** | 12.0 |
| 80,000 | 23.91 | +0.2° | 1.7° | 32.26 | +65 | 12.0 |
| 82,000 | 24.03 | +0.75° | 6.2° | 32.39 | +192 | 12.1 |
| 84,000 | 24.15 | +1.3° | 10.3° | 32.57 | +371 | 12.1 |
| 86,000 | 24.27 | +1.8° | 13.6° | 32.78 | +583 | 12.2 |

**Read-off conclusions:**

- **The fuel minimum is a flat basin**: bottom at **77,500 yr (32.198 km/s)**; everything
  from 76,500 to 78,000 lies within 7 m/s; 75–79.5k within ~65 m/s.
- **The ecliptic crossing (79,252 yr, in-plane aim) sits +33.4 m/s from the bottom** —
  the scale of the model's own noise (§5) — and is adopted as the **design epoch**,
  because it is the one epoch fixed by geometry alone (astrometry: −z₀/v_z), invariant
  under every pricing-model revision (it did not move when the miss-allowance convention
  was corrected; the basin bottom's value did).
- **The flyability edge is ~64,200 yr under the 15-yr custody gate** (a POLICY gate, not
  physics: the 63–64k aims are acquirable given ~16–20 yr of custody, so the edge moves
  ~1 kyr per gate choice — audit finding 8). Approaching it is expensive in both Δv
  (+1.5 km/s at 65k) and custody (14.0 yr at 65k vs 12.0 in the basin); the 58k
  cruise-speed minimum remains far beyond reach at any custody a 15-yr-class mission
  would accept.
- **Custody is ~12.0–12.2 yr everywhere in the basin** — the epoch choice does not move
  operations cost.
- The 73,000-yr epoch (the impulsive/chemical optimum, which PP never pays) costs the PP
  vehicle **+0.21 km/s ≈ 1.8 kg of xenon**.
- Convention note: the live calculator applies **no miss shave at all** — it prices the
  raw exact-intercept aim, which is conservative by the full allowance value: ~0.12 km/s
  above this record's totals at the crossing and ~0.19 km/s at 73k. The record spends
  the 2600-AU allowance optimally (speed shave vs tilt buy-down). Neither convention
  moves the basin location or the design decision; the deltas are epoch-smooth.

## 4. Cross-checks

1. **Convergence:** dt/8 re-integration moves the three checked rows by ≤ 4.1 m/s
   (75k: −3.2; 77.5k: −3.5; crossing: −4.1) — recorded in the JSON, audit-gated <40 m/s.
2. **Closed-form budget sweep** (v∞ + derived plane-tax + tax tables — independent
   tabulated pricing): argmin 77.8k, agreeing with the direct simulation within one grid
   step and ~30 m/s across the whole window (audit 13g(v)).
3. **Independent own-code 3-D re-integration** of the tilt cost (audit 13g(ii), written
   from the docstring spec with its own stepping): 610 m/s at the cap-model 2.48° point
   vs the engine's 606 m/s — and vs **PSI's independently measured 578 m/s** (their
   final assessment, 3-D re-optimization, an unrelated implementation): 5% apart.
4. **Fresh row replay in the audit suite** (13h): the recorded 75,000-yr row is
   re-simulated from the engine on every audit run and must land within 40 m/s.
5. **PSI's planar pumped column** (their Table 14 — tilt-free by their own caption) does
   **not** bottom at 73,000 yr: its trend floor is 23.74 km/s across the 56–60k rows,
   near their cruise-speed minimum — where tilt-blind pricing should bottom. (The
   column's single lower value, 23.49 at 65,000 yr, is a seed-scatter outlier PSI itself
   flags — a −0.3 km/s discontinuity between 23.79/23.82 neighbours against their stated
   ±0.2 km/s scatter. An earlier revision of this note read it as a trend minimum and
   claimed a corroborating coincidence with our flyability edge; both were retracted
   after adversarial audit — finding 9.)

## 5. Error budget — why the "bottom" is quoted as a basin, not a point

| Source | Scale |
|---|---|
| Steering-search scatter + termination granularity (dt/4, corrected) | ~5–10 m/s |
| dt truncation (measured dt/4 → dt/8) | ≤ 4 m/s per row |
| Tilt-curve derivation noise (build 174) | ~10–20 m/s |
| Tax-table dt truncation (documented, conservative direction) | ~+20–35 m/s |
| Miss-allowance convention (ONE-SIDED: the earlier max-shave form overpriced tilted epochs by ~60–100 m/s at ≤73k, ~0 at the crossing — corrected to the optimized offset; the live calculator still uses the conservative form, <10 m/s inside the basin) | one-sided, disclosed |
| Custody-gate policy (the flyability edge moves ~1 kyr per gate-year choice) | ~±1 kyr on the edge label |
| Astrometry inputs (sub-0.5% differences move the crossing itself ~500 yr) | ~±500 yr on any epoch label |

The 76.5–78k plateau spans 7 m/s — far below the ~30–50 m/s noise floor — so the
formal bottom (77,500) is **not resolvable from its neighbours** and has already moved
in value between derivation refinements (79.25k → 77.8k → 77.5k as tilt pricing, grids
and the miss convention sharpened). The crossing, +33 m/s away, never moves. Hence:
**design epoch = the crossing; the basin is the honest statement of the optimum.**

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

- **Design epoch: the 79,252-yr ecliptic crossing** (geometry-anchored; +33 m/s ≈
  0.10% ≈ noise). The calculator's default state and architecture-switch snap implement
  this; the fuel-optimum readout reports basin membership in Δv terms.
- **The epoch is a cost non-driver**: the whole 73–79.3k window is worth ~1.8 kg of
  xenon (~$20k under PSI's cost model), and custody is epoch-flat. An arrival-value
  preference (arrive ~6 kyr sooner at 73k for +0.21 km/s) is legitimate and documented,
  but is a preference, not an optimum.
- **Residuals:** steering is hyperbolic-leg-only (bound-phase plane steering could
  soften the ~64k flyability edge — untested); the edge itself is a 15-yr custody-gate
  policy label (~±1 kyr per gate choice), not a physics wall until ~63k; the tilt curve
  and tax tables are design-a₀-anchored; astrometry inputs are catalog values (a
  pre-departure re-reduction is PSI's R6 mitigation). Adversarial-audit record:
  `audit/fable/fable-pp-adversarial-audit.md`.

## 8. Reproduce

```bash
.venv/bin/python tools/sim_pp_arrival.py        # ~5 min; rewrites docs/data/pp_arrival_sim.json
.venv/bin/python tools/derive_epoch_table.py    # the coarse-grid variant (issue #11)
.venv/bin/python tools/derive_plane_tax.py      # the tilt-cost curve behind the integrator
.venv/bin/python audit/calcs/run_audits.py      # includes 13g/13h replays of the above
```
