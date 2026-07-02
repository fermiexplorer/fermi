# Fable 5 independent audit — conclusions

*Parallel model re-implementation (alongside `audit/codex`, `audit/grok`, `audit/gemini`),
performed by Claude Fable 5. Every headline quantity was re-derived from the same catalogued
inputs by a **different method** than the engine, then compared. The engine (`fermi_sim`) was
imported only to read the values being audited — never to produce the audit's own numbers.*

**Verdict: PASS — all 22 independent checks agree with the engine, most to <0.01 %, the
adaptive-integrator re-runs of the power gate to <0.2 %.** Run: `.venv/bin/python
audit/fable/fable_independent_checks.py` (results in `fable_results.json`).

## Method independence

| Quantity | Engine method | Fable method |
|---|---|---|
| AC velocity from catalogue | analytic RA/Dec sky-basis vectors | **finite-differencing** two proper-motion-propagated epochs |
| Closest approach | perpendicular-foot closed form | **golden-section minimisation** of \|r₀+vt\| |
| Intercept & optima | Vₚ = A₀/T + V_ac algebra + scipy | **forward-propagation loop closure** + bounded minimisation |
| v∞,Earth | law of cosines | **explicit 3-D vector subtraction** of Earth's velocity |
| Impulsive (Oberth) Δv | energy algebra | **numerical two-body propagation** of the post-burn state to large r, reading the asymptotic speed |
| Low-thrust spiral | fixed-step RK4 | **solve_ivp adaptive RK45** with energy events |
| Rocket equation | closed form | **numerical mass-flow ODE** |
| 1/r² power gate | fixed-dt RK4 loop | **solve_ivp adaptive RK45** re-implementation |
| Earth-escape revolutions | analytic N = μ/(8πar²) | **unwrapped polar angle** of the integrated spiral |

## Headline agreement

| Quantity | Fable | Engine | Diff |
|---|---|---|---|
| AC space speed | 32.3008 km/s | 32.3008 km/s | 1×10⁻⁸ % |
| Closest approach | 27.96 kyr @ 3.1297 ly | same | <2×10⁻⁴ % |
| Min-speed arrival | 58,138 yr, v∞ 23.272 km/s, tilt −10.0° | same | <0.01 % |
| Intercept loop closure (3 arrival times) | miss < 1 mm over ~6 ly | — | exact |
| v∞,Earth (min-speed aim) | 19.4885 km/s | 19.4885 km/s | 2×10⁻¹⁴ % |
| Impulsive departure Δv | 14.633 km/s | 14.633 km/s | 4×10⁻⁵ % |
| — propagated post-burn v∞ (RK45) | 19.4885 km/s | (energy algebra) | 2×10⁻⁸ % |
| Spiral escape time (C3=0, a=5×10⁻⁴) | 14.2652 Ms | 14.2657 Ms | 0.004 % |
| Spiral revolutions to escape | 691.98 | 691.87 (analytic) | 0.017 % |
| Low-thrust departure Δv (fit vs my spiral) | 25.987 km/s | 25.988 km/s | 0.002 % |
| Rocket-equation propellant (ODE) | 363.513 kg | 363.512 kg | 2×10⁻⁴ % |
| Power gate: high-α solar default (43/15 kg, 2 kW) | 30.34 km/s | 30.30 km/s | 0.15 % |
| Power gate: low-α solar (710/256 kg, 20 kW) | 14.45 km/s | 14.42 km/s | 0.19 % |
| Power gate: nuclear 5 kW (constant power) | 25.25 km/s | 25.24 km/s | 0.05 % |

## Findings

1. **The engine's physics is reproduced end-to-end by independent methods.** In particular
   the two results an adaptive integrator could most plausibly overturn — the fixed-step
   spiral and the fixed-dt 1/r² power gate — agree with solve_ivp (RK45, rtol 1e-8/1e-9)
   to 0.004 % and <0.2 % respectively.
2. **The α-conditional solar framing (build 104) is confirmed**: the high-α default
   (43 kg wet / 15 kg dry, 2 kW) reaches v∞ ≈ 30.3 km/s and **closes** (floor 23.4);
   the low-α vehicle (710/256 kg) saturates at 14.4 km/s and **fails**; nuclear 5 kW
   (constant power) closes at 25.25 km/s. Same closure verdicts, independent integrator.
3. **The derived low-thrust departure fit is genuinely a fit of the physics**: the engine's
   closed-form `lowthrust_departure_dv` matches an independently integrated (RK45)
   constant-tangential spiral from LEO to the mission v∞,E to 0.002 %.
4. **Consistency with the GMAT cross-validation** (`audit/gmat/`): the same impulsive C3
   and spiral-escape time that NASA GMAT reproduces are reproduced here by a third method
   (scipy adaptive integration), giving three-way agreement engine/GMAT/Fable.
5. Transparency note: two early drafts of this audit script had bugs of its own (a
   mas→radians factor off by 1000×, and a terminal event ending the spiral at C3=0 before
   the v∞ target). Both produced loud FAILs against the engine and were fixed in the audit —
   the engine needed no changes. This is the audit working as intended.

## Scope / limitations

Same first-order scope as the engine: straight-line AC motion, patched-conic departure,
point-mass gravity, best-case launch geometry. This audit checks that the engine computes
its stated model correctly and self-consistently — not that the model captures every
real-mission effect (see the page's "Guide for an independent auditor" for what a deeper
audit should probe).
