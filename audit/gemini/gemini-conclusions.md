# Gemini Conclusions — Independent Audit

Third independent re-implementation of the core physics, using **different methods**
from the engine and from the Codex/Grok audits:

- Alpha Centauri state via **astropy** `SkyCoord` (catalogue → ICRS Cartesian → ecliptic).
- Earth-escape spiral via **scipy `solve_ivp`** (adaptive RK45 with an energy event),
  independent of the engine's fixed-step RK4.
- Minimum-speed arrival via **scipy** optimisation.

Script: `audit/gemini/gemini_independent_checks.py` → `gemini_results.json`.

## Result — agreement with the engine

| Quantity | Gemini | Engine (`fermi_sim`) |
|---|---|---|
| AC position difference | 5.7 m (vs 4.34 ly) | — |
| AC velocity difference | 2.6e-6 m/s | — |
| v∞ heliocentric @ 75k yr | 23.810557 km/s | 23.810557 km/s |
| v∞ relative to Earth | 18.62839 km/s | 18.62839 km/s |
| impulsive Δv from LEO @ 75k | 13.88557 km/s | 13.88557 km/s |
| Earth-escape spiral Δv | 25.127 km/s | 25.127 km/s |

The astropy and hand-built ephemerides match to ~6 m / ~3e-6 m/s. The intercept,
departure, and impulsive-Δv numbers match to ~1e-8. The spiral Δv matches to ~0.002%
**across different integrators** (`solve_ivp` RK45 vs fixed-step RK4), confirming the
low-thrust-spiral upper bound is numerically robust.

## Bottom line

Gemini finds **no numerical disagreement** with the engine on any headline quantity.
With the Codex and Grok audits, three independent re-implementations (different
libraries, integrators, and optimisers) now agree to ≤0.1% — the feasibility result and
the headline numbers are robust at this model fidelity. The open item remains the same:
a derived (rather than benchmarked) phased low-thrust ~20 km/s figure — scoped in
`docs/plans/01-phased-low-thrust-trajectory.md`.
