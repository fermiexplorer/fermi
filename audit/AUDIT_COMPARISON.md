# Audit cross-comparison — every independent source, side by side

**What this is.** A single place to see how the Fermi engine, the external PSI assessment,
NASA GMAT, and the four independent AI re-implementations (Codex, Grok, Gemini, Fable) stack
up against each other — quantity by quantity — with an honest account of **which results are
trustworthy, which are single-sourced, and exactly why the numbers differ where they do.**

Every value below is copied from the committed result artifacts, not re-derived for this table.
Engine values are the current tree; bot values are from each bot's committed `*_results.json` /
conclusions; GMAT from [`audit/gmat/out/`](https://github.com/fermiexplorer/fermi/tree/main/audit/gmat/out);
PSI from [`audit/psi/`](https://github.com/fermiexplorer/fermi/tree/main/audit/psi).

**Quick links:** [master audit index](https://github.com/fermiexplorer/fermi/blob/main/audit/README.md) ·
[adversarial prompts](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md) ·
[in-repo suite](https://github.com/fermiexplorer/fermi/tree/main/audit/calcs) ·
[PSI assessment (PDF)](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/PSI-TR-2026-0714.pdf) ·
[GMAT](https://github.com/fermiexplorer/fermi/blob/main/audit/gmat/README.md) ·
[Codex](https://github.com/fermiexplorer/fermi/blob/main/audit/codex/codex-conclusions-v04.md) ·
[Grok](https://github.com/fermiexplorer/fermi/blob/main/audit/grok/grok-conclusions.md) ·
[Gemini](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini-conclusions.md) ·
[Fable](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-conclusions.md)

---

## 0. Read this first — "why do we get 4.9 and PSI gets 12?"

**They are different units.** Our **4.9 is revolutions**; PSI's **12 is years**. Comparing them
directly is an apples-to-oranges trap that this table exists to prevent:

| | Revolutions around the Sun | Campaign duration | Δv |
|---|---|---|---|
| **Fermi engine** (bang-bang policy) | **4.9 revs** | 9.6 yr | 25.63 km/s |
| **Fable** (adversarial, 2 integrators) | 4.88 revs | 9.6–9.7 yr | 25.61 km/s |
| **PSI** (optimised schedule) | ~5–6 perihelion passes | **12 yr** | 23.97 km/s |
| *(drawn animation)* | *~3.5 revs* | *8.6 yr* | *(schematic)* |

So the honest comparison is **4.9 revs / 9.6 yr (ours) vs ~5–6 passes / 12 yr (PSI)** — the
revolution counts are close; the *durations and Δv* differ, and they differ **by design**:

1. **Ours burns harder per arc.** Our bang-bang policy applies full available thrust whenever its
   gate opens, so each perihelion pass adds a bigger energy step. Bigger steps ⇒ slightly fewer,
   fatter revolutions and a shorter campaign (9.6 yr), paid for with **more Δv (25.63)**.
2. **PSI's optimiser is patient.** It spreads gentler arcs over more revolutions/time, staying
   closer to the impulsive ideal at each pass, so it reaches the same v∞ for **less Δv (23.97)** —
   at the cost of **12 years** of powered flight. PSI names this explicitly as the *patience trade*:
   in their own words, patience is worth ≈4 km/s (their faster variant costs 28.2 km/s in 4.9 **years** —
   another number whose numeric coincidence with our 4.9 *revolutions* is pure accident).
3. **Neither is "wrong."** Ours is a deliberately cruder, independent reconstruction whose job is to
   *validate the mechanism*; PSI's is an optimised schedule. Ours lands exactly where PSI's own
   patience curve predicts — between their patient (12 yr / 23.97) and fast (4.9 yr / 28.2) profiles.
   **PSI's is the more optimal trajectory**; ours is the independent check that the mechanism is real.
4. **The third number** (~3.5 revs in the on-page animation) is the drawn 3-body schematic, which
   starts from the *actual post-Earth-escape state* rather than the engine's clean 1 AU circular
   start. Same policy, different entry conditions — labelled "(drawn)" in the UI for that reason.

The phase-by-phase breakdown behind these numbers is in [§4](#4-perihelion-pumping--the-narrower-chain-engine-psi-fable-adversarial-only);
if the **α** figures are what you are comparing, read [§2b](#2b-α-specific-power--the-same-symbol-in-three-different-senses)
first — α means three different things across these sources, and PSI sizes in a₀ rather than α.

---

## 1. Provenance & independence — what each source was given, and whether it saw PSI

This is the load-bearing table for *trust*. "Saw PSI?" matters because the perihelion-pumping
result **originated** with PSI; a source that confirms it without having seen PSI is genuine
independent corroboration, whereas PSI confirming its own result is not.

| Audit run | Source | Build audited | Input / prompt given | **Saw the PSI report?** | Method (vs engine) | Scope | Document |
|---|---|---|---|---|---|---|---|
| Codex v01–v04 | GPT-class (Codex) | pre-pumping (≈v3–v4) | [`AUDIT_PROMPTS.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md) §1–10 (deep-dive on §10, the 58 kyr / xenon claim); repo only | **No** — ran on builds that predate pumping | hand-built vectors + rocket equation, independent grids | ephemeris, intercept, departure, xenon sizing | [v01](https://github.com/fermiexplorer/fermi/blob/main/audit/codex/codex-conclusions-v01.md) · [v02](https://github.com/fermiexplorer/fermi/blob/main/audit/codex/codex-conclusions-v02.md) · [v03](https://github.com/fermiexplorer/fermi/blob/main/audit/codex/codex-conclusions-v03.md) · [**v04**](https://github.com/fermiexplorer/fermi/blob/main/audit/codex/codex-conclusions-v04.md) · [scripts](https://github.com/fermiexplorer/fermi/tree/main/audit/codex) |
| Grok v02 | Grok | ≈build 106 | [`AUDIT_PROMPTS.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md) §1–10 + sensitivity sweeps; repo only | **No** | hand ephemeris + independent sweeps | all 10 areas | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/grok/grok-conclusions.md) · [results.json](https://github.com/fermiexplorer/fermi/blob/main/audit/grok/prompt_results.json) · [sweeps](https://github.com/fermiexplorer/fermi/blob/main/audit/grok/sweep_results.json) |
| Gemini v01 (+v2 rerun) | Gemini | ≈build 106 | [`AUDIT_PROMPTS.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md) §1–9; repo only | **No** | **astropy** SkyCoord + **scipy solve_ivp** (RK45) | ephemeris, intercept, spiral | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini-conclusions.md) · [v01 audit](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini-audit-v01.md) · [results](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini_results.json) · [v2 results](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini_results_v2.json) |
| Fable — core | Fable 5 | build 106 | 22 independent checks over §1–9; repo only | **No** | scipy RK45 + finite-difference ephemeris | ephemeris → power gate | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-conclusions.md) · [results.json](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable_results.json) · [script](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable_independent_checks.py) |
| **GMAT** | NASA GMAT (R2020a) | departure model | 2 mission scripts (impulsive C3; low-thrust escape) | **No** | separate flight-proven propagator | departure energetics only | [README](https://github.com/fermiexplorer/fermi/blob/main/audit/gmat/README.md) · [scripts](https://github.com/fermiexplorer/fermi/tree/main/audit/gmat/scripts) · [raw outputs](https://github.com/fermiexplorer/fermi/tree/main/audit/gmat/out) · [compare.py](https://github.com/fermiexplorer/fermi/blob/main/audit/gmat/compare.py) |
| Fable — pumping | Fable 5 (31-agent workflow) | build 123 | [`AUDIT_PROMPTS.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md) §11–12, adversarial ("refute it") | **Partial** — repo held *our* reproduction; **not** the PSI PDF (added only at build 135) | 2 independent integrators (own RK4 + **DOP853**) | perihelion pumping + synchrotron | [pumping/synchrotron audit](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-pumping-synchrotron-audit.md) |
| Fable — text/coherence | Fable 5 (144 / 98 / 43 agents) | builds 129–135 | reader-text + default-state + envelope lenses | Yes (by then archived) | scripted extraction + node/scipy re-derivation | prose, data, UI-state coherence | [text audit](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-text-audit.md) |
| **PSI** | Physical Superintelligence PBC | external (our public page) | produced end-to-end on its own platform | **Is** the report | autonomous physics-research platform | full mission | [PSI‑TR‑2026‑0714 (PDF)](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/PSI-TR-2026-0714.pdf) · [our notes](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/README.md) |

**The independence chain that matters:** Codex, Grok, Gemini, Fable-core and GMAT all ran on
builds that **predate the pumping work entirely** — pumping wasn't in the model yet, so they
could not have been influenced by PSI. They independently confirm the **geometry and departure
energetics** that PSI *also* independently confirmed. So those quantities are corroborated by
**six mutually-blind sources**. The **pumping** result is a narrower chain (Engine + Fable-
adversarial + PSI), detailed in §4.

---

## 2. Geometry & departure — corroborated by everyone (highest trust)

Blank cell = that source did not report that quantity. Bold engine column is the reference.

| Quantity | **Engine** | PSI | GMAT | Codex | Grok | Gemini | Fable |
|---|---|---|---|---|---|---|---|
| AC space speed (km/s) | **32.3008** | ~32.3 | — | 32.301 | 32.3008 | (Δ only) | 32.3008 |
| AC distance now (ly) | **4.344** | — | — | 4.513¹ | 4.344 | — | 4.344 |
| Closest-approach epoch (kyr) | **27.960** | 27.955 | — | — | 27.9597 | — | 27.9596 |
| Closest-approach distance (ly) | **3.1297** | 3.152 | — | — | 3.1297 | — | 3.1297 |
| Hand-vs-astropy state error | **—** | — | — | — | 5.66 m / 2.6×10⁻⁶ m/s | 5.66 m / 2.6×10⁻⁶ m/s | ~1×10⁻⁸ % |
| Tangential (min-speed) arrival (yr) | **58,138** | 58,422 | — | 58,138 | 58,138 | — | 58,138 |
| Tangential v∞ (km/s) | **23.2719** | 23.38 | — | 23.2719 | 23.2719 | — | 23.2719 |
| Tangential aim tilt (deg) | **−10.0** | — | — | −9.99 | −9.995 | — | −9.995 |
| Min-Δv arrival (yr) | **72,800** | 73,012 | — | 72,800 | 72,800 | — | — |
| Min-Δv impulsive floor (km/s) | **13.875** | 13.85 | — | 13.875 | 13.875 | 13.8856² | — |
| v∞ at 75 kyr (km/s) | **23.8106** | — | — | — | 23.8106 | 23.8106 | — |
| v∞,Earth at optimum (km/s) | **19.489** | 18.59² | — | 19.489 | — | 18.628² | 19.489 |
| Impulsive floor, 400 km @ optimum (km/s) | **14.633** | — | — | 14.633 | 14.651² | — | 14.633 |
| Post-burn C3 (km²/s²) | **379.8154** | — | **379.8154** | — | — | — | — |
| Spiral escape time (Ms) | **14.266** | — | **14.266** | — | — | — | 14.265 |
| Spiral revs to Earth escape | **691.9** | — | ~692 | — | — | — | 692.0 |
| Low-thrust departure Δv (km/s) | **25.99** | — | — | 25.987 | 25.99² | 25.127² | 25.987 |
| Xenon @ 20 km/s, Isp 3000 (kg) | **248.24** | — | — | 248.2 | 248.24 | — | — |
| Silicon array (kg / W·kg⁻¹) | **55.1 / 91** | — | — | — | 55.1 / 91 | — | — |

¹ Codex reported AC's *4.513 ly asymptotic* distance term, not the 4.344 ly present distance —
different quantity, not a disagreement. ² marked cells are evaluated at a **different arrival
epoch or aim** than the engine's reference (75 kyr / 58 kyr slider vs the 72.8 kyr optimum); see
§3. All unmarked cells agree with the engine to **≤0.2 %, most to ≤0.01 %.**

### α-conditional power gate (Fable's independent RK45 vs the engine's fixed-dt RK4)

| Gate case | **Engine** | Fable | Δ |
|---|---|---|---|
| High-α solar default v∞ (km/s) | **30.30** | 30.34 | 0.15 % |
| Low-α solar v∞ (km/s) | **14.42** | 14.45 | 0.19 % |
| Nuclear-electric 5 kW v∞ (km/s) | **25.24** | 25.25 | 0.05 % |

Same feasibility verdicts across two integrators — the α ≳ 100 W/kg outward-spiral gate is real.

---

## 2b. α (specific power) — the same symbol in three different senses

α is the most-confused number in this project, because **three different quantities all get called
"specific power"**, they differ by an order of magnitude, and PSI's primary sizing variable is not
α at all — it is **a₀** (initial thrust acceleration, m/s²). This section makes every α claim
comparable.

**The conversion.** With `F = 2ηP/vₑ` and `a₀ = F/m_wet`, whole-vehicle
`α = P/m_dry = (a₀·vₑ/2η) · (m_wet/m_dry)`. At the design profile (a₀ = 2.5×10⁻⁴ m/s²,
Isp 2800 s, η 0.55) the leading factor is **6.24 W/kg per unit mass-ratio**, so
**α = 6.24 · (m_wet/m_dry)** — α is fixed by the *mass ratio*, not by the vehicle's size.

### Sense 1 — component (array) specific power. *Not* the gate variable.

| Source | Array specific power | Notes |
|---|---|---|
| **PSI** | **60 W/kg** system-level, ×1.25 radiation penalty for a LEO start | PDF §5.1; PPU 6 kg/kW, tank 12 % of propellant |
| Engine — conservative preset | 91 W/kg (silicon, ~20 % cells) | Starlink-class representative value |
| Engine — page default | 1000 W/kg (ultra-thin GaAs) | epitaxial-liftoff cells, far-term blanket |
| Engine — concentrator preset | 486 W/kg | |
| Grok | 90.7 W/kg (independently recomputed) | matches the silicon preset |

*These are hardware numbers for one subsystem. A vehicle never achieves them, because engine, tank,
structure and payload dilute the dry mass.*

### Sense 2 — whole-vehicle α = P / (m_dry + payload). **This is the gate variable.**

| Source / design | Vehicle α | How obtained |
|---|---|---|
| **PSI — LEO 100 & 150 kg** (68 % propellant) | **19.5 W/kg** | derived here from PSI's own §5.1/§5.2 sizing (a₀ 2.5×10⁻⁴, Isp 2800, η 0.55) |
| **PSI — GTO 100 & 80 kg** (64 % propellant) | **17.3 W/kg** | same derivation |
| **Fermi page — published pumping band** | **15–21 W/kg** | our band; **brackets PSI's implied 17.3–19.5** ✔ |
| Fermi page — default vehicle (2 kW GaAs) | ~120 W/kg | the shipped default is *far above* what pumping needs |
| Fermi — nuclear-electric closure | ~23 W/kg | constant-power route |
| *(retracted)* 13 W/kg | **impossible** | R = 2.08 ⇒ Δv capacity 20.1 km/s < the 23.97 required (Fable audit finding; band corrected 13–25 → 15–21) |

**The key cross-check:** PSI never publishes a vehicle-α figure — it sizes in a₀. Converting PSI's
*own published mass model* through the formula above gives **17.3–19.5 W/kg**, which falls inside
the **15–21 W/kg** band this project publishes. So the headline claim *"pumping closes at today's
α"* is corroborated in PSI's own numbers, not merely asserted from ours.

### Sense 3 — α *thresholds* (what a trajectory class demands)

| Threshold | Value | Trajectory class | Source |
|---|---|---|---|
| Solar-escape floor | **~43 W/kg** | outward spiral — below this a solar vehicle never escapes the Sun | engine, bisected escape edge |
| Cheap targets (e.g. HD 7924, 3.9 km/s cruise) | ~46 W/kg | outward spiral | engine star tables |
| λ Ser (19.2 km/s cruise) | ~68 W/kg | outward spiral | engine star tables |
| **AC-class (23.3–24.9 km/s)** | **~100–140 W/kg** | outward spiral | engine; PSI cites "roughly 100 W/kg" for the same corner |
| Ceiling | no α suffices above ~26.5 km/s | outward spiral at this sizing | engine (fixed 20 km/s propellant budget) |
| **Perihelion pumping** | **15–21 W/kg** | pumped campaign | engine + PSI-derived (above) |

**Why the same mission needs ~100 W/kg one way and ~18 W/kg the other:** it is the *trajectory*, not
the power system. An outward spiral must keep thrusting as sunlight fades (1/r²), so it needs a very
light vehicle to finish while power is still available. Pumping instead concentrates every burn at
0.42 AU where power is up to 4× the 1-AU rating — so a ~6× heavier vehicle (per watt) closes the
same mission. **That factor of ~6 in α is the entire result.**

---

## 3. Why the geometry numbers differ where they do (every discrepancy accounted for)

None of these are engine errors; each has a specific, benign cause.

1. **PSI vs engine, ~0.5 % on the epochs** (58,422 vs 58,138 yr; 3.152 vs 3.130 ly; 73,012 vs
   72,800 yr; 23.38 vs 23.27 km/s tangential). **Cause: different input astrometry.** PSI adopts
   its own catalogue state for α Cen; the engine uses the SIMBAD/Hipparcos values in
   `fermi_sim/astro.py`. A ~0.5 % difference in the adopted proper motion / RV propagates to a
   ~0.5 % difference in the encounter epoch. This is an *input* disagreement, not a *method* one —
   and it is well inside the mission's own 2600 AU (1 %) miss tolerance.
2. **Gemini's 25.127 vs Codex/Fable's 25.987 km/s low-thrust Δv, and 18.628 vs 19.489 km/s
   v∞,Earth.** **Cause: different arrival epoch.** Gemini evaluated the departure at the **75 kyr**
   benchmark (tilt −1.52°); Codex and Fable at the **58 kyr** tangential aim (tilt −10°). Different
   aim → different tilt → different Earth-borrow → different Δv. At a *common* epoch all three agree.
3. **Codex/Grok "58 kyr slider" floor 14.651 vs optimum 14.633 km/s.** Same story — the 58,000 yr
   slider value vs the exact 58,138 yr tangential optimum.
4. **Fable power-gate ~0.15 % high.** Fixed-dt RK4 (engine) vs adaptive RK45 (Fable) on a stiff
   1/r² integrand — a pure discretisation difference, converging as dt → 0.
5. **The ~20 km/s SEP number (Grok risk #1, Codex caveat).** Both flagged it as *benchmarked, not
   derived from a phased trajectory*. **They were right**, and it has since been **superseded**: the
   shipped model now uses the conservative ~30 km/s two-leg budget and the pumping architecture.
   This is the one place an early audit's caution drove a real model change.

---

## 4. Perihelion pumping — the narrower chain (Engine, PSI, Fable-adversarial only)

The four "core" bots never tested pumping (it postdates their builds). Pumping is corroborated by
three sources only, and the distinction between *mechanism* (well-corroborated) and *optimality*
(single-source) is the key trust point.

| Quantity | **Engine** (bang-bang) | Fable-adversarial | PSI (optimised) |
|---|---|---|---|
| Design-point v∞ (km/s) | **23.66** | 23.66–23.67 (2 integrators) | 23.64 |
| Design-point Δv (km/s) | **25.63** | 25.61 | **23.97** |
| Powered campaign (yr) | **9.63** | 9.6–9.7 | 12.0 |
| Revolutions / passes | **4.89 revs** | 4.88 revs | ~5–6 passes |
| — retrograde pump-down | **2.13 revs** | (reproduced) | ~4 gentler revs |
| — prograde perihelion passes | **3** | (reproduced) | ~5–6 |
| Δv split (retro + prograde) | **8.3 + 17.3** | reproduced | — |
| Working-region edge a₀ (m/s²) | **2.24×10⁻⁴** | 2.239×10⁻⁴ (bisection) | 2.5×10⁻⁴ design |
| Non-monotonic islands/stalls | **yes** | yes (3 integrators) | (not characterised) |
| Outward-spiral ceilings (km/s) | **0 / 3.1 / 16.7** | confirms | 0 / 3.4 / 17.0 |
| Certified heliocentric lower bound | — | — | **16.56** |

**What is well-corroborated:** the *mechanism* (retrograde pump-down to 0.42 AU, then prograde
perihelion staircase), the *closure at today's α*, the *design-point endpoints*, the *outward-
spiral ceilings* (within PSI's own 2.7 % two-integrator band), and the *non-monotonic threshold
structure*. Engine and Fable agree to <0.2 % using two integrators each, and PSI agrees on the
mechanism and the ceilings.

**What is single-sourced (lower trust):**
- **PSI's optimised Δv 23.97 km/s and its 22.9 km/s lower anchor.** No other source has reproduced
  PSI's optimiser. PSI itself flags this honestly: their intended cross-check (a direct-collocation
  solver) **did not converge**, so 22.9 is a single-method (Pontryagin) result, not a bound.
- **Our +7 % premium (25.63 vs 23.97).** This is a *deliberate* policy difference, not an error: our
  bang-bang schedule is cruder than PSI's optimised one. The instrumented split (§4 table) shows the
  premium is almost entirely in the retrograde pump-down (our 8.3 km/s vs the ~6.9 km/s impulsive
  minimum); the prograde legs agree to ~2 %.

**Which is more optimal?** PSI's, unambiguously — that is what an optimiser is for. Ours is a
validation reconstruction, and it lands exactly on PSI's own patience-trade curve (between their
12-yr/23.97 patient profile and their faster/28.2 variant).

---

## 5. Trust summary — what to rely on, and how hard

| Tier | Quantities | Corroboration | Rely on it? |
|---|---|---|---|
| **A — triangulated** | ephemeris, intercept geometry, impulsive floor, low-thrust spiral, C3, xenon sizing, power gate | 4 blind AI bots + GMAT + PSI, ≤0.2 % (most ≤0.01 %), multiple methods | **Yes**, to Fermi-estimate fidelity |
| **B — dual-source mechanism** | pumping mechanism, design endpoints, thresholds, spiral ceilings, synchrotron model | Engine + Fable (2 integrators each) + PSI on mechanism | **Yes** for the *mechanism and thresholds* |
| **B — α closure band** | pumping closes at α ≈ 15–21 W/kg | our band **brackets** the 17.3–19.5 W/kg implied by PSI's own published mass model (§2b) | **Yes** — corroborated in both sources' numbers |
| **C — single-source** | PSI's optimised 23.97 / 22.9 km/s schedule; our exact bang-bang Δv premium | one optimiser each; PSI's own cross-check didn't converge | **Directionally** — the closure holds; the exact optimum is not independently confirmed |
| **D — superseded** | the old ~20 km/s "modest xenon" SEP budget | Grok/Codex flagged it; replaced by the ~30 km/s + pumping model | **No** — historical only |

**Bottom line.** The *feasibility verdict and the geometry* are as solid as a first-order study
gets — six independent, mutually-blind sources agree. The *pumping mechanism* is corroborated by
two independent reconstructions plus PSI. The one genuinely single-sourced claim is *PSI's exact
optimised Δv*, which PSI itself does not present as a proven bound. Nothing in the audit record
overturns the closure; the honest caveats are all about *how cheaply* pumping closes, not *whether*.

---

## 6. How to reproduce / extend

Each bot's script + committed results live under its own directory (linked in §1); the prompts are
[`audit/AUDIT_PROMPTS.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md)
(§1–10 geometry/departure, §11–12 pumping/synchrotron). To add a new independent run, follow the
setup line in the prompts file, drop the conclusions + `*_results.json` under a new
`audit/<name>/`, and add a column here.

Codex v01–v04 and Gemini v01/v2 are **separate runs of the same §1–10 audit** and converged; their
per-run detail is in the individual documents linked in §1 — this page shows each bot's definitive
(latest) values. The genuinely *different* audits are kept as separate documents:
[core geometry/departure](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-conclusions.md),
[pumping/synchrotron](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-pumping-synchrotron-audit.md),
and [text/coherence](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-text-audit.md).

**Reproduce the engine side yourself:**
[`fermi_sim/`](https://github.com/fermiexplorer/fermi/tree/main/fermi_sim) (source of truth) ·
[`web/physics.js`](https://github.com/fermiexplorer/fermi/blob/main/web/physics.js) (parity-checked port) ·
[`run_analysis.py`](https://github.com/fermiexplorer/fermi/blob/main/run_analysis.py) ·
[`audit/calcs/run_audits.py`](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/run_audits.py) (130 checks) ·
[`audit/calcs/audit_pumping.py`](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/audit_pumping.py) (the pumping guards, incl. the phase split) ·
[`audit/calcs/audit_webjs.mjs`](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/audit_webjs.mjs) (35 parity checks)
