# 01 — Phased low-thrust trajectory optimization (scope)

## Why

Today the model treats the realistic ion departure budget as a **benchmark, not a
derived result**. We have three points:

- **Impulsive floor ≈ 14 km/s** — rigorous (patched-conic + Oberth at LEO perigee).
- **Naïve continuous spiral ≈ 25 km/s** — a numerically-integrated upper bound
  (constant tangential thrust, full gravity losses).
- **"Realistic" SEP ≈ 20 km/s** — an *industry benchmark* inserted via the additive
  low-thrust-penalty slider. **This is the only headline number not derived by the code.**

Both the Codex and Grok audits independently flagged this as the single largest open
item. The goal of this work is to **replace the ~20 km/s assumption with a value
(and a flight profile) computed from a phased, finite-thrust trajectory optimization.**

## Objective

Given a spacecraft (power at 1 AU, Isp, thruster efficiency, dry mass, propellant) and
the required heliocentric escape state (v∞ vector and arrival time from the existing
intercept solver), compute the **minimum-Δv low-thrust trajectory from LEO to solar-
system escape**, producing:

1. Total Δv and propellant mass (the derived replacement for the ~20 km/s benchmark).
2. The thrust/coast profile vs time, total thrust duration, and the Earth-escape vs
   heliocentric split.
3. Sensitivity of all the above to power (with the solar 1/r² falloff), Isp, and
   thrust-to-mass.

## Phases to model

1. **Earth-escape spiral (geocentric).** Many-revolution low-thrust spiral from LEO to
   Earth-escape with the required v∞,Earth. Gravity losses and (optional) perigee-biased
   thrusting / coast-near-apogee are the main physics. This is where most of the loss
   vs impulsive lives.
2. **Heliocentric escape.** From Earth's SOI to the target heliocentric v∞, with solar-
   electric power falling as 1/r² (thrust drops as the probe climbs out). Determines how
   much of the burn must happen close to the Sun.
3. **Coast.** Ballistic to the AC intercept (already handled by `fermi_sim.intercept`).

## Candidate methods (pick per phase)

| Method | Good for | Cost / risk |
|---|---|---|
| Edelbaum / orbital-element **averaging** | the many-rev Earth spiral | fast, approximate; classic SEP-escape estimate |
| **Sims-Flanagan** transcription (impulses-on-arcs) + NLP | heliocentric leg, mission-design standard | medium; great via **pykep** |
| Direct **collocation** (Hermite-Simpson) + NLP (IPOPT/SLSQP) | full finite-burn optimum | heavier; most rigorous |
| **Indirect / Pontryagin** (costate) | elegant optimum, thrust-switching | hard to converge; sensitive |
| Control-parametrized RK + `scipy.optimize` | quick in-repo first pass | medium accuracy |

**Recommended first pass:** (a) Earth-escape via an Edelbaum/averaged spiral (or our
existing RK spiral, refined with perigee-biased thrusting) for the v∞,Earth budget;
(b) heliocentric leg via **pykep** (ESA) Sims-Flanagan with a 1/r² power model. pykep is
the practical open-source choice (Taylor integrators, low-thrust legs, Lambert). Cross-
check against the analytic bracket [14, 25] km/s and against a flown SEP datapoint
(e.g. Dawn: Isp ~3100 s, ~11 km/s delivered over years).

## Inputs / outputs (proposed `fermi_sim/lowthrust.py`)

- **In:** `power_1au_w, isp_s, eta, dry_mass, leo_alt, v_inf_sun (vec), arrival_T`.
- **Out:** `dv_total, prop_mass, t_thrust, dv_earth_escape, dv_helio, thrust_profile,
  converged (bool)`, plus a sensitivity table over power/Isp.
- Feeds the web tool: the low-thrust-penalty slider default becomes a *derived* number,
  with the bracket retained as a sanity band.

## Validation & acceptance

- Result lands inside the [14, 25] km/s bracket and is self-consistent with the energy
  audit; converges across solver tolerances.
- New independent check in `audit/calcs/` (e.g. energy/impulse bookkeeping along the
  optimized arc; Edelbaum closed-form vs numerical spiral agreement).
- Documented limitation: no eclipse/duty-cycle, J2, or detailed PPU throttling unless
  added later.

## Milestones / effort (rough)

1. **M1 (small):** Earth-escape spiral with perigee-biased thrusting + coast; report the
   real Earth-departure loss vs impulsive. (Refines our current RK spiral.)
2. **M2 (medium):** heliocentric SEP leg with 1/r² power (pykep Sims-Flanagan); derive
   total Δv + thrust profile for the baseline design.
3. **M3 (small):** sensitivity sweep over power/Isp; wire the derived number into the web
   tool and add the independent audit.

## Out of scope (for this pass)

Full mission-design fidelity: launch-window/calendar phasing, planetary gravity assists
as phased solutions, eclipse/thermal duty cycles, navigation, and multi-year operations.
Those are separate items already listed in the on-page auditor guide.
