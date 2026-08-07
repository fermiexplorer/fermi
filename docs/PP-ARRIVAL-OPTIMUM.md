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

The astrometry is the jointly-validated adopted state — Akeson et al. 2021 at its
native epoch J2019.5, kinematic-frame RV (V0 + the +61.4 m/s gravitational-redshift
correction), pinned as the golden fixture (`audit/psi/golden_v2/`) and gated on every
audit run. T is counted from J2019.5; the 2029.0 departure origin subtracts 9.5 yr.

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

All epochs are on the state clock (T from J2019.5); departure-origin times
subtract 9.5 yr (departure 2029.0).

| T (yr) | v∞ (km/s) | tilt (optimized aim) | γ* | total Δv (km/s) | vs bottom | custody |
|---|---|---|---|---|---|---|
| 66,000 | 23.44 | −5.2° | 29.4° | 33.64 | +1349 m/s | 13.6 yr |
| 68,000 | 23.52 | −4.3° | 29.2° | 33.26 | +978 | 12.6 |
| 70,000 | 23.60 | −3.4° | 24.7° | 32.92 | +637 | 12.3 |
| 72,000 | 23.68 | −2.5° | 19.9° | 32.64 | +355 | 12.2 |
| 73,000 | 23.72 | −2.2° | 17.2° | 32.53 | +245 | 12.1 |
| 74,000 | 23.76 | −1.8° | 14.8° | 32.44 | +153 | 12.1 |
| 75,000 | 23.79 | −1.4° | 12.0° | 32.37 | +79 | 12.1 |
| 76,000 | 23.84 | −1.1° | 9.1° | 32.32 | +34 | 12.1 |
| 77,000 | 23.88 | −0.8° | 6.4° | 32.293 | +7 | 12.0 |
| **77,500** | 23.90 | −0.6° | 5.3° | **32.286 — bottom** | 0 | 12.0 |
| 78,000 | 23.92 | −0.5° | 4.5° | 32.287 | +1 | 12.0 |
| 78,500 | 23.94 | −0.3° | 3.1° | 32.29 | +6 | 12.0 |
| 79,000 | 23.97 | −0.2° | 1.9° | 32.30 | +14 | 12.0 |
| 79,500 | 23.99 | −0.07° | 0.9° | 32.31 | +27 | 12.1 |
| **79,766 — crossing** | 24.00 | 0.0° | 0.3° | 32.32 | **+35 — design default** | 12.1 |
| 80,000 | 24.02 | +0.06° | 0.5° | 32.33 | +44 | 12.1 |
| 82,000 | 24.13 | +0.6° | 4.8° | 32.44 | +154 | 12.1 |
| 84,000 | 24.26 | +1.1° | 8.6° | 32.60 | +318 | 12.2 |
| 86,000 | 24.37 | +1.7° | 12.2° | 32.80 | +516 | 12.3 |

**Read-off conclusions:**

- **The fuel minimum is a flat basin**: bottom at **77,500 yr (32.286 km/s)**; everything
  from 77,000 to 78,500 lies within 7 m/s; 75–80k within ~80 m/s.
- **The ecliptic crossing (79,765.9 yr on the state clock — 79,756.4 yr from the 2029
  departure, crossing date AD 81,785 — in-plane aim) sits +35.4 m/s from the bottom** —
  the scale of the model's own noise (§5) — and is adopted as the **design epoch**,
  because it is the one epoch fixed by geometry alone (astrometry: −z₀/v_z), invariant
  under every pricing-model revision (it did not move when the miss-allowance convention
  was corrected; the basin bottom's value did).
- **The flyability edge is ~64,800 yr under the 15-yr custody gate** (a POLICY gate, not
  physics: the aims just below it are acquirable given ~16–20 yr of custody, so the edge
  moves ~1 kyr per gate choice — audit finding 8). Approaching it is expensive in both Δv
  (+1.3 km/s at 66k) and custody (13.6 yr at 66k vs 12.0 in the basin); the 58k
  cruise-speed minimum remains far beyond reach at any custody a 15-yr-class mission
  would accept.
- **Custody is ~12.0–12.3 yr everywhere in the basin** — the epoch choice does not move
  operations cost.
- The 73,000-yr epoch (near the impulsive/chemical optimum, which PP never pays) costs
  the PP vehicle **+0.25 km/s ≈ 2.1 kg of xenon**.
- Convention note: the live calculator applies **no miss shave at all** — it prices the
  raw exact-intercept aim, which is conservative by the full allowance value: ~0.15 km/s
  above this record's totals at the crossing and ~0.2 km/s at 73k. The record spends
  the 2600-AU allowance optimally (speed shave vs tilt buy-down). Neither convention
  moves the basin location or the design decision; the deltas are epoch-smooth.

## 4. Cross-checks

1. **Convergence:** dt/8 re-integration moves the three checked rows by ≤ 4.4 m/s
   (75k: +4.2; 77.5k: +4.3; crossing: +4.4) — recorded in the JSON, audit-gated <40 m/s.
2. **Closed-form budget sweep** (v∞ + derived plane-tax + tax tables — independent
   tabulated pricing): argmin 78.3k — inside the same sub-noise plateau as the
   simulation's 77.5k (the plateau is flat to ~7 m/s, so argmin location is
   noise-dominated within it; audit 13g(v) gates the agreement at ≤1 kyr).
3. **Independent own-code 3-D re-integration** of the tilt cost (audit 13g(ii), written
   from the docstring spec with its own stepping): 610 m/s at the cap-model 2.48° point
   vs the engine's 606 m/s — and vs **PSI's independently measured 578 m/s** (their
   final assessment, 3-D re-optimization, an unrelated implementation): 5% apart.
4. **Fresh row replay in the audit suite** (13h): the recorded 75,000-yr row is
   re-simulated from the engine on every audit run and must land within 40 m/s.
5. **Foundations verification (five-way, blind):** the arrival-model premises behind
   this table — linear kinematics over 79 kyr, the frame chain, constants, and the
   error terms of §5/§5b — were adversarially re-derived by this project's own
   multi-agent audit workflow plus four external frontier models (GPT-5.6 Sol,
   Grok 4.5, two Gemini tiers), each blind to the others. The chain is verified
   sound (galactic tide 1–5 AU; perspective acceleration exactly contained in the
   Cartesian propagation; constants < 0.01 yr); the honest uncertainty is in the
   catalog inputs, as budgeted in §5. Record: `audit/fable/fable-foundations-audit.md`.
6. **PSI's planar pumped column** (their Table 14 — tilt-free by their own caption) does
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
| Astrometry inputs — absolute-RV frame (catalog ±2 m/s sigmas are internal precision; the kinematic line-of-sight floor is 30–100 m/s: spectrograph zero points, convective-blueshift model residuals, orbit-fit gamma; three published gammas from the same data already span 13.4 m/s. The spectroscopic→kinematic gravitational-redshift correction, +61.4 ± 2.7 m/s, IS applied in the adopted state — every epoch label here is kinematic-frame) | ~±150–500 yr on any epoch label |
| Astrometry inputs — parallax/PM catalog identity (the adopted state is Akeson 2021 end-to-end at its native epoch J2019.5; the Kervella 2016 catalog differs by 3.64 mas ≈ 5.1σ formal ≈ 530 yr, an unresolved cross-catalog tension carried as a systematic; formal single-catalog sigmas are ±55 yr) | ~±200–500 yr systematic |
| Probe clock (T is measured from the state epoch, not from departure; at the 2029 departure target the correction v∞′ = \|r(T)\|/(T − t_dep) is ~+12 m/s — an exact identity once t_dep is fixed) | ~+12 m/s, deterministic |

The 77–78.5k plateau spans 7 m/s — far below the ~30–50 m/s noise floor — so the
formal bottom (77,500) is **not resolvable from its neighbours** and has already moved
in value between derivation refinements (79.25k → 77.8k → 77.5k as tilt pricing, grids
and the miss convention sharpened). The crossing, +35 m/s away, never moves. Hence:
**design epoch = the crossing; the basin is the honest statement of the optimum.**
Every epoch label above is *from the state epoch* and carries the astrometry band;
the basin's flatness (75–79.5k within ~65 m/s) is what makes the design insensitive
to it.

### 5b. Aim error in AU — the requirement's own currency

The mission requirement lives in **AU at closest approach**, not in years: the pass
condition is ≤ 2600 AU from the **AB barycenter at closest approach**, and
radial-velocity error is almost purely *along-track* — it moves the encounter
calendar, not the flyby distance (miss correlation ~0.007; scoring the same error
model at a fixed instant instead of at closest approach misreads ~0.99 pass
probability as ~0.80). The aim-error terms, independently derived and cross-checked
by five parties (this project's audit workflow + four external frontier-model
re-derivations, run blind):

| Aim-error term (AU at closest approach) | Scale | Character |
|---|---|---|
| Parallax/PM catalog identity (aim built on one catalog while the other is true: ~940 AU between the two published catalogs; up to ~2,200 AU for a mixed-catalog state vs a published-catalog truth) | ~900–2,200 AU | Systematic; retired only by new astrometry or a joint catalog adoption |
| Radial velocity (any size) | ~0 AU | Along-track timing only |
| Sun-vs-SSB frame (the aim v∞ is heliocentric, catalog velocities are barycentric; the Sun moves ≤16 m/s about the barycenter) | ~100–270 AU | Deterministic once the departure date is fixed; a launch-epoch trim |
| Proxima's pull on the AB barycenter over the flight (two-body integration, ~92 AU; not in the linear ephemeris) | ~90–105 AU | Deterministic, sign known; correctable with a wobble term |
| Solar-system escape + AB gravity bookkeeping (combined deterministic line) | ~130 AU | Correctable trim |
| Galactic tide (differential, both bodies feel the Galaxy) | < 8 AU | Verified null |
| A/B component excursion from the barycenter | ≤ ~20 AU | Verified null |

Under formal catalog sigmas the closest-approach pass probability is ≈ 1.00; under
honest systematic floors ≈ 0.98–0.99; only stressing the full catalog gap as a 1σ
drops it to ~0.83–0.88. Every configuration this record actually flies clears the
2600-AU condition.

**Shave-convention caveat:** the per-epoch "optimal spend" of the 2600-AU allowance
(§2) is a *pricing device* for the Δv table, not a flyable budget — a real mission
must hold the allowance in reserve against the systematic terms above rather than
spend it on aim shaping. The live calculator's no-shave convention (§3) is the
flyable-side statement; the two bracket the truth by ~0.12–0.19 km/s.

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

- **Design epoch: the 79,766-yr ecliptic crossing** (state clock; 79,756 yr from the
  2029 departure; geometry-anchored; +35 m/s ≈ 0.11% ≈ noise). The calculator's default
  state and architecture-switch snap implement this; the fuel-optimum readout reports
  basin membership in Δv terms.
- **The epoch is a cost non-driver**: the whole 73–79.8k window is worth ~2.1 kg of
  xenon (~$23k under PSI's cost model), and custody is epoch-flat. An arrival-value
  preference (arrive ~6.8 kyr sooner at 73k for +0.25 km/s) is legitimate and documented,
  but is a preference, not an optimum.
- **Residuals:** steering is hyperbolic-leg-only (bound-phase plane steering could
  soften the ~64.8k flyability edge — untested); the edge itself is a 15-yr custody-gate
  policy label (~±1 kyr per gate choice), not a physics wall until ~63.5k; the tilt curve
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
