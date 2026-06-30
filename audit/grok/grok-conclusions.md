# Grok Conclusions — Independent Audit (v02)

Rerun against `audit/AUDIT_PROMPTS.md` (prompts 1–10), June 2026.
Parallel Codex/Gemini sessions under `audit/codex/` and `audit/gemini/` left untouched.

## What Was Run

| Command | Result |
|---|---|
| `.venv/bin/python audit/calcs/run_audits.py` | **41/41 PASS** |
| `node audit/calcs/audit_webjs.mjs` | **10/10 PASS** |
| `.venv/bin/pytest tests/ -q` | **8/8 PASS** |
| `.venv/bin/python audit/grok/grok_audit_prompts.py` | **10/10 PASS** → `prompt_results.json` |
| `.venv/bin/python audit/grok/grok_independent_checks.py` | PASS |
| `.venv/bin/python audit/grok/grok_sensitivity_sweeps.py` | PASS → `sweep_results.json` |

## Prompt-by-Prompt Findings

### 1 · Ephemeris & coordinate frame — PASS

Astropy and hand-built catalog states agree to **5.7 m / 2.6×10⁻⁶ m/s**. Closest approach:
**27,960 yr @ 3.130 ly**. Galactic tidal curvature over 100k yr ≈ **1.03 AU** — negligible
vs the 2600 AU miss target. Straight-line AC propagation is acceptable.

### 2 · Intercept geometry — PASS

Two optima are **distinct and correctly separated**:

| Optimum | Arrival | v∞ | Tilt | Impulsive Δv |
|---|---|---|---|---|
| Min **speed** (tangential) | 58,138 yr | 23.27 km/s | −10.0° | 14.65 km/s |
| Min **Δv** (propellant) | 72,800 yr | 23.79 km/s | −2.4° | **13.88 km/s** |

2600 AU miss maps to ±**710 yr** @ 75k, ±**689 yr** @ optimum — sensible windows.

### 3 · Departure energetics — PASS

LEO impulsive energy balance and heliocentric v_dep→v∞ relation verified independently.
The β = v∞ tilt assumption is **exact for radial departure at 1 AU** but **optimistic**
if a fixed launch date misaligns the in-plane projection with Earth's velocity — a
documented limitation, not a code bug.

### 4 · Low-thrust spiral — PASS (with caveat)

`solve_ivp` spiral at 75k: **25.13 km/s** (engine RK4: 25.13 km/s, Δ < 0.6 m/s).
Additive penalty = spiral − floor = **11.24 km/s**, matching web `SPIRAL_MAX = 11.3`.
Floor + 6 km/s penalty → **19.9 km/s**, bracketing the ~20 km/s SEP benchmark.

**Caveat:** The additive model is a defensible *bracket*, not a derived phased trajectory.
Real perigee-biased SEP could differ; this is the #1 adversarial risk (see prompt 9).

### 5 · Rocket equation, power & energy — PASS

255 kg dry, 20 km/s, Isp 3000 s → **248 kg** xenon, **49,737 kWh**, **1.13 yr** burn @ 5 kW.
Energy rises with Isp at fixed Δv (confirmed). Silicon array: **18.4 m², 55 kg, 91 W/kg** —
within the 50–150 W/kg plausibility band used in `audit/calcs/`.

### 6 · Fuel-cell energy wall — PASS

Mass-optimal fuel-cell Isp: **1353 s**, **28.3 t** consumables. At Isp 3000 s, reactants
are **677×** the 55 kg solar array. Self-powered cap **2.4 km/s**. RTG/reactor does not
change the conclusion for a burn within a few AU — solar is free there.

### 7 · Gravity assists — PASS (bounds only)

Jupiter max gain **15.3 km/s** (geometric upper bound). Solar Oberth: **2 km/s burn @ 6 R☉
→ 31.8 km/s v∞**. Heat-shield mass for 4–6 R☉ perihelion is **not modelled** — correctly
flagged as out of scope for the first-order model.

### 8 · Cross-implementation — PASS

Spot checks match engine exactly. Full suite: 41 Python + 10 JS parity checks pass.
Embedded AC state vector in `web/physics.js` matches `fermi_sim` (verified by parity audit).

### 9 · Adversarial sweep — verdict unchanged

Top 5 risks by impact on the feasibility conclusion:

1. **~20 km/s SEP is benchmarked, not derived** — could shift propellant ±20–30 %
2. **Best-case launch timing** — fixed date could add several km/s
3. **Additive low-thrust penalty model** — 20 km/s is mid-bracket, not proven
4. **Solar subsystem mass assumptions** — affects margin, not go/no-go
5. **Straight-line AC motion** — negligible (~1 AU vs 2600 AU tolerance)

None of these overturn the feasibility verdict at Fermi-estimate fidelity.

### 10 · The 58 kyr intercept & "modest xenon" — PASS (with nuance)

**(a) Vector decomposition @ tangential intercept (58,138 yr):**

- |A₀|/T = **22.45 km/s** (aim only — would undershoot)
- V_ac = **32.30 km/s**
- V_p = **23.27 km/s**, tilt **−10.0°**

AC's own motion is essential; bare aim term is insufficient.

**(b) Xenon masses @ Isp 3000 s, 255 kg dry (independently reproduced):**

| Budget | Δv | Xenon | Fraction |
|---|---|---|---|
| 58k impulsive floor | 14.65 km/s | 165 kg | 39% |
| 73k min-Δv impulsive | 13.88 km/s | 154 kg | 38% |
| **SEP design (20 km/s)** | **20 km/s** | **248 kg** | **49%** |
| 58k spiral bound | 26.01 km/s | 362 kg | 59% |

**(c) Is "modest" honest?**

**Partially.** ~165 kg (39%) at the 58k *impulsive floor* is mathematically correct but
**not the right sizing budget** — ion propulsion cannot capture the Oberth floor. The
design must use **~20 km/s → ~248 kg (49%)**. Mass closes: 55 kg array + 30 kg engine
+ 20 kg tank → **150 kg** remainder for bus/payload/margin. A 40–60 % xenon fraction in
a single COPV stage is physically storable.

**(d) "Long trip ≠ large Δv"** — confirmed. AC at 274,719 AU; Voyager-class 16.6 km/s
would take ~78k yr just to cover today's distance. Ion Isp 3000 s gives v_e ≈ 29.4 km/s ≈ Δv,
holding mass ratio near 2.0.

**(e) Min-speed vs min-Δv conflation** — the tool **does not conflate them**. `index.html`
methodology table and text explicitly distinguish 58k (min speed, more Δv) from 72.8k
(min Δv, min propellant). The arrival slider correctly targets the min-propellant optimum.

## Overall Conclusion

**PASS.** All 10 adversarial prompts satisfied. Physics is numerically robust across
four independent re-implementations (calcs suite, Codex, Grok, Gemini) agreeing to ≤0.1 %.

The feasibility verdict holds: direct solar-electric ion from LEO, ~500 kg wet, ~20 km/s
SEP budget, ~73–75k yr arrival, well inside 100k yr / 2600 AU.

The single largest open item — already scoped in `docs/plans/01-phased-low-thrust-trajectory.md`
— is replacing the benchmarked ~20 km/s SEP figure with a derived phased low-thrust trajectory.

## Files

```
audit/grok/
  grok_audit_prompts.py       # prompts 1–10 → prompt_results.json
  grok_independent_checks.py
  grok_sensitivity_sweeps.py
  sweep_results.json
  prompt_results.json
  grok-conclusions.md         # this document
```