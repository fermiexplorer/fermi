# Project Fermi — Alpha Centauri ion-propulsion mission feasibility

A first-order ("Fermi") simulation and interactive calculator for an interstellar
precursor mission: get a small spacecraft **99% of the way to Alpha Centauri
(≤ 2600 AU) within 100,000 years**, carrying a ≥1 kg payload, departing from LEO
with ion propulsion.

It answers:

- Is the concept (≈500 kg, ~20 km/s from LEO, solar-electric ion, direct from LEO)
  feasible? **Yes.**
- What is the **minimum spacecraft Δv from LEO** with no gravity assist, and the
  mission profile that achieves it?
- **Solar vs fuel-cell vs hybrid** power — which wins, and why?
- **Direct vs gravity-assist** (Jupiter flyby, solar Oberth) trajectories.

## Headline results

| Quantity | Value |
|---|---|
| Required heliocentric cruise speed v∞ | ~23–24 km/s |
| Min departure Δv from LEO (impulsive floor) | ~14 km/s @ ~73,000 yr arrival |
| Realistic low-thrust (SEP) departure Δv | ~20 km/s |
| Best direct-departure window | ~70,000-80,000 yr (exact floor near 72,800 yr) |
| Departure aim | ~2.4° off the ecliptic at exact floor; ~1.5° at the 75k benchmark |
| Baseline vehicle | ~500 kg wet, ~40–50% xenon, ~55 kg silicon array @5 kW |
| Power verdict | **Solar wins; fuel cells lose by ~1000×** (chemical energy too sparse) |

The transit time is set by cruise speed, not by the propulsion — the years-long burn
is negligible against the ~80,000-year coast.

## Layout

```
fermi_sim/            Python engine (source of truth)
  astro.py        Alpha Centauri ephemeris + ecliptic transform
  intercept.py    V_p = A0/T + V_ac geometry, arrival-time optimisation
  departure.py    LEO -> v_inf Δv (impulsive + numerical low-thrust spiral)
  spacecraft.py   rocket eq, power, solar vs fuel-cell mass models
  trajectory.py   cruise time, Jupiter assist, solar Oberth
run_analysis.py   prints the full integrated analysis
index.html        interactive calculator (sliders / charts / methodology)
web/physics.js    shared JS physics used by the page (parity-checked vs Python)
audit/calcs/      independent verification suite (see below)
audit/codex/      Codex independent audits (conclusions + scripts)
audit/grok/       Grok independent audits (conclusions + scripts)
docs/             tender report + Codex audit prompts
```

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install numpy scipy astropy

# integrated numeric analysis
.venv/bin/python run_analysis.py

# independent audits (41 checks: astropy ephemeris, conservation laws, optima)
.venv/bin/python audit/calcs/run_audits.py

# web<->python parity (Node)
node audit/calcs/audit_webjs.mjs

# the interactive calculator (needs internet for the Plotly CDN)
python3 -m http.server 8000
# then open http://localhost:8000/index.html
```

## Verification

The physics is checked **independently** (different method, not self-comparison):

- ephemeris vs **astropy**; closest approach reproduced (~28 kyr, ~3 ly);
- intercept optimum vs **brute-force** optimiser + forward-propagation loop closure;
- departure Δv via **energy conservation**; spiral integrator convergence;
- rocket equation by **numerical mass-flow integration**;
- fuel-cell optimum Isp by **independent minimisation**;
- web JS vs Python **parity** (`audit/calcs/audit_webjs.mjs`).

All 41 Python checks + 10 JS-parity checks pass (plus a Playwright UI render test
and independent Codex & Grok re-implementations under `audit/`). See
`docs/CODEX_AUDIT_PROMPTS.md` for adversarial review prompts.

## Scope / limitations

First-order model: straight-line AC motion, patched-conic departure with best-case
launch timing, additive low-thrust penalty, geometric (not phased) gravity-assist
bounds. Cost is treated as a soft constraint and is out of scope here. Intended for
feasibility and architecture trades, not detailed trajectory design.
