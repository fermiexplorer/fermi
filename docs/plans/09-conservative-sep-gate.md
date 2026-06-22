# 09 — Make the model conservative: close the three optimism gaps 100%

> **STATUS (build 61): IMPLEMENTED + VERIFIED.** Gap 1: `sep_achievable_vinf` (1/r² power-fade
> RK4) in fermi_sim, mirrored to physics.js, parity 18/18; it is now a feasibility gate so a PURE
> solar-electric design is `feasible` only if achievable v∞ ≥ the cruise floor. The conservative
> power-fade analysis (20 kW/1.6 t → 19.5 km/s, below 23.4) makes the default pure-SEP **NOT FEASIBLE
> (power-limited)** — Oberth/Jupiter and the chemical boost remain the closing paths. Gap 2:
> conservative defaults — Hall thruster Isp 1585 s, η 0.50. Gap 3: Departure-Δv relabelled as the
> optimistic Earth-escape budget; feasibility set by the gate; chemical/impulsive floor is the
> "Chemical-boost option" comparison. Gap 4: `buildTraj` thrust now fades as 1/r². New KPI
> "Power-limited v∞". Independent audit (Euler-Cromer, different dt) in audit_departure (19/19);
> ui_sliders 60/60 (default infeasible, Oberth closes, 50 kW still doesn't close), pytest 8/8.

Goal: `feasible` must mean **survives the conservative case**, not "masses add up". Engine-first
(fermi_sim source of truth) → mirror physics.js → independent audit → UI.

## Gap 1 (decisive): power-limited achievable-v∞ gate — the 1/r² coupled SEP model
Today feasibility = mass closure only. Add the power-fade physics: as the probe spirals out,
array power falls as 1/r², throttling thrust before v∞ is reached.

**Model (new engine fn `sep_achievable_vinf`)**, for a given installed power P0 (at 1 AU), wet mass,
dry+payload, Isp, efficiency:
- v_e = Isp·g₀;  array mass = k_arr·P0,  thruster+PPU = k_ppu·P0  (k_arr=10, k_ppu=5 kg/kW);
  propellant m_p = m_wet − (dry+pay) − k_arr·P0 − k_ppu·P0  (≤0 ⇒ infeasible).
- Thrust F(r) = 2·η·P0/(v_e·r²) (r in AU); ṁ = F/v_e. Start at 1 AU heliocentric circular
  (v=29.78 km/s), thrust prograde, RK4-integrate (like buildTraj) until propellant exhausts; then
  coast. **Achievable v∞ = asymptotic speed** = √(max(0, 2·(½v² − μ☉/r)) sampled as r→large).
- Returns achievable v∞ for that P0/mass/Isp.

**Feasibility gate:** the probe is **power-feasible** iff achievable v∞ ≥ required floor (≈23.4 km/s)
for the CURRENT design (one integration per compute(), like buildTraj — cheap). For the headline
verdict, also report the **best achievable v∞ optimised over P0** (grid/golden-section, ~12 P0
samples) so we can state "no practical mass reaches the floor" on an independent basis.
→ If power-infeasible, the design is **NOT FEASIBLE** even when the mass budget closes.

Independent audit (`audit/calcs/`): re-integrate the same scenario with a *different* integrator/step
and confirm achievable v∞ matches; confirm the **saturation** (achievable v∞ vs wet mass is monotone
and stays < floor for SEP-from-1-AU) — i.e. reproduce the saturation-curve shape by an independent
method (not by calling the engine against itself).

## Gap 2: conservative defaults
- **Default Isp → 1585 s** (was 3000 s). Keep the slider for optimistic exploration; add a
  "conservative (1585 s) / optimistic" note.
- Adopt the conservative specific masses in the power/mass model (array 10 kg/kW, PPU 5 kg/kW,
  η 50 %) as the defaults used by the gate, with sliders still overriding.

## Gap 3: departure Δv on the conservative basis
- The achievable-v∞ integration already answers feasibility directly (it IS the real v∞ the SEP can
  reach), so it supersedes the 25-vs-41 bookkeeping for the verdict.
- For the Δv KPI: show the **conservative full-electric-spiral Δv (~41 km/s from LEO, no Earth-velocity
  borrowing / no Oberth)** as the headline ion number, with the optimistic borrowed-velocity ~25 km/s
  and the impulsive ~14 km/s floor as labelled comparisons. (Pointing/GNC margins already added.)

## Verdict reframing
- `feasible` = mass closure **AND** power-feasible (achievable v∞ ≥ floor) **AND** propellant ≥ 0.
- Expected outcome: pure-SEP from 1 AU **does NOT close** without a gravity assist — on the
  conservative basis. The solar-Oberth/Sundiver (`ga=oberth`) and chemical-boost remain the closing paths.
- New KPI "Power-limited v∞" showing achievable vs required, and the infeasibility reason when it bites.

## Verification
- New engine fn + audit check (independent integrator); JS↔Py parity for `sepAchievableVinf`.
- pytest, node webjs parity, ui_sliders (assert: default pure-SEP now INFEASIBLE on power; raising
  power/Isp or enabling Oberth restores feasibility; achievable v∞ < floor for SEP-from-LEO).
- Screenshot the new verdict + KPI.

## Decisions needed before coding (see chat)
1. Flip the **headline default** to the conservative verdict (pure-SEP shown NOT feasible, Oberth/
   chemical as the closing options)? — recommended, that's the point.
2. Default **Isp 1585 s**? (changes many displayed numbers)
3. Headline departure Δv = **conservative ~41 km/s** (optimistic 25 km/s as comparison)?

## Gap 4 (added): orbital paths under 1/r² power fade
The trajectory integrator (`buildTraj`) uses CONSTANT tangential thrust. Revisit it so thrust
fades as 1/r² like the real array: the heliocentric escape arc then accelerates hard near the
Sun and weakly far out, and **asymptotes to the achievable v∞** — so the drawn path is consistent
with the feasibility gate (a power-starved design visibly falls short of the floor instead of
magically reaching it). Same change conceptually applies to how the chase-cam escape arc is shaped.

## Decision (chat): FULL CONSERVATIVE, default — confirmed.

## Push/deploy: build NN, engine+physics.js+audit+UI, standard inline deploy.
