# Codex audit prompts — Project Fermi

Paste these into an independent coding agent (Codex/Claude/etc.) pointed at this
repo. Each is scoped to one risk area and asks for an **independent** re-derivation
plus a numeric counter-check, not a restatement. Run them in a fresh session so the
reviewer doesn't inherit our assumptions.

> Setup line to prepend to any prompt:
> "This repo (`fermi_sim/`, `web/physics.js`, `audits/`) models an ion-propulsion probe
> to Alpha Centauri. Be adversarial: independently re-derive the physics, plug in
> the catalogue numbers yourself, and flag any error, unit slip, or unstated
> assumption. Don't trust the code's own comments."

## 1. Ephemeris & coordinate frame
"In `fermi_sim/astro.py` we convert Alpha Centauri's (RA, Dec, distance, proper motion,
radial velocity) into a heliocentric **ecliptic** Cartesian state, then propagate it
linearly. Independently recompute the 3-D position and space velocity (use astropy
or hand math), verify the obliquity rotation direction and the proper-motion→km/s
conversion (4.74047·μ[″/yr]·d[pc]), and confirm the closest approach (~28 kyr, ~3 ly).
Is treating AC's motion as a straight line over 10⁵ yr acceptable for a 2600 AU
(1%) miss target? Quantify the galactic-orbit curvature error."

## 2. Intercept geometry
"We claim the required heliocentric velocity to intercept AC at time T is
`V_p(T) = A₀/T + V_ac`, that |V_p| is minimised at the tangential intercept (~58 kyr,
|V_p| = AC's tangential speed ≈ 23.3 km/s), but that the **departure Δv from LEO** is
minimised later (~75 kyr) because of the out-of-ecliptic plane-change penalty.
Re-derive both optima from scratch, confirm the two are different and why, and check
the 2600 AU miss tolerance maps to a sensible spread of acceptable arrival times."

## 3. Departure energetics (patched-conic)
"In `fermi_sim/departure.py` we compute LEO→v∞ Δv via patched conics: heliocentric
`v_dep = √(v∞² + v_esc,☉²)` at 1 AU, borrow Earth's 29.8 km/s **in-plane only**
(`v∞,E² = v_dep² + v_E² − 2 v_dep v_E cos β`, β = out-of-plane tilt), then impulsive
`Δv = √(v∞,E² + v_esc,LEO²) − v_circ,LEO`. Independently verify the energy balance,
challenge the 'align in-plane projection with Earth's velocity' best-case assumption,
and check whether approximating β by the v∞ asymptote tilt (rather than the velocity
direction at 1 AU) is conservative or optimistic."

## 4. Low-thrust spiral model
"`spiral_escape_dv` integrates a constant-tangential-thrust 2-D spiral (RK4,
radius-adaptive dt) to estimate the low-thrust Earth-departure Δv, giving ~25 km/s
vs the ~14 km/s impulsive floor. Verify the integrator conserves energy, is in the
thrust-acceleration-independent 'low-thrust limit', and that ~25 km/s is a reasonable
**upper** bound for a naive continuous spiral. Is the additive penalty model used in
the web tool (floor + slider) defensible, and is ~20 km/s realistic for optimised
perigee-biased SEP? Cite SEP escape literature if you can."

## 5. Rocket equation, power & energy
"Check `fermi_sim/spacecraft.py`: `m_p = m_dry(e^(Δv/v_e) − 1)`, electrical energy
`E = ½ m_p v_e²/η`, thrust `F = 2ηP/v_e`, burn time `m_p v_e/F`. Confirm units and that
E scales **linearly with v_e** at fixed Δv (the basis of 'higher Isp costs energy').
Sanity-check the baseline: 255 kg dry, 20 km/s, Isp 3000 s → ~248 kg xenon, ~50,000 kWh,
~1.1 yr burn at 5 kW. Are the ~150 W/kg solar and η = 0.6 assumptions current?"

## 6. Fuel-cell energy wall
"We argue chemical fuel cells can't power this EP mission: reactant mass
`= E/(η_fc·e_chem)` is tens of tonnes; the mass-optimal fuel-cell Isp is ~1350 s (found
numerically, NOT the naive `√(2η e_chem)` which only holds for v_e≫Δv); and if the spent
exhaust is the propellant, `v_e ≤ √(2η e_chem)` ≈ 2.4 km/s. Independently reproduce the
optimum (minimise propellant+reactant over Isp), verify the self-powered cap, and confirm
the ~1000× mass disadvantage vs a solar array. Does an RTG/reactor change the conclusion
for a burn done within a few AU of the Sun?"

## 7. Gravity assists
"`fermi_sim/trajectory.py` gives a Jupiter flyby max heliocentric gain (turn-angle bound)
and a solar-Oberth v∞ (`√((v_peri+Δv)² − v_esc²)` at a few R_sun). These are geometric
upper bounds, not phased solutions. Check the Jupiter turn-angle formula and the Oberth
leverage (~1–2 km/s burn → 24 km/s v∞), and assess realism: heat-shield mass for a
~6 R_sun perihelion, and how to drop perihelion (retro burn vs planetary assist)."

## 8. Cross-implementation & units
"`web/physics.js` (browser) must match `fermi_sim/` (Python). Run `audits/run_audits.py`
and `node audits/audit_webjs.mjs`. Independently spot-check 3 values across both.
Grep for unit bugs (km vs m, deg vs rad, Isp vs v_e, year length). Confirm the embedded
AC state vector in `web/physics.js` equals what `fermi_sim` produces."

## 9. Adversarial sweep (meta)
"Find the single biggest error or most optimistic assumption in this model that would
change the feasibility verdict (currently: direct solar-electric ion, ~20 km/s from LEO,
~500 kg, ~75–80 kyr, feasible). Rank the top 5 risks by impact on the conclusion."

## 10. The 58 kyr intercept & the "modest xenon" claim
"We claim the minimum-**speed** (tangential) intercept at ~58 kyr is achievable with only a
modest xenon load — which feels surprising for an interstellar-class mission. Engine numbers
to attack (recompute, don't restate): AC now at 274,719 AU = 4.344 ly, |V_ac| = 32.30 km/s;
tangential arrival 58,138 yr → v∞ = 23.27 km/s tilted −10.1° out of the ecliptic; departure Δv
from a 400 km LEO = **14.65 km/s** impulsive (Oberth floor) up to **26.01 km/s** naive low-thrust
spiral, with a ~20 km/s optimised-SEP budget in between. On a **255 kg** dry+payload bus the
rocket equation `m_p = m_dry(e^(Δv/v_e) − 1)` gives, at **Isp 3000 s**: ~**165 kg** xenon (39%) at
the floor, ~**248 kg** (49%) at 20 km/s, ~362 kg (59%) at the spiral bound (Isp 4000 s: 116 / 170 /
240 kg).

Independently:
(a) Re-derive v∞(58 kyr) from `V_p(T) = A₀/T + V_ac` and confirm the −10° plane angle — note the
    bare `|A₀|/T` is only 22.45 km/s, so AC's own motion matters; show your vectors.
(b) Reproduce the full departure-Δv chain and the xenon mass yourself, and reconcile with the
    engine's `propellant_mass`.
(c) Decide whether 'modest' is honest or an artifact: is the impulsive Oberth floor the right
    sizing budget, or should the 20–26 km/s low-thrust number drive it? Does the mass actually
    close once the tank (~8% of m_p), thruster+PPU and structure are taken out of the 255 kg dry,
    and is a 40–60% propellant fraction physically storable in one stage?
(d) Stress-test the framing that 'long trip ≠ large Δv': confirm the 58 kyr is set by the 2.7×10⁵ AU
    distance at a Voyager-class speed, and that ion's v_e ≈ Δv (29.4 km/s at Isp 3000) is what holds
    the mass ratio near 2 — or find where that reasoning fails.
(e) Confirm 58 kyr is the min-**speed** aim and costs *more* Δv than the ~73 kyr min-**Δv** point
    (13.88 km/s, ~154 kg xenon at Isp 3000) because of the out-of-plane plane change; flag anywhere
    the tool or its copy conflates the min-speed and min-Δv arrivals."
