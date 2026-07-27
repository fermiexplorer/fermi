# Audit cross-comparison — every independent source, side by side

**What this is.** A single place to see how the Fermi engine, the external PSI assessment,
NASA GMAT, and the four independent AI re-implementations (Codex, Grok, Gemini, Fable) stack
up against each other — quantity by quantity — with an honest account of **which results are
trustworthy, which are single-sourced, and exactly why the numbers differ where they do.**

Every value below is copied from the committed result artifacts, not re-derived for this table.
Engine values are the current tree; bot values are from each bot's committed `*_results.json` /
conclusions; GMAT from [`audit/gmat/out/`](https://github.com/fermiexplorer/fermi/tree/main/audit/gmat/out);
PSI from [`audit/psi/`](https://github.com/fermiexplorer/fermi/tree/main/audit/psi).

> **The headline result in one line:** the same spacecraft flown as an *outward spiral* needs
> **~100–140 W/kg** of whole-vehicle specific power, but flown as a *perihelion-pumped* campaign
> needs only **~15–21 W/kg** — a **~6× difference that comes entirely from the trajectory, not the
> power system.** That factor is what moves the mission onto today's hardware. Full derivation and
> corroboration: **[§2c](#2c-the-6x-specific-power-result--the-trajectory-not-the-power-system-decides-feasibility)**.

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

**They are different units.** The bang-bang gate's **4.9 is revolutions**; PSI's **12 is years**.
Comparing them directly is an apples-to-oranges trap that this table exists to prevent:

| | Revolutions around the Sun | Campaign duration | Δv | Power model |
|---|---|---|---|---|
| **Fermi engine — anchored optimised schedule** (the flown default, issues #4/#5) | **7.9 revs** | **12.0 yr** | **24.44 km/s** | **derived thermal curve** (cap_eff(0.42) = 3.54) |
| Fermi engine — same construction at the idealised cap (PSI-comparable) | 5.9 revs | 12.0 yr | **23.14 km/s** | assumed 4× step |
| **Fermi engine** (bang-bang cross-check) | 4.9 revs | 9.6 yr | 25.63 km/s | assumed 4× step |
| **Fable** (adversarial, 2 integrators, bang-bang) | 4.88 revs | 9.6–9.7 yr | 25.61 km/s | assumed 4× step |
| **PSI** (optimised schedule) | ~5–6 perihelion passes | **12 yr** | 23.97 km/s | assumed 4× step |
| *(drawn animation)* | *~7.9 revs* | *~12 yr* | *(schematic)* | derived thermal curve |

So there are TWO comparisons to keep straight. **Like-for-like at 12 years under PSI's own 4×
assumption**: our optimised schedule buys the same cruise for **23.14 km/s vs PSI's 23.97**
(−3.5%). **What the calculator actually ships** (issue #5): the same optimisation under the
power curve *derived* from the array's energy balance — 3.54× at the floor, not 4× — which
costs **24.44 km/s** at the same custody. The bang-bang rows differ from PSI's **by design**:

1. **The gate burns harder per arc.** The bang-bang policy applies full available thrust whenever
   its gate opens, so each perihelion pass adds a bigger energy step. Bigger steps ⇒ slightly fewer,
   fatter revolutions and a shorter campaign (9.6 yr), paid for with **more Δv (25.63)**.
2. **Optimised schedules are patient.** They spread gentler arcs over more revolutions/time, staying
   closer to the impulsive ideal at each pass, so they reach the same v∞ for less Δv — PSI's 12-yr
   schedule costs **23.97**, and our anchored optimised schedule (4 free switching parameters,
   event-located arc edges, Nelder-Mead per a₀) costs **23.14** at the same 12-yr custody. PSI names
   the underlying trade explicitly as the *patience trade*: in their own words, patience is worth
   ≈4 km/s (their faster variant costs 28.2 km/s in 4.9 **years** — a number whose numeric
   coincidence with the gate's 4.9 *revolutions* is pure accident).
3. **Neither is "wrong."** The bang-bang is a deliberately cruder, independent reconstruction whose
   job is to *validate the mechanism* (and it stays the calculator's feasibility gate); the optimised
   schedule is what the calculator flies and prices. The gate lands exactly where PSI's own patience
   curve predicts — between their patient (12 yr / 23.97) and fast (4.9 yr / 28.2) profiles.
4. **The last row** (~4.9 revs / ~10 yr in the on-page animation) is the drawn 3-body schematic,
   which starts from the *actual post-Earth-escape state* rather than the engine's clean 1 AU
   circular start. Same schedule, different entry conditions — labelled "(drawn)" in the UI for
   that reason.

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
| Fable — pumping | Fable 5 (31-agent workflow) | builds 124–126 | [`AUDIT_PROMPTS.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md) §11–12, adversarial ("refute it") | **Partial** — repo held *our* reproduction; **not** the PSI PDF (added only at build 135) | 2 independent integrators (own RK4 + **DOP853**) | perihelion pumping + synchrotron | [pumping/synchrotron audit](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-pumping-synchrotron-audit.md) |
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
| AC space speed (km/s) | **32.3008** | 32.38³ | — | 32.301 | 32.3008 | (Δ only) | 32.3008 |
| AC distance now (ly) | **4.344** | — | — | 4.513¹ | 4.344 | — | 4.344 |
| Closest-approach epoch (kyr) | **27.960** | 27.955 | — | — | 27.9597 | — | 27.9596 |
| Closest-approach distance (ly) | **3.1297** | 3.152³ | — | — | 3.1297 | — | 3.1297 |
| Hand-vs-astropy state error | **—** | — | — | — | 5.66 m / 2.6×10⁻⁶ m/s | 5.66 m / 2.6×10⁻⁶ m/s | ~1×10⁻⁸ % |
| Tangential (min-speed) arrival (yr) | **58,138** | 58,422³ | — | 58,138 | 58,138 | — | 58,138 |
| Tangential v∞ (km/s) | **23.2719** | 23.38³ | — | 23.2719 | 23.2719 | — | 23.2719 |
| Tangential aim tilt (deg) | **−10.0** | — | — | −9.99 | −9.995 | — | −9.995 |
| Min-Δv arrival (yr) | **72,800** | 73,012³ | — | 72,800 | 72,800 | — | — |
| Min-Δv impulsive floor (km/s) | **13.875** | 13.85 | — | 13.875 | 13.875 | 13.8856² | — |
| v∞ at 75 kyr (km/s) | **23.8106** | — | — | — | 23.8106 | 23.8106 | — |
| v∞,Earth at optimum (km/s) | **19.489** | 18.59² | — | 19.489 | — | 18.628² | 19.489 |
| Impulsive floor, 400 km @ optimum (km/s) | **14.633** | — | — | 14.633 | 14.651² | — | 14.633 |
| Post-burn C3 (km²/s²) | **379.8154** | — | **379.8154** | — | — | — | — |
| Spiral escape time (Ms) | **14.266** | — | 14.265 | — | — | — | 14.265 |
| Spiral revs to Earth escape | **691.9** | — | ~692 | — | — | — | 692.0 |
| Low-thrust departure Δv (km/s) | **25.99** | — | — | 25.987 | 26.01 | 25.127² | 25.987 |
| Xenon @ 20 km/s, Isp 3000 (kg) | **248.24** | — | — | 248.2 | 248.24 | — | — |
| Silicon array (kg / W·kg⁻¹) | **55.1 / 91** | — | — | — | 55.1 / 91 | — | — |

¹ Codex reported AC's *4.513 ly asymptotic* distance term, not the 4.344 ly present distance —
different quantity, not a disagreement. ² marked cells are evaluated at a **different arrival
epoch or aim** than the engine's reference (75 kyr / 58 kyr slider vs the 72.8 kyr optimum); see
§3. ³ PSI evaluates against its own catalogue astrometry and optimiser, so these cells differ from
the engine by 0.2–0.7 % (all reconciled in §3). All unmarked (non-², non-³) cells agree with the
engine to **≤0.2 %, most to ≤0.01 %.**

### α-conditional power gate (Fable's independent RK45 vs the engine)

| Gate case | **Engine** | Fable | Δ |
|---|---|---|---|
| High-α solar default v∞ (km/s) | **30.34** | 30.34 | 0.001 % |
| Low-α solar v∞ (km/s) | **14.47** | 14.45 | 0.09 % |
| Nuclear-electric 5 kW v∞ (km/s) | **25.25** | 25.25 | 0.003 % |

Same feasibility verdicts across two integrators — the α ≳ 100 W/kg outward-spiral gate is real.
The engine column is the issue-#2 integrator (adaptive step, mass-coupled RK4); its agreement
with Fable's independent adaptive RK45 tightened from 0.05–0.19 % to 0.001–0.09 %, confirming
the earlier gaps were the retired fixed-step + first-order-mass error.

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
| Fermi — anchored optimised campaign, idealised 4× cap (issue #4) | 14.5 W/kg | Δv 23.14 ⇒ R = e^(23136/27459) = 2.32 ⇒ α = 6.24·2.32 |
| **Fermi — flown campaign under the derived thermal curve (issue #5)** | **15.2 W/kg** | Δv 24.44 ⇒ R = e^(24437/27459) = 2.44 ⇒ α = 6.24·2.44 — the shipped default lands *inside* the published band |
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

### Reading α correctly — α and Δv are *different* constraints (worked example: α² Librae)

A low α threshold does **not** mean an easy target. α is set by the **required cruise speed** alone;
the **Δv budget** is set by cruise *plus* the out-of-plane aim. They can point in opposite directions,
and α² Librae is the clean case:

| | **α² Librae** | **α Centauri** (crossing) |
|---|---|---|
| Required cruise | 14.5 km/s | 23.9 km/s |
| Arrival epoch | +798 kyr | ~80 kyr |
| **Min solar α (outward spiral)** | **~57 W/kg** ← *half of AC* | ~112 W/kg |
| Aim tilt | **−47°** | 0° |
| **Δv budget** | **39.1 km/s** ← *much worse* | 25.2 km/s |
| Propellant fraction | 74 % | 57 % |

**Why α is lower:** 798 kyr of patience permits a 14.5 km/s crawl, and a slower cruise is a much
easier power problem. **Why that is misleading:** α Librae's binding constraint is not power but the
−47° plane change, which Earth's velocity cannot supply and propellant must buy. It is
**power-easy but propellant-brutal** — which is precisely why this project ranks candidates by
**Δv budget, not by α** (the same trap as the c UMa −46° "tilt trap").

**Under pumping the α advantage vanishes entirely**, because every campaign flies at the same
validated a₀ — so α converges for both targets while α² Librae's plane change *plus* its
low-cruise campaign overhead make its budget substantially **worse**:

| Target | Cruise | Plane-change term | Pumped Δv | Propellant | Vehicle α |
|---|---|---|---|---|---|
| α² Lib | 14.5 | **10.6** | **41.0**¹ | 78 % | **27.8 W/kg** |
| AC (crossing) | 23.9 | 0.0 | 33.5 | 70 % | 21.1 W/kg |
| AC (design) | 23.6 | 1.0 | 34.2 | 71 % | 21.7 W/kg |

¹ α² Lib's campaign leg is priced by the **v∞-dependent tax** (`pump_tax_for`, a table
interpolated from the integrated campaign at the design a₀ — issue #3): tax(14.5) ≈ 8.2 km/s,
so the closed-form budget gives 40.9 km/s, matching the direct integration (41.0) to ~0.1 km/s.
The AC rows use the same table at its **pinned 2.0 km/s anchor** (v∞ = 23.64), which keeps every
published AC budget identical to the original corridor calibration. The table's validity floor
is 8 km/s; below it the budget refuses.

*(α² Lib's low cruise does close at a₀ as small as 8×10⁻⁵ — but that campaign runs ~60 yr over
~15 revolutions: the patience trade taken to its limit.)*

*(On the band: the project's headline "~15–21 W/kg" is the **PSI-implied** vehicle-α band, which
brackets PSI's own mass model. The engine's cruder bang-bang sizing lands slightly higher —
21.7 W/kg at the AC design point, just above the top of the band — the idealised-cap optimised
campaign slightly lower (14.5), and the campaign the calculator actually flies since issue #5
(the anchored schedule under the derived thermal curve) lands at **15.2 W/kg, inside the band**:
same physics, ±1 W/kg of schedule/power-model quality around the band, and the headline is kept
at 15–21 because that is the PSI-implied figure the project cites.
α² Lib's 27.8 W/kg is higher for a different reason — its integrated low-cruise campaign
carries ~8 km/s of in-plane overhead, which inflates the mass ratio that multiplies into vehicle α.)*

**Naming & kinematic caveat (α² Lib = SIMBAD "alf02 Lib" = PSI's "Alpha-2 Librae").** All rows
above refer to the same object: the naked-eye A-type component of the α Librae multiple system
(Zubenelgenubi). Its **systemic radial velocity is disputed between credible solutions**: the
star-table pipeline adopts **−11.0 km/s** (median of 8 published measurements, MAD 5.9 — but the
star is a spectroscopic binary, so that scatter is *orbital motion*, and the median is a biased
estimate of the centre-of-mass velocity), while the revised-Hipparcos systemic solution used by
[PSI‑TR‑2026‑0714 §8.3](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/PSI-TR-2026-0714.pdf)
is **−22.0 ± 5.8 km/s**. The 11 km/s difference moves the minimum-cruise-speed intercept epoch by
~2× (≈2.07 Myr on the adopted RV, ≈1.03 Myr on the Hipparcos value — substituting PSI's RV into
this project's linear kinematics reproduces their epoch to ~1%). **The verdict is identical under
either solution**: the cheap intercept lies far outside any mission horizon, and a
horizon-constrained arrival costs more than going to α Centauri itself (PSI: 19.74 vs
13.85 km/s impulsive) — so α² Lib is excluded as a mission target, appears only in the
relaxed-clock survey tables, and its row carries the ⚠ unverified-kinematics flag
(`RV_DISPUTED` in the star-table generator,
[`tools/make_starmap_data.py`](https://github.com/fermiexplorer/fermi/blob/main/tools/make_starmap_data.py)).

**Rule of thumb for reading these tables: α tells you whether the power system can do it at all;
Δv tells you whether the vehicle can afford it. Both must pass.**

---

*Why the same mission demands ~100 W/kg one way and ~18 W/kg the other is the whole result — it gets
its own section next.*

---

## 2c. The 6x specific-power result — the trajectory, not the power system, decides feasibility

This is the single most important number in the project, and it is easy to miss because it hides
behind two α figures quoted in different sections.

> **The same spacecraft, the same array, the same thruster, the same Isp — flown two different ways —
> differ by a factor of ~6 in the specific power they require.**
>
> | Flying the *same* AC-class mission | Whole-vehicle α required | Verdict at today's hardware |
> |---|---|---|
> | **Outward spiral** (thrust continuously while receding) | **~100–140 W/kg** | ✗ needs a far-term ultralight vehicle |
> | **Perihelion pumping** (burn only at 0.42 AU) | **~15–21 W/kg** (PSI's own model: 17.3–19.5) | ✓ **closes on today's hardware** |
> | **Ratio** | **≈ 5–7× (call it ~6×)** | this factor *is* the feasibility result |

### Where the ~6× comes from (decomposition)

Two multiplicative effects, both purchased by moving the burn to 0.42 AU:

| Effect | Factor | Why |
|---|---|---|
| **Power availability** | **4.0×** | array output ∝ 1/r²; at 0.42 AU that is 5.7× the 1-AU rating, capped at **4×** by the assumed thermal limit |
| **Oberth leverage** | **2.18×** | energy gained per unit Δv is `v·Δv`; perihelion speed there is 65.0 km/s vs 29.8 km/s circular at 1 AU (65.0/29.8 = 2.18) |
| *naive product* | *8.7×* | if the manoeuvre were free |
| **Observed α ratio** | **≈ 5–7×** | the shortfall is the cost of *getting* there — the retrograde pump-down (8.3 of our 25.6 km/s) plus gravity losses |

### Why this, and not "better solar panels", is the answer

- An **outward spiral is self-defeating**: it must keep thrusting as it recedes, exactly when its
  power source is fading. The Δv still deliverable arrives at ever-larger radii, where each increment
  buys less orbital energy — so achievable v∞ *saturates* below the cruise floor no matter how much
  propellant is carried. The only escape is to finish the burn before the light fades, i.e. an
  ultralight (high-α) vehicle — the ~100–140 W/kg requirement.
- **Pumping inverts the logic**: it first spends Δv to *lower* perihelion, then takes every subsequent
  burn where power is quadrupled and speed is doubled. The vehicle may therefore be ~6× heavier per
  installed watt and still close.
- **Consequence.** This moves the mission from *"needs a far-term thin-film array (~1000 W/kg class
  hardware to reach ~100+ W/kg vehicle α)"* to *"closes with a 60 W/kg system-level array"* — which is
  precisely the array PSI sizes with. **No power-system breakthrough is required; the change is
  entirely in the trajectory.**

### What it costs (the honest other side)

The ~6× in α is not free — it is bought with Δv, time and thermal risk:

| Price | Value |
|---|---|
| Extra Δv vs the impulsive ideal | flown campaign 24.44 km/s (derived thermal curve) / 23.14 (ours at the idealised 4×) / 23.97 (PSI, at 4×) / 25.6 (bang-bang, at 4×) vs a 13.9 km/s impulsive floor |
| Powered-flight duration | 12 yr (ours and PSI, optimised) – 9.6 yr (bang-bang) vs ~0.5–2 yr for a spiral |
| Thermal qualification | repeated 0.42 AU passes — MESSENGER-class; the harvest multiple is now DERIVED from the array energy balance (cap_eff 3.54× at the floor, T = 492 K; issue #5), and silicon-class cells collapse (0.08×) — GaAs is load-bearing |
| Policy fragility | fixed-geometry success is non-monotonic in a₀ (and the fixed geometries strand at the design a₀ under the derived curve); per-a₀ re-optimised schedules close every tested gap |

### Corroboration

| Claim | Engine | Fable (adversarial) | PSI |
|---|---|---|---|
| Outward spiral saturates below the floor | ✓ 0 / 3.0 / 16.7 km/s | ✓ confirms | ✓ 0 / 3.4 / 17.0 km/s |
| Pumping reaches the floor at the design a₀ | ✓ 23.66 km/s | ✓ 23.66–23.67 | ✓ 23.64 km/s |
| Vehicle α needed for pumping | ✓ 15–21 W/kg | ✓ band verified, 13 refuted | ✓ 17.3–19.5 implied (§2b) |
| Outward-spiral α for AC-class | ✓ ~100–140 W/kg | ✓ gate reproduced (RK45) | ✓ cites "roughly 100 W/kg" |

*Reproduce it:* the power and Oberth factors follow from `MU_SUN`/`AU` in
[`fermi_sim/constants.py`](https://github.com/fermiexplorer/fermi/blob/main/fermi_sim/constants.py)
(v_esc(0.42 AU) = 65.0 km/s vs v_circ(1 AU) = 29.8; cap = 4 from the power law in
[`departure.py`](https://github.com/fermiexplorer/fermi/blob/main/fermi_sim/departure.py));
the spiral ceilings come from `sep_achievable_vinf` and the pumped endpoints from
`perihelion_pumped_vinf`, both guarded in
[`audit/calcs/audit_pumping.py`](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/audit_pumping.py);
the α figures are derived in §2b.

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

All columns in this table are at the **idealised 4× power cap** — the assumption PSI's numbers
are published under, kept here for like-for-like comparison. The calculator's shipped default
since issue #5 is the same anchored optimisation under the **derived thermal curve**
(cap_eff(0.42) = 3.54): Δv **24.44** km/s, 12.0 yr, 7.9 revs.

| Quantity | **Engine** (bang-bang gate) | **Engine** (anchored optimised, issue #4) | Fable-adversarial | PSI (optimised) |
|---|---|---|---|---|
| Design-point v∞ (km/s) | **23.66** | 23.64 | 23.66–23.67 (2 integrators) | 23.64 |
| Design-point Δv (km/s) | **25.63** | **23.14** | 25.61 | **23.97** |
| Powered campaign (yr) | **9.63** | **12.0** | 9.6–9.7 | 12.0 |
| Revolutions / passes | **4.89 revs** | 5.86 revs | 4.88 revs | ~5–6 passes |
| — retrograde pump-down | **2.13 revs** | (gentler, wider arcs) | (reproduced) | ~4 gentler revs |
| — prograde perihelion passes | **3** | ~4 | (reproduced) | ~5–6 |
| Δv split (retro + prograde) | **8.3 + 17.3** | — | reproduced | — |
| Working-region edge a₀ (m/s²) | **2.24×10⁻⁴** | (grid closes 1.6–3.0×10⁻⁴) | 2.239×10⁻⁴ (bisection) | 2.5×10⁻⁴ design |
| Non-monotonic islands/stalls | **yes** | **no — per-a₀ schedules close every tested gap** | yes (3 integrators) | (not characterised) |
| Outward-spiral ceilings (km/s) | **0 / 3.0 / 16.7** | — | confirms | 0 / 3.4 / 17.0 |
| Certified heliocentric lower bound | — | — | — | **16.56** |

The **anchored optimised** column is the campaign the calculator flies and prices since issue #4:
a 4-parameter switching schedule (retro/prograde arc half-widths, escape guard, perihelion latch)
with event-located (bisected) arc edges, optimised per a₀ by Nelder-Mead multi-start
(`tools/optimize_pump_schedule.py`), every published number re-integrated at full engine
resolution (`fermi_sim/pump_schedule.py`). At the PSI-comparable 12-yr custody it reaches the
same cruise for **23.14 km/s — 3.5% under PSI's published 23.97**; the unconstrained frontier
point is 22.84 km/s at 28.5 yr. The bang-bang column stays as the independent
feasibility gate and cross-check (the optimum is audited to never lose to it).

**What is well-corroborated:** the *mechanism* (retrograde pump-down to 0.42 AU, then prograde
perihelion staircase), the *closure at today's α*, the *design-point endpoints*, the *outward-
spiral ceilings* (within PSI's own 2.7 % two-integrator band), and the *non-monotonic threshold
structure*. Engine and Fable agree to <0.2 % using two integrators each, and PSI agrees on the
mechanism and the ceilings.

**What is single-sourced (lower trust):**
- **PSI's 22.9 km/s lower anchor.** PSI itself flags this honestly: their intended cross-check (a
  direct-collocation solver) **did not converge**, so 22.9 is a single-method (Pontryagin) result,
  not a bound. Our optimised schedule's 12-yr result (23.14) now sits between their published
  optimum (23.97) and that anchor, consistent with both; our unconstrained frontier point (22.84
  at 28.5 yr) dips slightly below their anchor, which is unsurprising for a longer custody.
- **The bang-bang +7 % premium (25.63 vs 23.97).** This is a *deliberate* policy difference, not an
  error: the bang-bang schedule is cruder by construction. The instrumented split (§4 table) shows
  the premium is almost entirely in the retrograde pump-down (its 8.3 km/s vs the ~6.9 km/s
  impulsive minimum); the prograde legs agree to ~2 %.

**Which is more optimal?** Since issue #4, ours — the anchored optimised schedule beats PSI's
published 12-yr optimum by 3.5% under identical physics assumptions (and the audit suite replays
it end-to-end). The bang-bang reconstruction still lands exactly on PSI's own patience-trade
curve (between their 12-yr/23.97 patient profile and their faster/28.2 variant), which is what
validates the mechanism independently of any optimiser.

---

## 4b. Provenance & priority — who found perihelion pumping, and when

Stated plainly, because credit matters and the record is unambiguous.

### The Fermi Explorer position *before* the PSI paper

Build 64 (2026-06-22, §5b "Solar-Oberth, in depth") did not merely omit pumping — it **argued
against the electric perihelion burn**, and that text stood unchanged through build 122, the last
build before the assessment arrived:

> "**The perihelion burn must be high-thrust (chemical), not ion.** The Oberth benefit exists only
> during the brief perihelion pass (hours). A ~0.2 N ion thruster would need ~58 days to deliver
> 1.4 km/s, so it cannot capture the effect — a small storable-chemical or solid kick stage is
> required at perihelion. So this path is *not* pure electric propulsion."

**No audit caught it.** A full-history search of the four independent bot audits (Codex v01–v04,
Grok, Gemini, Fable-core), every `docs/plans/` entry, and the page's complete `perihelion` lineage
returns **zero** occurrences of multi-revolution / pump-down / retrograde-arc / apoapsis-shedding
concepts before build 123. The page's `perihelion` history jumps straight from build 64 (single-pass
solar-Oberth) to build 123 (PSI pumping).

### Why it was missed — a scope error, not an arithmetic error

The "58 days vs an hours-long pass" calculation was **correct**. What was wrong was the unexamined
premise that the manoeuvre must complete **in a single pass**. Spread those same 58 days across
~3–6 perihelion passes and the objection dissolves — the number we published as a refutation was
in fact the requirement.

Sharper still: **both ingredients were already in this project's own material, in separate documents,
and were never combined.**

| Ingredient | Where we already had it | Why it didn't connect |
|---|---|---|
| Multi-revolution low-thrust apsis-arc escape | the Earth-departure model integrates **~692 revolutions** | applied at Earth only; never transposed to the heliocentric leg |
| Repeated perihelion kicks, Sun as the return path | private "lasso" notes (2026-06-22) — a recirculating perihelion accelerator | **externally powered stations, passive probe**; and its own post-critique conclusion was that recirculating one probe is *weak* (one terminal kick per probe is the strong form) |
| Electric burn at a deep perihelion | §5b | rejected on the single-pass timing argument above |

The missing physical fact — the one that makes the combination work — is that a **power-limited
onboard** thruster receives up to **4× its 1-AU rated power** at 0.42 AU. Neither of our documents
contained that step.

### What PSI claims — and what PSI explicitly does *not* claim

PSI is scrupulous about priority. From [PSI‑TR‑2026‑0714](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/PSI-TR-2026-0714.pdf) §4.3 (emphasis added; reference brackets omitted):

> "The ingredients of this maneuver are established practice, and it is worth stating which are old
> and which is new. The energetic advantage of burning deep in a gravity well was identified by
> **Oberth**, and the two-burn strategy that exploits it — lower the periapsis, then burn at
> periapsis — **is classical**. Powered-flyby and solar-Oberth (perihelion-burn) escapes built on the
> same effect **are established concepts** in the interstellar-precursor literature, **including in
> Fermi Explorer's own reference analysis**. Splitting a low-thrust maneuver into repeated
> apsis-centered arcs over many revolutions **is likewise standard practice**: **SMART-1** escaped
> geostationary-transfer orbit on repeated perigee- and apogee-centered thrust arcs, and
> multi-revolution apsis-arc structures **are routine in low-thrust trajectory optimization**. What
> the present analysis contributes is **the quantified closure of this mission class by that
> combination** — cruise speed, Δv, flight time, and mass fraction — under the 1/r² law."

So PSI credits Oberth (1929), SMART-1's flight heritage, and standard low-thrust optimisation
practice — and credits *this project's own analysis* for the solar-Oberth concept.

### Attribution, as this project records it

| Question | Answer |
|---|---|
| Did Fermi Explorer or its audits find pumping first? | **No.** A documented rejection of the electric perihelion burn stood for ~3 weeks; no audit raised it. |
| Was PSI first **for this project**? | **Yes.** PSI overturned our published conclusion and supplied the mechanism, the design point, and the closure. |
| Did PSI invent perihelion pumping *as such*? | **No — and PSI says so itself** (§4.3): the ingredients are Oberth-classical and flight-demonstrated (SMART-1). |
| What is genuinely PSI's contribution? | **The quantified closure of this mission class** under the 1/r² power law — cruise speed, Δv, flight time and mass fraction — plus the correction of our single-pass error. |
| What is this project's contribution on top? | Independent in-engine reproduction, the non-monotonic envelope characterisation (islands/stall bands), the validated-profile convention, and the durable guard suite. |

**Adopted from PSI and credited throughout:** the perihelion-pumping closure, the validated design
profile (`PUMP_DESIGN_A0` = 2.5×10⁻⁴ m/s², `PUMP_DESIGN_ISP` = 2800 s), the GTO drop-off
recommendation, and the independent confirmation of the intercept geometry and target rankings.

---

## 5. Trust summary — what to rely on, and how hard

| Tier | Quantities | Corroboration | Rely on it? |
|---|---|---|---|
| **A — triangulated** | ephemeris, intercept geometry, impulsive floor, low-thrust spiral, C3, xenon sizing, power gate | 4 blind AI bots + GMAT + PSI, ≤0.2 % (most ≤0.01 %), multiple methods | **Yes**, to Fermi-estimate fidelity |
| **B — dual-source mechanism** | pumping mechanism, design endpoints, thresholds, spiral ceilings, synchrotron model | Engine + Fable (2 integrators each) + PSI on mechanism | **Yes** for the *mechanism and thresholds* |
| **B — α closure band** | pumping closes at α ≈ 15–21 W/kg | our band **brackets** the 17.3–19.5 W/kg implied by PSI's own published mass model (§2b) | **Yes** — corroborated in both sources' numbers |
| **C — optimised schedules** | PSI's optimised 23.97 / 22.9 km/s; our anchored optimised 23.14 (12 yr, at 4×) | two independent optimisers now agree the 12-yr optimum sits at ~23–24 km/s (ours 3.5% under theirs); PSI's own cross-check didn't converge; the audit suite replays ours end-to-end | **Yes** for the 12-yr closure level; the exact unconstrained optimum remains method-dependent |
| **C — thermal derating** (issue #5) | cap_eff(0.42) = 3.54; flown campaign 24.44 @ 12 yr; Si collapses (0.08×) | single first-principles model (energy balance verified by an independent bisection in the suite; representative α/ε/coefficient inputs) — no external source has reviewed the derate curve yet | **Yes** for the sign and scale of the derate; the exact curve inherits the thermo-optical inputs |
| **D — superseded** | the old ~20 km/s "modest xenon" SEP budget | Grok/Codex flagged it; replaced by the ~30 km/s + pumping model | **No** — historical only |

**Bottom line.** The *feasibility verdict and the geometry* are as solid as a first-order study
gets — six independent, mutually-blind sources agree. The *pumping mechanism* is corroborated by
two independent reconstructions plus PSI, and the *12-yr optimised closure level* is now confirmed
by two independent optimisers (ours and PSI's, agreeing to 3.5%). The remaining single-method
claim is the exact *unconstrained* optimum (PSI's 22.9 anchor; our frontier's 22.84 at 28.5 yr —
consistent, but each from one optimiser). Nothing in the audit record overturns the closure; the
honest caveats are all about *how cheaply* pumping closes, not *whether*.

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
